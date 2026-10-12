"""rizomuv-uv / unwrap_file — unwrap and pack one mesh headlessly.

Parameter resolution order (dcc-mcp-core execute_script convention):
1. stdin JSON: {"path": ..., "output_path": ..., "pack": ...}
2. CLI flags: --path --output-path --pack/--no-pack
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

from dcc_mcp_rizomuv.driver import RizomuvError, RizomuvSession  # noqa: E402


def _force_utf8_stdio() -> None:
    """Deterministic output contract: stdout/stderr are always UTF-8.

    On Windows a piped subprocess stdout defaults to the ANSI codepage and fails
    on CJK text, and mesh paths are exactly where non-ASCII shows up.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def run(params: dict) -> None:
    if not isinstance(params, dict):
        print(
            json.dumps(
                {
                    "success": False,
                    "message": "expected a JSON object of parameters, got %s" % type(params).__name__,
                    "context": {},
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)
    path = params.get("path")
    if not path:
        print(
            json.dumps(
                {"success": False, "message": "a mesh path is required", "context": {}},
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    session = RizomuvSession()
    try:
        session.start()
        result = session.unwrap_file(path, params.get("output_path"), pack=params.get("pack", True))
    except RizomuvError as error:
        result = {"status": "error", "error": str(error)}
    except Exception as error:  # noqa: BLE001 - a tool reports, it does not traceback
        result = {"status": "error", "error": "unexpected failure: %s" % error}
    finally:
        session.close()

    if result.get("status") == "ok":
        print(
            json.dumps(
                {
                    "success": True,
                    "message": "unwrapped %s" % os.path.basename(result["path"]),
                    "context": {
                        "path": result["path"],
                        "output": result.get("output"),
                        "islands": result.get("islands"),
                    },
                },
                ensure_ascii=False,
            )
        )
        return
    print(
        json.dumps(
            {"success": False, "message": result.get("error", "unwrap failed"), "context": {}},
            ensure_ascii=False,
        )
    )
    sys.exit(1)


def main() -> None:
    _force_utf8_stdio()
    params: dict = {}
    payload_seen = False
    if not sys.stdin.isatty():
        raw = sys.stdin.read()
        if raw.strip():
            payload_seen = True
            try:
                params = json.loads(raw)
            except json.JSONDecodeError:
                params = {}
    if not params and not payload_seen:
        # No payload at all, so this is a human at a terminal: fall back to
        # flags. A payload that arrived but is empty is a caller bug and must
        # still produce an envelope, not argparse usage text on stdout.
        parser = argparse.ArgumentParser(description="Unwrap and pack one mesh headlessly")
        parser.add_argument("--path", required=True, help="mesh to unwrap")
        parser.add_argument("--output-path", dest="output_path", default=None)
        parser.add_argument("--pack", dest="pack", action=argparse.BooleanOptionalAction, default=True)
        params = vars(parser.parse_args())
    run(params)


if __name__ == "__main__":
    main()
