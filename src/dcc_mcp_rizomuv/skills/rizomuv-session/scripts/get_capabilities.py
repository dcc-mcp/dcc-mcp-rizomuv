"""Report the supported formats, operations, and headless safety boundaries."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

from dcc_mcp_rizomuv.discovery import MIN_HEADLESS_VERSION  # noqa: E402
from dcc_mcp_rizomuv.driver import SUPPORTED_INPUT_EXTENSIONS, allowed_roots  # noqa: E402


def main() -> int:
    print(
        json.dumps(
            {
                "input_formats": list(SUPPORTED_INPUT_EXTENSIONS),
                "operations": ["unfold", "pack", "unwrap_file", "unwrap_batch"],
                "min_headless_version": ".".join(str(part) for part in MIN_HEADLESS_VERSION),
                "allowed_roots": allowed_roots(),
                "boundaries": [
                    "paths are confined to DCC_MCP_RIZOMUV_ALLOWED_ROOTS when set",
                    "headless is not displayless: a desktop session is still required",
                    "dialogs are auto-answered; an unrequested yes is answered no",
                    "a failed Load returns an Error dict rather than raising",
                ],
                "unsupported": [
                    "alembic (.abc)",
                    "interactive editing",
                    "arbitrary Python execution",
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
