# AGENTS.md

Instructions for coding agents working in `dcc-mcp/dcc-mcp-rizomuv`.

## What this adapter is

A headless-first RizomUV adapter. RizomUV has no command-line scripting entry
point: automation runs through **RizomUVLink**, a Python package that ships
inside the RizomUV installation and drives an instance over IPC.

## Non-negotiables

- **Headless is not displayless.** `-hl` promises that nothing is *drawn*, not
  that nothing is *needed*. RizomUV still requires a desktop session: an X
  display on Linux, a logged-in session on Windows. It will not start in a
  container with no X server, nor as a Windows service. Never claim container
  support without Xvfb or equivalent.
- **A failed `Load` does not raise.** It returns `{"Error": {"Msg", "Code"}}`.
  Every command must read its result. Without the check the run continues to
  `Unfold` and `Save`, and the failure surfaces several commands later as a
  confusing "no UV set".
- **Dialogs are auto-answered.** In headless mode a prompt is written to the
  command log instead of being shown, and a question you would have answered
  "yes" to is answered "no". Ambiguity resolves conservatively; never rely on a
  default that was never requested.
- **Paths are confined.** Everything goes through `resolve_path`, which honours
  `DCC_MCP_RIZOMUV_ALLOWED_ROOTS` and normalises to absolute forward-slash
  form. RizomUV runs with its own directory as the working directory, so a
  relative path resolves somewhere unintended.
- **One instance per batch.** Launching RizomUV is by far the most expensive
  step; pay it once. Each mesh is still wrapped independently so one unreadable
  file costs that file, not the batch.
- **No clear is needed between batch loads.** RizomUVLink documents `Load` as
  "Import (replace existing) ... as new mesh", and the official batch example
  reuses one instance across a folder without clearing. Do not add a clear
  "just in case" — it would discard the reuse that makes batching cheap.
- **Always `Quit({})` on teardown.** A headless instance has no window to close,
  so returning without quitting leaves an invisible process behind.
- **Version gates are real.** `headless=True` needs RizomUV 2027.0.417+;
  `background=True` needs 2027.0.297+. An older build given an unparseable flag
  answers with a message box nobody is there to dismiss.
- **Python 3.9 is the floor** (`requires-python=">=3.9"`). PEP 604 unions need
  `from __future__ import annotations`; `ruff` `FA` rules enforce this. Do not
  introduce anything that would force Core off Python 3.7.
- **No arbitrary Python execution.** Tools are a fixed, typed surface declared
  in `tools.yaml`.
- **Skill scripts take parameters from stdin JSON, not positional argv.** Core's
  `run_main` reads a JSON object from stdin and calls the entry point with it as
  keyword arguments; a script reading `sys.argv[1:]` receives nothing and fails
  100% of the time under MCP. Follow the two-tier order: stdin JSON first, CLI
  flags only when no payload arrived.
- **Every script emits a `ToolResultEnvelope`** (`success` / `message` /
  `context`) and forces UTF-8 stdio. A piped stdout on Windows defaults to the
  ANSI codepage and raises `UnicodeEncodeError` on CJK mesh paths.
- **Path confinement closes two separate escape layers.** `startswith` lets
  `C:\allowed_evil` pass for `C:\allowed`, so components are compared with
  `commonpath`. But `abspath` is purely lexical, so a symlink or junction
  inside the root still reaches outside — confinement and the returned path
  both use `realpath`. Junctions are common on Windows (`mklink /J`, OneDrive,
  redirected `Desktop`/`Documents`), so this is not theoretical.

## Layout

| Path | Purpose |
|---|---|
| `src/dcc_mcp_rizomuv/discovery.py` | Locate the RizomUV install and its bundled RizomUVLink package. |
| `src/dcc_mcp_rizomuv/driver.py` | Headless session: load, unfold, pack, save, batch. |
| `src/dcc_mcp_rizomuv/doctor.py` | Readiness self-check (contract A013). |
| `src/dcc_mcp_rizomuv/server.py` | MCP server and `doctor`/`status` CLI. |
| `src/dcc_mcp_rizomuv/skills/` | `rizomuv-session`, `rizomuv-uv` skills with `tools.yaml`. |

## Before opening a PR

```bash
python -m pytest -m "not rizomuv"
python -m ruff check src tests
python -m ruff format --check src tests
```

`tests/` marked `rizomuv` need a licensed RizomUV 2027 runtime and are skipped
in CI.
