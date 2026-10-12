"""Locate a RizomUV installation and the RizomUVLink package it ships.

RizomUV has no command-line scripting entry point. The supported automation path
is RizomUVLink, a Python package that drives a running RizomUV instance over IPC.
That package ships inside the RizomUV installation itself, so the adapter has to
find the installation before it can import the bridge.

There is no registration mechanism on Linux: the AppImage has no install
location, so the caller points at it with ``RIZOMUV_EXE`` or ``RIZOMUV_LINK_DIR``.
"""

from __future__ import annotations

import os
import platform
import re
from pathlib import Path
from typing import Optional, Tuple

# RizomUVLink has shipped with RizomUV since 2022.2.
_MIN_LINK_VERSION = (2022, 2)

# Headless mode landed in 2027.0.417; the -bg flag (no foreground steal) in
# 2027.0.297. An older build given -hl answers a command line it cannot parse
# with a message box nobody is there to dismiss, so we refuse to launch it.
MIN_HEADLESS_VERSION = (2027, 0, 417)
MIN_BACKGROUND_VERSION = (2027, 0, 297)

_WIN_REGISTRY_ROOT = "SOFTWARE\\Rizom Lab"
_WIN_KEY_PATTERN = r"RizomUV VS RS ([0-9]+)\.([0-9]+)"


def _parse_version(text: str) -> Tuple[int, ...]:
    """Extract the leading dotted-integer version from a string.

    RizomUV reports versions like ``2027.0.598`` and install directories carry a
    two-part ``2027.0``. Both compare correctly as integer tuples, and comparing
    as integers is what makes ``2027.10`` rank above ``2027.2``.
    """
    parts = re.findall(r"\d+", text or "")
    return tuple(int(part) for part in parts[:3]) or (0,)


def windows_install_dirs() -> list:
    """Installed RizomUV directories on Windows, newest first.

    Every setup registers its installation directory, so the registry is the
    reliable lookup. Returns an empty list anywhere else.
    """
    if platform.system() != "Windows":
        return []
    try:
        import winreg
    except ImportError:  # pragma: no cover - non-Windows
        return []

    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _WIN_REGISTRY_ROOT)
    except OSError:
        return []

    versions = []
    with root:
        index = 0
        while True:
            try:
                name = winreg.EnumKey(root, index)
            except OSError:  # no more subkeys
                break
            index += 1
            match = re.fullmatch(_WIN_KEY_PATTERN, name)
            if not match:
                continue
            version = (int(match.group(1)), int(match.group(2)))
            if version >= _MIN_LINK_VERSION:
                versions.append((version, name))

    found = []
    for _version, name in sorted(versions, reverse=True):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _WIN_REGISTRY_ROOT + "\\" + name) as key:
                exe_path = winreg.QueryValue(key, "rizomuv.exe")
        except OSError:
            continue
        if exe_path:
            found.append(os.path.dirname(exe_path))
    return found


def macos_install_dirs() -> list:
    """Versioned RizomUV application bundles on macOS, newest first."""
    if platform.system() != "Darwin":
        return []
    bundles = list(Path("/Applications").glob("RizomUV*.app"))
    bundles.sort(key=lambda path: _parse_version(path.name), reverse=True)
    return [str(bundle) for bundle in bundles]


def link_package_dirs() -> list:
    """Candidate RizomUVLink package directories, most preferred first.

    ``RIZOMUV_LINK_DIR`` wins outright because on Linux the package has to be
    extracted from the AppImage by hand; there is nothing to discover.
    """
    override = os.environ.get("RIZOMUV_LINK_DIR")
    if override:
        return [override]

    dirs = []
    for install_dir in windows_install_dirs():
        dirs.append(os.path.join(install_dir, "RizomUVLink"))
    for bundle in macos_install_dirs():
        dirs.append(os.path.join(bundle, "Contents", "Resources", "RizomUVLink"))
    return dirs


def executable_candidates() -> list:
    """Candidate RizomUV executables, most preferred first."""
    override = os.environ.get("RIZOMUV_EXE")
    if override:
        return [override]

    system = platform.system()
    found = []
    if system == "Windows":
        for install_dir in windows_install_dirs():
            found.append(os.path.join(install_dir, "RizomUV.exe"))
    elif system == "Darwin":
        for bundle in macos_install_dirs():
            found.append(os.path.join(bundle, "Contents", "MacOS", "RizomUV"))
    return found


def import_link_module():
    """Import and return the RizomUVLink module, or None when it is unavailable.

    The package cannot be asked where it lives before it is imported, so the
    search path is primed from the discovered installations first.
    """
    import sys

    for directory in link_package_dirs():
        if directory not in sys.path:
            sys.path.insert(0, directory)
    try:
        from RizomUVLink import CRizomUVLink, CZEx  # noqa: F401
    except ImportError:
        return None
    import RizomUVLink

    return RizomUVLink


def headless_supported(version: Optional[str]) -> bool:
    """Whether a reported RizomUV version is new enough for headless batch work."""
    if not version:
        return False
    return _parse_version(version) >= MIN_HEADLESS_VERSION
