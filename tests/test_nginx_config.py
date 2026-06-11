"""Validate nginx prod templates (syntax check via Docker)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
NGINX_IMAGE = "nginx:1.27-alpine"
TEMPLATES = ROOT / "docker/nginx/templates"
SNIPPETS = ROOT / "docker/nginx/snippets"


def _write_dummy_tls_certs(base_dir: Path, domain: str) -> None:
    cert_dir = base_dir / "live" / domain
    cert_dir.mkdir(parents=True, exist_ok=True)
    if not shutil.which("openssl"):
        pytest.skip("openssl not available")
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-nodes",
            "-newkey",
            "rsa:2048",
            "-days",
            "1",
            "-keyout",
            str(cert_dir / "privkey.pem"),
            "-out",
            str(cert_dir / "fullchain.pem"),
            "-subj",
            f"/CN={domain}",
        ],
        check=True,
        capture_output=True,
    )


def _run_nginx_syntax_check(
    *,
    template_path: Path,
    domain: str,
    tls_mount: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    template_dir = template_path.parent
    template_name = template_path.name

    script = f"""
set -e
export DOMAIN={domain}
envsubst '${{DOMAIN}}' < /templates/{template_name} | sed 's/server app:8000/server 127.0.0.1:8000/' > /tmp/default.conf
cat > /tmp/nginx.conf <<'EOF'
events {{ worker_connections 1024; }}
http {{
    include /etc/nginx/snippets/proxy-params.conf;
    include /tmp/default.conf;
}}
EOF
nginx -t -c /tmp/nginx.conf
"""
    cmd = [
        "docker",
        "run",
        "--rm",
        "-e",
        f"DOMAIN={domain}",
        "-v",
        f"{template_dir}:/templates:ro",
        "-v",
        f"{SNIPPETS}:/etc/nginx/snippets:ro",
    ]
    if tls_mount is not None:
        cmd.extend(["-v", f"{tls_mount}:/etc/letsencrypt:ro"])
    cmd.extend([NGINX_IMAGE, "sh", "-c", script])
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


@pytest.mark.skipif(not shutil.which("docker"), reason="docker not available")
def test_nginx_http_only_template_syntax():
    result = _run_nginx_syntax_check(
        template_path=SNIPPETS / "http-only.conf.template",
        domain="test.example.com",
    )
    assert result.returncode == 0, result.stderr + result.stdout


@pytest.mark.skipif(not shutil.which("docker"), reason="docker not available")
def test_nginx_https_template_syntax(tmp_path):
    domain = "test.example.com"
    _write_dummy_tls_certs(tmp_path, domain)
    result = _run_nginx_syntax_check(
        template_path=TEMPLATES / "default.conf.template",
        domain=domain,
        tls_mount=tmp_path,
    )
    assert result.returncode == 0, result.stderr + result.stdout


def test_nginx_templates_include_websocket_proxy_settings():
    https = (TEMPLATES / "default.conf.template").read_text(encoding="utf-8")
    http_only = (SNIPPETS / "http-only.conf.template").read_text(encoding="utf-8")
    params = (SNIPPETS / "proxy-params.conf").read_text(encoding="utf-8")

    assert "proxy_set_header Upgrade" in params
    assert "proxy_read_timeout 86400" in params
    assert "connection_upgrade" in https
    assert "connection_upgrade" in http_only
    assert "shatra_app" in https
    gzip = (SNIPPETS / "gzip.conf").read_text(encoding="utf-8")
    assert "gzip on" in gzip
    assert "gzip_proxied" in gzip
    assert "snippets/gzip.conf" in https
    assert "snippets/gzip.conf" in http_only
