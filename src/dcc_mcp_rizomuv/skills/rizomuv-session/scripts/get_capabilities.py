"""rizomuv-session / get_capabilities — supported formats and safety boundaries.

Parameter resolution order (dcc-mcp-core execute_script convention):
1. stdin JSON (no parameters for this tool)
2. CLI flags: none
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

from dcc_mcp_rizomuv.discovery import MIN_HEADLESS_VERSION  # noqa: E402
from dcc_mcp_rizomuv.driver import SUPPORTED_INPUT_EXTENSIONS, allowed_roots  # noqa: E402


def _force_utf8_stdio() -> None:
    """Deterministic output contract: stdout/stderr are always UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def run(params: dict) -> None:
    capabilities = {
        "input_formats": list(SUPPORTED_INPUT_EXTENSIONS),
        "operations": ["unfold", "pack", "unwrap_file", "unwrap_batch"],
        "min_headless_version": ".".join(str(part) for part in MIN_HEADLESS_VERSION),
        "allowed_roots": allowed_roots(),
        "boundaries": [
            "paths are confined to DCC_MCP_RIZOMUV_ALLOWED_ROOTS when set",
            "headless is not displayless: a desktop session is still required",
            "dialogs are auto-answered; an unrequested yes is answered no",
            "a failed command returns an Error dict rather than raising",
        ],
        "unsupported": ["alembic (.abc)", "interactive editing", "arbitrary Python execution"],
    }
    print(
        json.dumps(
            {"success": True, "message": "RizomUV adapter capabilities", "context": capabilities},
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
