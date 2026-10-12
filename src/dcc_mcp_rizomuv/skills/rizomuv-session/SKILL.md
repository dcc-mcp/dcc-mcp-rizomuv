---
name: rizomuv-session
description: >-
  Verify a headless RizomUV 2027 installation and report whether batch UV work can
  run on this machine. No arbitrary Python execution.
license: MIT
compatibility: "RizomUV 2027.0.417+ (headless); dcc-mcp-core 0.20.36+"
allowed-tools: "python"
metadata:
  dcc-mcp:
    dcc: rizomuv
    layer: domain
    version: "0.1.0"  # x-release-please-version
    tags: "rizomuv,uv,mcp,dcc,automation,headless"
    tools: tools.yaml
    depends: ["dcc-diagnostics"]
---

# RizomUV session

Start with `get_status`. Every path must be inside
`DCC_MCP_RIZOMUV_ALLOWED_ROOTS`. Set `RIZOMUV_EXE` to pin a build, and
`RIZOMUV_LINK_DIR` when RizomUVLink is not importable from an installation.

Headless mode needs a desktop session: an X display on Linux, a logged-in
session on Windows. Nothing is drawn, but the session is still required.

Use `rizomuv-uv` for unwrapping and packing.
