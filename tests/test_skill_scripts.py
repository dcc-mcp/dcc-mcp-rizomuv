"""Skill script smoke tests.

The other suites test the library layers only, which is how a broken parameter
contract reached main under a green CI. These execute the skill scripts the way
the MCP executor does: as subprocesses fed a JSON payload on stdin.

They assert the *contract* -- parameters are accepted from stdin, and the output
is a ToolResultEnvelope -- not a successful unwrap, which needs a licensed
RizomUV 2027 runtime that CI does not have.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "src" / "dcc_mcp_rizomuv" / "skills"


def run_script(script: Path, payload: dict):
    """Run a skill script as the executor does and return (returncode, stdout)."""
    completed = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(script.parent),
    )
    return completed.returncode, completed.stdout.strip()


class SkillScriptContractTest(unittest.TestCase):
    """Every tool script honours the stdin-JSON + ToolResultEnvelope contract."""

    def test_unwrap_file_reads_its_path_from_stdin(self):
        code, out = run_script(
            SKILLS / "rizomuv-uv" / "scripts" / "unwrap_file.py",
            {"path": "C:/meshes/a.obj"},
        )
        payload = json.loads(out)
        # The old positional-argv script answered "a mesh path is required" even
        # though the path was supplied; reaching the runtime proves it arrived.
        self.assertNotIn("is required", payload.get("message", ""))
        self.assertIsInstance(payload.get("success"), bool)

    def test_unwrap_batch_reads_paths_and_output_dir_from_stdin(self):
        code, out = run_script(
            SKILLS / "rizomuv-uv" / "scripts" / "unwrap_batch.py",
            {"paths": ["a.obj", "b.fbx"], "output_dir": "out"},
        )
        payload = json.loads(out)
        self.assertNotIn("is required", payload.get("message", ""))
        self.assertIsInstance(payload.get("success"), bool)

    def test_missing_required_parameter_fails_rather_than_hanging(self):
        code, out = run_script(SKILLS / "rizomuv-uv" / "scripts" / "unwrap_file.py", {})
        payload = json.loads(out)
        self.assertFalse(payload["success"])
        self.assertEqual(code, 1)

    def test_every_script_emits_a_tool_result_envelope(self):
        scripts = sorted(SKILLS.glob("*/scripts/*.py"))
        self.assertTrue(scripts)
        for script in scripts:
            with self.subTest(script=script.name):
                code, out = run_script(script, {})
                self.assertTrue(out, "%s printed nothing" % script.name)
                payload = json.loads(out)
                self.assertIn("success", payload)
                self.assertIsInstance(payload["success"], bool)
                self.assertIn("message", payload)
                self.assertIsInstance(payload["message"], str)
                self.assertIn("context", payload)

    def test_non_ascii_path_is_reported_without_crashing_on_windows(self):
        """A piped stdout defaults to the ANSI codepage and breaks on CJK text."""
        code, out = run_script(
            SKILLS / "rizomuv-uv" / "scripts" / "unwrap_file.py",
            {"path": "C:/网格/立方体.obj"},
        )
        payload = json.loads(out)  # a UnicodeEncodeError would have printed nothing
        self.assertIsInstance(payload.get("success"), bool)
