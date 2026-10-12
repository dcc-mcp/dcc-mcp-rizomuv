"""rizomuv-uv / unwrap_batch — unwrap a folder of meshes headlessly.

Parameter resolution order (dcc-mcp-core execute_script convention):
1. stdin JSON: {"paths": [...], "output_dir": ..., "pack": ...}
2. CLI flags: --output-dir --path (repeatable) --pack/--no-pack
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
    paths = params.get("paths") or []
    output_dir = params.get("output_dir")
    if not paths or not output_dir:
        print(
            json.dumps(
                {
                    "success": False,
                    "message": "an output directory and at least one mesh are required",
                    "context": {},
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    session = RizomuvSession()
    try:
        session.start()
        result = session.unwrap_batch(paths, output_dir, pack=params.get("pack", True))
    except RizomuvError as error:
        result = {"status": "error", "error": str(error)}
    except Exception as error:  # noqa: BLE001 - a tool reports, it does not traceback
        result = {"status": "error", "error": "unexpected failure: %s" % error}
    finally:
        session.close()

    succeeded = result.get("succeeded", 0)
    failed = result.get("failed", 0)
    ok = result.get("status") == "ok"
    print(
        json.dumps(
            {
                "success": ok,
                "message": "%d unwrapped, %d failed" % (succeeded, failed),
                "context": {
                    "output_dir": result.get("output_dir"),
                    "requested": result.get("requested", 0),
                    "succeeded": succeeded,
                    "failed": failed,
                    "results": result.get("results", []),
                },
            },
            ensure_ascii=False,
        )
    )
    if not ok:
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
        parser = argparse.ArgumentParser(description="Unwrap a folder of meshes headlessly")
        parser.add_argument("--output-dir", dest="output_dir", required=True)
        parser.add_argument("--path", dest="paths", action="append", default=[])
        parser.add_argument("--pack", dest="pack", action=argparse.BooleanOptionalAction, default=True)
        params = vars(parser.parse_args())
    run(params)


if __name__ == "__main__":
    main()
