"""Driver tests.

The error contract is the part worth testing without a licence: a failed Load
returns ``{"Error": ...}`` instead of raising, and path confinement is enforced
by the adapter rather than delegated to RizomUV.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest

from dcc_mcp_rizomuv.discovery import _parse_version, headless_supported
from dcc_mcp_rizomuv.driver import (
    _ENV_ALLOWED_ROOTS,
    RizomuvError,
    RizomuvSession,
    _error_from_result,
    resolve_path,
)


class ErrorContractTest(unittest.TestCase):
    def test_error_dict_is_read_out_of_a_result(self):
        self.assertEqual(_error_from_result({"Error": {"Msg": "bad file", "Code": 3}}), "bad file")

    def test_clean_result_yields_no_error(self):
        self.assertIsNone(_error_from_result({"Islands": 12}))
        self.assertIsNone(_error_from_result(None))
        self.assertIsNone(_error_from_result("ok"))


class VersionGateTest(unittest.TestCase):
    def test_versions_compare_as_integers(self):
        self.assertGreater(_parse_version("2027.10"), _parse_version("2027.2"))

    def test_headless_requires_the_minimum_build(self):
        self.assertTrue(headless_supported("2027.0.598"))
        self.assertTrue(headless_supported("2027.0.417"))
        self.assertFalse(headless_supported("2027.0.416"))
        self.assertFalse(headless_supported("2022.2"))
        self.assertFalse(headless_supported(None))
        self.assertFalse(headless_supported(""))


class CommandResultTest(unittest.TestCase):
    """A failed command must not be reported as success.

    Load was the only command reading its result, so a Save that failed still
    reported ok with an output path that was never written.
    """

    def _session(self, link):
        import threading

        session = RizomuvSession.__new__(RizomuvSession)
        session._link = link
        session._lock = threading.RLock()
        session._link_module = object()
        session._exe_path = "x"
        return session

    def test_every_command_result_is_read(self):
        class SaveFails:
            def __init__(self):
                self.commands = []

            def Load(self, _p):
                return {"ok": 1}

            def Unfold(self, _p):
                return {"ok": 1}

            def Pack(self, _p):
                return {"ok": 1}

            def Save(self, _p):
                return {"Error": {"Msg": "read-only filesystem", "Code": 5}}

        link = SaveFails()
        result = self._session(link).unwrap_file("a.obj", "out.obj")
        self.assertEqual(result["status"], "error")
        self.assertIn("read-only filesystem", result["error"])

    def test_pack_false_skips_the_pack_command(self):
        class Recorder:
            def __init__(self):
                self.commands = []

            def Load(self, _p):
                return {"ok": 1}

            def Unfold(self, _p):
                self.commands.append("Unfold")
                return {"ok": 1}

            def Pack(self, _p):
                self.commands.append("Pack")
                return {"ok": 1}

            def Save(self, _p):
                self.commands.append("Save")
                return {"ok": 1}

            def Count(self, _q):
                return 3

        link = Recorder()
        self._session(link).unwrap_file("a.obj", "out.obj", pack=False)
        self.assertEqual(link.commands, ["Unfold", "Save"])

    def test_pack_true_includes_the_pack_command(self):
        class Recorder:
            def __init__(self):
                self.commands = []

            def Load(self, _p):
                return {"ok": 1}

            def Unfold(self, _p):
                self.commands.append("Unfold")
                return {"ok": 1}

            def Pack(self, _p):
                self.commands.append("Pack")
                return {"ok": 1}

            def Save(self, _p):
                self.commands.append("Save")
                return {"ok": 1}

            def Count(self, _q):
                return 3

        link = Recorder()
        self._session(link).unwrap_file("a.obj", "out.obj", pack=True)
        self.assertEqual(link.commands, ["Unfold", "Pack", "Save"])

    def test_an_empty_batch_is_refused_rather_than_reported_as_success(self):
        import threading

        session = RizomuvSession.__new__(RizomuvSession)
        session._link = None
        session._lock = threading.RLock()
        session._link_module = object()
        session._exe_path = "x"
        with self.assertRaises(RizomuvError):
            session.unwrap_batch([], "out")


class PathConfinementTest(unittest.TestCase):
    def setUp(self):
        self._roots = os.environ.get("DCC_MCP_RIZOMUV_ALLOWED_ROOTS")
        os.environ["DCC_MCP_RIZOMUV_ALLOWED_ROOTS"] = os.path.abspath(os.sep + "allowed")

    def tearDown(self):
        if self._roots is None:
            os.environ.pop("DCC_MCP_RIZOMUV_ALLOWED_ROOTS", None)
        else:
            os.environ["DCC_MCP_RIZOMUV_ALLOWED_ROOTS"] = self._roots

    def test_path_inside_the_allowed_root_is_accepted(self):
        resolved = resolve_path(os.path.join(os.path.abspath(os.sep + "allowed"), "mesh.obj"))
        self.assertTrue(resolved.endswith("/mesh.obj") or resolved.endswith("\\mesh.obj"))
        self.assertIn("allowed", resolved)

    def test_path_outside_the_allowed_root_is_refused(self):
        with self.assertRaises(RizomuvError):
            resolve_path(os.path.join(os.path.abspath(os.sep + "elsewhere"), "mesh.obj"))

    def test_sibling_directory_prefix_cannot_escape_the_root(self):
        """`allowed_evil` and `allowed2` share a text prefix with `allowed`.

        A startswith check accepts both, which is a workspace escape. These are
        the positive controls the original confinement test was missing.
        """
        for sibling in ("allowed_evil", "allowed2", "allowe"):
            with self.assertRaises(RizomuvError, msg=sibling):
                resolve_path(os.path.join(os.path.abspath(os.sep + sibling), "mesh.obj"))

    def test_a_subdirectory_of_the_root_is_accepted(self):
        resolve_path(os.path.join(os.path.abspath(os.sep + "allowed"), "sub", "mesh.obj"))

    def test_a_symlink_inside_the_root_cannot_reach_outside_it(self):
        """A link is the second escape layer: abspath is purely lexical.

        Windows needs developer mode or elevation for os.symlink, so an
        OSError skips rather than asserting behaviour that never happened.
        """
        root = tempfile.mkdtemp(prefix="rizomuv_jail_")
        self.addCleanup(shutil.rmtree, root, True)
        allowed = os.path.join(root, "allowed")
        secret = os.path.join(root, "secret")
        os.makedirs(allowed)
        os.makedirs(secret)
        outside = os.path.join(secret, "mesh.obj")
        with open(outside, "w") as handle:
            handle.write("x")
        link = os.path.join(allowed, "escape")
        try:
            os.symlink(secret, link, target_is_directory=True)
        except (OSError, NotImplementedError, AttributeError) as error:
            self.skipTest("symlinks unavailable here: %s" % error)
        if not os.path.islink(link):
            self.skipTest("symlink was not created")

        previous = os.environ.get(_ENV_ALLOWED_ROOTS)
        os.environ[_ENV_ALLOWED_ROOTS] = allowed
        self.addCleanup(
            lambda: (
                os.environ.pop(_ENV_ALLOWED_ROOTS, None)
                if previous is None
                else os.environ.__setitem__(_ENV_ALLOWED_ROOTS, previous)
            )
        )
        with self.assertRaises(RizomuvError):
            resolve_path(os.path.join(link, "mesh.obj"))

    def test_empty_path_is_refused(self):
        with self.assertRaises(RizomuvError):
            resolve_path("   ")


if __name__ == "__main__":
    unittest.main()
