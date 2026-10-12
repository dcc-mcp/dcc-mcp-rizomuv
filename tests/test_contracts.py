"""Packaging and repository-contract tests.

A024 wants release-please present and consistent; A003/A012 want an explicit
Core floor at or above the organisation baseline. Both are cheap to assert and
silent to get wrong, which is exactly why they are asserted.
"""

from __future__ import annotations

import json
import re
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
        """The manifest and the package version must agree.

        Asserting a literal version here is a self-destructing ratchet: it is
        green on main only until release-please bumps the manifest, and red on
        every release PR after that. Compare against the declared package
        version instead, so the check holds at any version.
        """
        manifest = _read_json(ROOT / ".release-please-manifest.json")
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        self.assertIsNotNone(match, "no project version declared in pyproject.toml")
        self.assertEqual(manifest["."], match.group(1))

    def test_every_release_please_extra_file_exists(self):
        config = _read_json(ROOT / "release-please-config.json")
        extra = config["packages"]["."]["extra-files"]
        self.assertTrue(extra)
        for entry in extra:
            self.assertTrue((ROOT / entry["path"]).is_file(), entry["path"])

    def test_every_extra_file_carries_the_release_please_marker(self):
        """A generic extra-file is bumped only via its in-file marker.

        The two SKILL.md files carry `# x-release-please-version` and so were
        bumped; `__version__.py` did not and was silently skipped, which ships a
        wheel whose metadata says one version while `--version` and the MCP
        handshake report another.
        """
        config = _read_json(ROOT / "release-please-config.json")
        for entry in config["packages"]["."]["extra-files"]:
            if entry.get("type") != "generic":
                continue
            text = (ROOT / entry["path"]).read_text(encoding="utf-8")
            self.assertIn(
                "x-release-please-version",
                text,
                "%s is a generic extra-file without a version marker" % entry["path"],
            )

    def test_declared_versions_all_agree(self):
        """Manifest, pyproject, and __version__.py must all report one version."""
        manifest = _read_json(ROOT / ".release-please-manifest.json")["."]
        pyproject = re.search(
            r'^version\s*=\s*"([^"]+)"',
            (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        self.assertIsNotNone(pyproject, "no project version declared in pyproject.toml")
        module = re.search(
            r'^__version__\s*=\s*"([^"]+)"',
            (ROOT / "src" / "dcc_mcp_rizomuv" / "__version__.py").read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        self.assertIsNotNone(module, "no __version__ in the package")
        self.assertEqual(manifest, pyproject.group(1))
        self.assertEqual(manifest, module.group(1))


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
