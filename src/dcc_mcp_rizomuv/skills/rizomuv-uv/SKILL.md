---
name: rizomuv-uv
description: >-
  Unwrap and pack UVs for meshes through a headless RizomUV instance, one file or
  a whole folder, without any window ever appearing.
license: MIT
compatibility: "RizomUV 2027.0.417+ (headless); dcc-mcp-core 0.20.36+"
allowed-tools: "python"
metadata:
  dcc-mcp:
    dcc: rizomuv
    layer: domain
    version: "0.1.0"  # x-release-please-version
    tags: "rizomuv,uv,unwrap,pack,mcp,dcc,automation"
    tools: tools.yaml
    depends: ["dcc-diagnostics"]
---

# RizomUV UV

One instance is launched per batch and reused, because launching RizomUV is by
far the most expensive step. Each mesh is wrapped independently: one unreadable
file costs that file, not the batch.

Supported input: `.obj`, `.fbx`, `.usd`, `.usda`, `.usdc`, `.gltf`, `.glb`.

Use `rizomuv-session.get_status` first when the runtime is unknown.
