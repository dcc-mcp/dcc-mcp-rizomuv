# dcc-mcp-rizomuv

Headless [RizomUV](https://www.rizomuv.com/) adapter for DCC-MCP: batch UV
unwrapping and packing driven by an AI agent, with no window ever appearing.

## Validation status

The adapter is implemented and has a [v0.1.1 GitHub release](https://github.com/dcc-mcp/dcc-mcp-rizomuv/releases/tag/v0.1.1).
Default CI runs host-free driver and contract tests; licensed-host tests are
excluded by default. No native acceptance record is committed in this repository,
so green CI does not establish real RizomUV load, unwrap, pack or save behavior.

## Why headless

RizomUV 2027 ships a headless mode (`-hl` / `--headless`) in which the whole
scripting surface runs with nothing on screen. For agent-driven work that is the
difference between a batch that finishes and a batch that hangs:

- no window, no panel, no dialog, no message box
- no modal can stop a run waiting for a click
- console output and clean exit codes for reliable orchestration
- user settings are not touched, so runs are reproducible
- the command log is a replayable script: drive the GUI once, replay it headless

## Install

```bash
pip install dcc-mcp-rizomuv
```

Requires **RizomUV 2027.0.417 or later**. RizomUVLink ships inside that
installation, so installing RizomUV is enough on Windows and macOS. On Linux
there is no install registration: extract the package from the AppImage and
point `RIZOMUV_LINK_DIR` at it.

| Variable | Purpose |
|---|---|
| `RIZOMUV_EXE` | Pin a specific RizomUV executable. Required on Linux. |
| `RIZOMUV_LINK_DIR` | Point at an extracted RizomUVLink package. |
| `DCC_MCP_RIZOMUV_ALLOWED_ROOTS` | `os.pathsep`-separated roots that reads and writes are confined to. |

## Usage

```bash
# Is headless RizomUV usable here?
dcc-mcp-rizomuv doctor --json

# Run the MCP server
dcc-mcp-rizomuv
```

```python
from dcc_mcp_rizomuv import RizomuvSession

with RizomuvSession() as session:
    print(session.unwrap_file("mesh.obj", "mesh_unwrapped.obj"))
    print(session.unwrap_batch(["a.obj", "b.fbx"], "out/"))
```

Supported input: `.obj`, `.fbx`, `.usd`, `.usda`, `.usdc`, `.gltf`, `.glb`.

## Important constraints

**Headless is not displayless.** RizomUV still needs a desktop session to
start — an X display on Linux, a logged-in session on Windows. It will not run
in a container with no X server, nor as a Windows service. Under CI or Docker,
provide Xvfb or equivalent.

**A failed `Load` does not raise.** It returns `{"Error": {"Msg", "Code"}}`.
Check the result; otherwise the run carries on and fails later with a
misleading "no UV set".

**Dialogs are auto-answered**, and a question you would have answered "yes" to
is answered "no" — a script that did not ask for something must not get it.

**Licensing.** Headless uses the normal RizomUV license. Several instances can
run concurrently, but with a floating license each instance takes a token.

## License

MIT. See [LICENSE](LICENSE).
