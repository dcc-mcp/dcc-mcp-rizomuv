"""Doctor self-check tests.

These run without a RizomUV installation: the doctor reports, it does not raise,
so an absent runtime has to come back as a structured report rather than an
exception. A013 wants the module present; these tests want it honest.
"""

from __future__ import annotations

import unittest

from dcc_mcp_rizomuv.doctor import run_doctor


class DoctorReportTest(unittest.TestCase):
    def test_report_is_structured_and_never_raises(self):
        report = run_doctor()

        self.assertIn(report["status"], ("ok", "error"))
        self.assertEqual(report["adapter"], "dcc-mcp-rizomuv")
        self.assertIsInstance(report["checks"], list)
        self.assertIsInstance(report["next_steps"], list)

    def test_every_check_names_itself_and_states_a_status(self):
        for check in run_doctor()["checks"]:
            self.assertTrue(check["name"])
            self.assertIn(check["status"], ("ok", "warn", "error"))
            self.assertIn("detail", check)

    def test_failed_checks_produce_a_next_step(self):
        report = run_doctor()
        if report["status"] == "error":
            self.assertTrue(report["next_steps"])

    def test_desktop_session_requirement_is_always_reported(self):
        names = [check["name"] for check in run_doctor()["checks"]]
        self.assertIn("desktop_session_required", names)


if __name__ == "__main__":
    unittest.main()
