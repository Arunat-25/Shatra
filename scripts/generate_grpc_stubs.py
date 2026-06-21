#!/usr/bin/env python3
"""Generate Python gRPC stubs from proto/shatra/ai/v1/ai.proto."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "proto" / "shatra" / "ai" / "v1" / "ai.proto"
OUT = ROOT / "backend" / "proto"


def main() -> int:
    if not PROTO.is_file():
        print(f"Missing proto: {PROTO}", file=sys.stderr)
        return 1
    # Use grpcio-tools matching requirements.txt (protobuf 5.x). Protoc 6 stubs break runtime 5.x.
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "__init__.py").write_text('"""Generated gRPC stubs for shatra-ai."""\n', encoding="utf-8")
    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{ROOT / 'proto'}",
        f"--python_out={OUT}",
        f"--grpc_python_out={OUT}",
        str(PROTO.relative_to(ROOT / "proto")),
    ]
    print(" ".join(cmd))
    subprocess.run(cmd, cwd=ROOT / "proto", check=True)
    # Fix import path in generated grpc module (package layout).
    grpc_py = OUT / "shatra" / "ai" / "v1" / "ai_pb2_grpc.py"
    if grpc_py.is_file():
        text = grpc_py.read_text(encoding="utf-8")
        text = text.replace(
            "from shatra.ai.v1 import ai_pb2 as shatra_dot_ai_dot_v1_dot_ai__pb2",
            "from backend.proto.shatra.ai.v1 import ai_pb2 as shatra_dot_ai_dot_v1_dot_ai__pb2",
        )
        import re

        text = re.sub(
            r"GRPC_GENERATED_VERSION = '[^']+'",
            "GRPC_GENERATED_VERSION = '1.71.0'  # pinned to requirements.txt grpcio",
            text,
            count=1,
        )
        grpc_py.write_text(text, encoding="utf-8")
    for pkg in ("shatra", "shatra/ai", "shatra/ai/v1"):
        init = OUT / pkg / "__init__.py"
        init.parent.mkdir(parents=True, exist_ok=True)
        if not init.is_file():
            init.write_text("", encoding="utf-8")
    print(f"Generated stubs under {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
