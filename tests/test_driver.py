"""Driver tests.

The error contract is the part worth testing without a licence: a failed Load
returns ``{"Error": ...}`` instead of raising, and path confinement is enforced
by the adapter rather than delegated to RizomUV.
"""

from __future__ import annotations

import os
import unittest

from dcc_mcp_rizomuv.discovery import _parse_version, headless_supported
from dcc_mcp_rizomuv.driver import RizomuvError, _error_from_result, resolve_path


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

    def test_empty_path_is_refused(self):
        with self.assertRaises(RizomuvError):
            resolve_path("   ")


if __name__ == "__main__":
    unittest.main()
