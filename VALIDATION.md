# Prototype validation — 2026-10-24

Tested locally on macOS ARM64 using the exact upstream commits and dependency versions in `upstreams.json` and `requirements/`.

`./scripts/test -q`: **14 passed** (46.03 seconds from the final project directory after bootstrap).

- 13 contract tests validate actions, actor identity restrictions, ID/path validation, followed-account visibility, duplicate-share avoidance and scheduling-independent random draws.
- One integration test runs a live TCP server with the real OpenEnv client, real AgentSociety Ray tasks and the real OASIS Platform/SQLite backend.
- Checkpoint restoration reproduces all five subsequent world states exactly, including timestamps and social posts.
- A fresh controller process can restore the checkpoint after the original session has closed.
- A tampered checkpoint is rejected without advancing the active world.
- Unknown repost IDs are rejected without advancing the simulation clock.
- Agent workspace step counts, OASIS action traces, native AgentSociety replay, recorded frames and exported ZIP contents are checked.

Reference scenario: seed 7, 20 scripted agents, checkpoint at step 2 with 6 unique accounts having shared the unverified signal. After five further steps:

| Policy | Unique accounts sharing the unverified signal | Posts |
| --- | ---: | ---: |
| Open | 20 / 20 | 20 |
| Friction | 10 / 20 | 10 |

This difference follows the explicit programmed rule. It is not a measured effect in humans or evidence of predictive accuracy.

Manual browser verification: world creation, step progression, checkpoint creation and both comparison branches completed through the actual dashboard. The rendered graph and activity feed reflect returned engine state, not fixture data.

The documented bootstrap completed successfully using the native ARM uv binary. The standalone external-agent example also completed five API-driven steps against the installed server.
