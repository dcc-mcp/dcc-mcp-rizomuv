"""Packaging and repository-contract tests.

A024 wants release-please present and consistent; A003/A012 want an explicit
Core floor at or above the organisation baseline. Both are cheap to assert and
silent to get wrong, which is exactly why they are asserted.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_FLOOR_BASELINE = (0, 20, 36)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class ReleasePleaseTest(unittest.TestCase):
    def test_config_and_manifest_exist(self):
        self.assertTrue((ROOT / "release-please-config.json").is_file())
        self.assertTrue((ROOT / ".release-please-manifest.json").is_file())

    def test_manifest_version_matches_the_package(self):
        manifest = _read_json(ROOT / ".release-please-manifest.json")
        self.assertEqual(manifest["."], "0.1.0")

    def test_every_release_please_extra_file_exists(self):
        config = _read_json(ROOT / "release-please-config.json")
        extra = config["packages"]["."]["extra-files"]
        self.assertTrue(extra)
        for entry in extra:
            self.assertTrue((ROOT / entry["path"]).is_file(), entry["path"])


class CoreFloorTest(unittest.TestCase):
    def test_pyproject_declares_an_explicit_core_floor(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('"dcc-mcp-core>=', text)

    def test_core_floor_is_at_or_above_the_baseline(self):
        import re

        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'"dcc-mcp-core>=\s*([0-9]+)\.([0-9]+)\.([0-9]+)', text)
        self.assertIsNotNone(match, "no explicit dcc-mcp-core floor declared")
        version = tuple(int(part) for part in match.groups())
        self.assertGreaterEqual(version, CORE_FLOOR_BASELINE)


class ContractFileTest(unittest.TestCase):
    def test_agents_md_exists(self):
        self.assertTrue((ROOT / "AGENTS.md").is_file())

    def test_readme_and_license_exist(self):
        self.assertTrue((ROOT / "README.md").is_file())
        self.assertTrue((ROOT / "LICENSE").is_file())

    def test_no_agent_or_ide_directory_is_version_controlled(self):
        for name in (".claude", ".cursor", ".codex", ".windsurf", ".vscode", ".idea"):
            self.assertFalse((ROOT / name).is_dir(), name)


if __name__ == "__main__":
    unittest.main()
