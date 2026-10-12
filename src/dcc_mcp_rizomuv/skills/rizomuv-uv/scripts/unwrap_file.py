"""Unwrap and pack one mesh through a headless RizomUV instance.

Usage:
    python unwrap_file.py <path> [output_path]
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

from dcc_mcp_rizomuv.driver import RizomuvError, RizomuvSession  # noqa: E402


def main(argv=None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        print(json.dumps({"status": "error", "error": "a mesh path is required"}, sort_keys=True))
        return 2
    path = arguments[0]
    output_path = arguments[1] if len(arguments) > 1 else None

    session = RizomuvSession()
    try:
        session.start()
        result = session.unwrap_file(path, output_path)
    except RizomuvError as error:
        result = {"status": "error", "error": str(error)}
    except Exception as error:  # noqa: BLE001 - a tool reports, it does not traceback
        result = {"status": "error", "error": "unexpected failure: %s" % error}
    finally:
        session.close()
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
