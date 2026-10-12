from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from dcc_mcp_core import DccServerOptions
from dcc_mcp_core.server_base import DccServerBase

from .__version__ import __version__

_server: Optional["RizomuvMcpServer"] = None


class _ArgumentFailure(Exception):
    pass


class _LifecycleParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _ArgumentFailure(message)


class RizomuvMcpServer(DccServerBase):
    def __init__(self, port: Optional[int] = None):
        options = DccServerOptions.from_env(
            "rizomuv",
            Path(__file__).parent / "skills",
            port=port,
            server_name="dcc-mcp-rizomuv",
            server_version=__version__,
            adapter_version=__version__,
        )
        super().__init__(options=options)

    def _version_string(self):
        return __version__


def start_server(port: Optional[int] = None):
    global _server
    if _server is None or not _server.is_running:
        _server = RizomuvMcpServer(port)
        _server.register_builtin_actions()
        _server.start()
    return _server


def stop_server():
    global _server
    if _server is not None:
        _server.stop()
        _server = None


def _build_parser() -> argparse.ArgumentParser:
    parser = _LifecycleParser(description="Run or inspect the RizomUV adapter lifecycle.")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for operation in ("doctor", "status"):
        command = subparsers.add_parser(operation, help="Report whether headless RizomUV is usable here.")
        command.add_argument("--json", action="store_true", dest="json_output")
    return parser


def _print_result(result: Mapping[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(result, sort_keys=True))
        return
    print("%s: %s" % (result.get("status", "unknown"), result.get("reason", "")))
    for step in result.get("next_steps", []):
        command = step.get("command") if isinstance(step, Mapping) else None
        if isinstance(command, list):
            print("next: %s" % " ".join(str(part) for part in command))


def _run_server() -> None:
    event = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: event.set())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: event.set())
    start_server()
    try:
        event.wait()
    finally:
        stop_server()


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the no-argument service or report the headless readiness."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        _run_server()
        return 0
    try:
        args = _build_parser().parse_args(arguments)
    except _ArgumentFailure:
        _print_result(
            {"status": "error", "reason": "unrecognised arguments"},
            json_output=True,
        )
        return 2
    from .doctor import run_doctor

    result = run_doctor()
    _print_result(result, json_output=args.json_output)
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
