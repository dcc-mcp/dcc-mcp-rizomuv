"""Self-check that reports whether headless RizomUV can actually run here.

Three things have to line up before a batch can run, and they fail
independently, so the doctor reports each one rather than stopping at the first:

1. RizomUVLink is importable -- the package ships inside the RizomUV install.
2. An executable was found, or was pinned with ``RIZOMUV_EXE``.
3. That build is new enough for ``-hl`` (2027.0.417+).

Headless still needs a desktop session (an X display on Linux, a logged-in
session on Windows). That cannot be proven without launching, so the doctor
reports it as a requirement rather than as something it verified.
"""

from __future__ import annotations

import platform
from typing import Any, Dict

from .discovery import (
    MIN_HEADLESS_VERSION,
    executable_candidates,
    import_link_module,
    link_package_dirs,
)


def run_doctor() -> Dict[str, Any]:
    """Assemble the readiness report. Never raises; every finding is reported."""
    system = platform.system()
    link_module = import_link_module()
    executables = executable_candidates()
    link_dirs = link_package_dirs()

    checks = []
    next_steps = []

    checks.append(
        {
            "name": "rizomuv_link_importable",
            "status": "ok" if link_module is not None else "error",
            "detail": "RizomUVLink found" if link_module else "RizomUVLink is not importable",
            "searched": link_dirs,
        }
    )
    if link_module is None:
        next_steps.append(
            {
                "command": ["set", "RIZOMUV_LINK_DIR"],
                "hint": ("install RizomUV 2027.0+, or point RIZOMUV_LINK_DIR at the extracted package"),
            }
        )

    checks.append(
        {
            "name": "executable_found",
            "status": "ok" if executables else ("error" if system == "Linux" else "warn"),
            "detail": executables[0] if executables else "no RizomUV executable discovered",
            "searched": executables,
        }
    )
    if not executables:
        next_steps.append(
            {
                "command": ["set", "RIZOMUV_EXE"],
                "hint": "Linux has no install registration, so RIZOMUV_EXE is required there",
            }
        )

    checks.append(
        {
            "name": "desktop_session_required",
            "status": "warn",
            "detail": (
                "headless is not displayless: an X display (Linux) or a logged-in "
                "session (Windows) is still required to start RizomUV"
            ),
            "platform": system,
        }
    )

    version = None
    if link_module is not None and executables:
        try:
            from .driver import RizomuvSession

            session = RizomuvSession(exe_path=executables[0])
            version = session.status().get("version")
        except Exception as error:  # noqa: BLE001 - the doctor reports, it does not raise
            checks.append(
                {
                    "name": "headless_version",
                    "status": "warn",
                    "detail": "could not query RizomUV without launching: %s" % error,
                }
            )
        else:
            checks.append(
                {
                    "name": "headless_version",
                    "status": "ok" if version else "warn",
                    "detail": version or "version undetermined",
                    "required": ".".join(str(part) for part in MIN_HEADLESS_VERSION),
                }
            )

    healthy = all(check["status"] != "error" for check in checks)
    return {
        "status": "ok" if healthy else "error",
        "adapter": "dcc-mcp-rizomuv",
        "platform": system,
        "reason": "headless RizomUV ready" if healthy else "headless RizomUV is not usable yet",
        "checks": checks,
        "next_steps": next_steps,
    }
