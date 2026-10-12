"""Report whether headless RizomUV is usable on this machine.

Read-only: it inspects the installation without launching RizomUV.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

from dcc_mcp_rizomuv.driver import RizomuvError, RizomuvSession  # noqa: E402


def main() -> int:
    session = RizomuvSession()
    try:
        result = session.status()
    except RizomuvError as error:
        print(json.dumps({"status": "error", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
