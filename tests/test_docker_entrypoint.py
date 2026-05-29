"""Проверка Docker entrypoint: миграции перед стартом приложения."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "docker-entrypoint.sh"
DOCKERFILE = ROOT / "Dockerfile"


class TestDockerEntrypoint:
    def test_script_exists_and_has_shebang(self):
        assert ENTRYPOINT.is_file()
        content = ENTRYPOINT.read_text(encoding="utf-8")
        assert content.startswith("#!/")
        assert "set -e" in content

    def test_runs_alembic_before_uvicorn(self):
        content = ENTRYPOINT.read_text(encoding="utf-8")
        alembic_pos = content.find("alembic upgrade head")
        uvicorn_pos = content.find("uvicorn main:app")
        assert alembic_pos != -1
        assert uvicorn_pos != -1
        assert alembic_pos < uvicorn_pos

    def test_dockerfile_uses_entrypoint(self):
        docker = DOCKERFILE.read_text(encoding="utf-8")
        assert "docker-entrypoint.sh" in docker
        assert "ENTRYPOINT" in docker
        assert "chmod +x" in docker
