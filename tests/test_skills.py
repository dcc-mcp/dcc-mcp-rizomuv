"""Skill catalogue tests.

A tools.yaml entry that points at a script which does not exist fails only when
someone invokes that tool -- far too late. Every declared tool is checked here.
"""

from __future__ import annotations

import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

SKILLS = Path(__file__).resolve().parents[1] / "src" / "dcc_mcp_rizomuv" / "skills"

FRONTMATTER_KEYS = ("name", "description", "license", "compatibility", "allowed-tools", "metadata")


@unittest.skipIf(yaml is None, "PyYAML is not installed")
class SkillCatalogueTest(unittest.TestCase):
    def test_every_skill_declares_its_tools_file(self):
        for skill_dir in sorted(SKILLS.iterdir()):
            if not skill_dir.is_dir():
                continue
            self.assertTrue((skill_dir / "SKILL.md").is_file(), skill_dir.name)
            self.assertTrue((skill_dir / "tools.yaml").is_file(), skill_dir.name)

    def test_every_declared_tool_script_exists(self):
        for skill_dir in sorted(SKILLS.iterdir()):
            tools_file = skill_dir / "tools.yaml"
            if not tools_file.is_file():
                continue
            catalogue = yaml.safe_load(tools_file.read_text(encoding="utf-8"))
            for tool in catalogue.get("tools", []):
                script = skill_dir / tool["source_file"]
                self.assertTrue(script.is_file(), "%s -> %s" % (skill_dir.name, tool["source_file"]))

    def test_every_tool_declares_a_schema_and_a_source(self):
        for skill_dir in sorted(SKILLS.iterdir()):
            tools_file = skill_dir / "tools.yaml"
            if not tools_file.is_file():
                continue
            catalogue = yaml.safe_load(tools_file.read_text(encoding="utf-8"))
            for tool in catalogue.get("tools", []):
                self.assertTrue(tool["name"])
                self.assertTrue(tool["description"])
                self.assertIn("input_schema", tool)
                self.assertEqual(tool["input_schema"]["type"], "object")


if __name__ == "__main__":
    unittest.main()
