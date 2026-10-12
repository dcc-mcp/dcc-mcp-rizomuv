"""rizomuv-session / get_status — report whether headless RizomUV can run here.

Read-only: it inspects the installation without launching RizomUV.

Parameter resolution order (dcc-mcp-core execute_script convention):
1. stdin JSON (no parameters for this tool)
2. CLI flags: none
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

from dcc_mcp_rizomuv.driver import RizomuvError, RizomuvSession  # noqa: E402


def _force_utf8_stdio() -> None:
    """Deterministic output contract: stdout/stderr are always UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def run(params: dict) -> None:
    session = RizomuvSession()
    try:
        result = session.status()
    except RizomuvError as error:
        print(
            json.dumps(
                {"success": False, "message": str(error), "context": {}},
                ensure_ascii=False,
            )
        )
        sys.exit(1)
    print(
        json.dumps(
            {
                "success": True,
                "message": result.get("status", "unknown"),
                "context": result,
            },
            ensure_ascii=False,
        )
    )


def main() -> None:
    _force_utf8_stdio()
    params: dict = {}
    if not sys.stdin.isatty():
        raw = sys.stdin.read()
        if raw.strip():
            try:
                params = json.loads(raw)
            except json.JSONDecodeError:
                params = {}
    run(params)


if __name__ == "__main__":
    main()
