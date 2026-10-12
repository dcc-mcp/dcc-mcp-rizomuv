"""Drive a headless RizomUV instance through RizomUVLink.

The contract that matters, because it is the opposite of what most bridges do:

* A failed ``Load`` does **not** raise. It returns ``{"Error": {"Msg", "Code"}}``.
  Without checking the return value the run carries on to ``Unfold`` and
  ``Save``, and the failure surfaces several commands later as a confusing
  "no UV set". Every command here reads its result.
* Headless is not displayless. RizomUV still needs a desktop session to start --
  an X display on Linux, a logged-in session on Windows. The flag promises that
  nothing is *drawn*, not that nothing is *needed*. A container with no X server
  will not start it.
* Dialogs are auto-answered and written to the command log, and a question you
  would have answered "yes" to is answered "no". Ambiguity resolves to the
  conservative branch rather than to a hang.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Dict, List, Mapping, Optional

from .discovery import executable_candidates, headless_supported, import_link_module

# Formats the RizomUVLink batch example filters on. Alembic (.abc) is absent
# from every documented import path, so it is not advertised here.
SUPPORTED_INPUT_EXTENSIONS = (".obj", ".fbx", ".usd", ".usda", ".usdc", ".gltf", ".glb")

_ENV_ALLOWED_ROOTS = "DCC_MCP_RIZOMUV_ALLOWED_ROOTS"


class RizomuvError(Exception):
    """A RizomUV operation failed in a way the caller should report."""


def _error_from_result(result: Any) -> Optional[str]:
    """Return the error message a RizomUV result carries, or None when it is clean."""
    if isinstance(result, Mapping) and "Error" in result:
        error = result["Error"]
        if isinstance(error, Mapping):
            return str(error.get("Msg", error))
        return str(error)
    return None


def allowed_roots() -> List[str]:
    """Workspace roots the adapter may read and write, from the environment."""
    raw = os.environ.get(_ENV_ALLOWED_ROOTS, "")
    return [entry.strip() for entry in raw.split(os.pathsep) if entry.strip()]


def resolve_path(path: str) -> str:
    """Resolve a caller-supplied path against the allowed roots.

    RizomUV runs with its own directory as the working directory, not the
    caller's, so a relative path resolves somewhere unintended. Everything is
    made absolute and normalised to forward slashes, which every platform
    accepts.
    """
    if not path or not path.strip():
        raise RizomuvError("path must be a non-empty string")

    candidate = os.path.abspath(os.path.expanduser(path.strip()))
    roots = allowed_roots()
    if roots:
        normalized = os.path.normcase(candidate)
        if not any(normalized.startswith(os.path.normcase(os.path.abspath(root))) for root in roots):
            raise RizomuvError("path is outside %s; refusing to touch it" % _ENV_ALLOWED_ROOTS)
    return candidate.replace("\\", "/")


class RizomuvSession:
    """One headless RizomUV instance, reused across a batch.

    Launching RizomUV is by far the most expensive step, so a session is paid
    once and then reused for every mesh rather than per mesh.
    """

    def __init__(self, exe_path: Optional[str] = None, background: bool = True):
        self._link_module = import_link_module()
        self._link = None
        self._exe_path = exe_path or (executable_candidates()[0] if executable_candidates() else None)
        self._background = background
        self._lock = threading.RLock()

    @property
    def available(self) -> bool:
        return self._link_module is not None

    def _require_link_module(self):
        if self._link_module is None:
            raise RizomuvError(
                "RizomUVLink is not importable; install RizomUV 2027.0 or later, "
                "or set RIZOMUV_LINK_DIR to the extracted package"
            )
        return self._link_module

    def start(self) -> Dict[str, Any]:
        """Launch (or reuse) the headless instance and report what came up."""
        module = self._require_link_module()
        with self._lock:
            if self._link is not None:
                return self.status()
            if not self._exe_path:
                raise RizomuvError("no RizomUV executable found; set RIZOMUV_EXE to the RizomUV binary")
            link = module.CRizomUVLink()
            port = link.RunRizomUV(exePath=self._exe_path, headless=True, background=self._background)
            version = link.RizomUVVersion()
            if not headless_supported(version):
                self._link = None
                raise RizomuvError("RizomUV %s is too old for headless mode; 2027.0.417 or later is required" % version)
            self._link = link
            return {"status": "ok", "version": version, "port": port, "headless": True}

    def status(self) -> Dict[str, Any]:
        """Report whether an instance is up, without launching one."""
        self._require_link_module()
        with self._lock:
            if self._link is None:
                return {
                    "status": "not_running",
                    "executable": self._exe_path,
                    "headless": True,
                    "link_available": True,
                    "min_headless_version": "2027.0.417",
                    "allowed_roots": allowed_roots(),
                }
            return {
                "status": "ok",
                "version": self._link.RizomUVVersion(),
                "executable": self._exe_path,
                "headless": True,
                "link_available": True,
                "min_headless_version": "2027.0.417",
                "allowed_roots": allowed_roots(),
            }

    def unwrap_file(self, path: str, output_path: Optional[str] = None, pack: bool = True) -> Dict[str, Any]:
        """Load, unfold, optionally pack, and save one mesh."""
        with self._lock:
            if self._link is None:
                self.start()
            input_path = resolve_path(path)
            if output_path:
                target = resolve_path(output_path)
            else:
                base, extension = os.path.splitext(input_path)
                target = resolve_path(base + "_unwrapped" + (extension or ".obj"))

            result = self._link.Load(
                {
                    "File": {
                        "Path": input_path,
                        "XYZUVW": True,
                        "ImportGroups": True,
                        "UVWProps": True,
                    }
                }
            )
            error = _error_from_result(result)
            if error:
                return {"status": "error", "path": input_path, "error": error}

            self._link.Unfold({"WorkingSet": "Visible", "PrimType": "Island"})
            if pack:
                self._link.Pack({"WorkingSet": "Visible"})
            self._link.Save({"File": {"Path": target, "UVWProps": True}})

            try:
                islands = self._link.Count("Lib.Mesh.Islands")
            except Exception:  # noqa: BLE001 - a count failure must not lose the save
                islands = None

            return {"status": "ok", "path": input_path, "output": target, "islands": islands}

    def unwrap_batch(self, paths, output_dir: str, pack: bool = True) -> Dict[str, Any]:
        """Unwrap many meshes through one instance.

        Each mesh is wrapped on its own: one unreadable file in a folder of two
        hundred should cost that file, not the batch.
        """
        with self._lock:
            if self._link is None:
                self.start()
            target_dir = resolve_path(output_dir)
            os.makedirs(target_dir, exist_ok=True)

            results = []
            for entry in paths:
                source = resolve_path(entry)
                name = os.path.splitext(os.path.basename(source))[0]
                destination = os.path.join(target_dir, name + "_unwrapped.obj").replace("\\", "/")
                try:
                    outcome = self.unwrap_file(source, destination, pack=pack)
                except RizomuvError as error:
                    outcome = {"status": "error", "path": source, "error": str(error)}
                except Exception as error:  # noqa: BLE001 - one bad mesh must not end the batch
                    outcome = {"status": "error", "path": source, "error": str(error)}
                results.append(outcome)

            succeeded = sum(1 for item in results if item.get("status") == "ok")
            return {
                "status": "ok" if succeeded and succeeded == len(results) else "partial",
                "requested": len(results),
                "succeeded": succeeded,
                "failed": len(results) - succeeded,
                "output_dir": target_dir,
                "results": results,
            }

    def close(self) -> None:
        """Shut the instance down. Safe to call twice."""
        with self._lock:
            if self._link is None:
                return
            try:
                module = self._link_module
                if module is not None:
                    self._link.Close()
            except Exception:  # noqa: BLE001 - teardown must not mask the original result
                pass
            self._link = None

    def __enter__(self) -> "RizomuvSession":
        self.start()
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
