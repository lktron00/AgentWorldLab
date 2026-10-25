# Release validation — 2026-10-24

Tested locally on macOS ARM64 using the exact upstream commits and dependency versions in `upstreams.json` and `requirements/`.

`./scripts/test -q`: **51 passed** (96.49 seconds, macOS ARM64).

- 13 contract tests validate actions, actor identity restrictions, ID/path validation, followed-account visibility, duplicate-share avoidance and scheduling-independent random draws.
- Three integration tests run a live TCP server with the real OpenEnv client, real AgentSociety Ray tasks and the real OASIS Platform/SQLite backend.
- Checkpoint restoration reproduces all five subsequent world states exactly, including timestamps and social posts.
- A fresh controller process can restore the checkpoint after the original session has closed.
- A tampered checkpoint is rejected without advancing the active world.
- Unknown repost IDs are rejected without advancing the simulation clock.
- Agent workspace step counts, OASIS action traces, native AgentSociety replay, recorded frames and exported ZIP contents are checked.
- A deliberately corrupted agent clock fails the tick, exposes failed state, prevents continuation and recovers from a healthy checkpoint.
- Two concurrent sessions retain independent worlds; checkpoints requested during a step save a consistent boundary.
- Configurable scenario validation, termination, zero-probability friction and immutable restore parameters are covered.
- Checkpoint inventory rejects unexpected files, symbolic links, inconsistent clocks and a corrupt SQLite database, including forged matching hashes.
- Process communication tests enforce deadlines for incomplete responses and blocked request writes, detect malformed envelopes and handle worker rejection without desynchronization.
- HTTP and WebSocket browser-origin/Host protection is tested alongside valid local clients.

Reference scenario: seed 7, 20 scripted agents, checkpoint at step 2 with 6 unique accounts having shared the unverified signal. After five further steps:

| Policy | Unique accounts sharing the unverified signal | Posts |
| --- | ---: | ---: |
| Open | 20 / 20 | 20 |
| Friction | 10 / 20 | 10 |

This difference follows the explicit programmed rule. It is not a measured effect in humans or evidence of predictive accuracy.

Manual browser verification: world creation, step progression, checkpoint creation and both comparison branches completed through the actual dashboard. The rendered graph and activity feed reflect returned engine state, not fixture data.

The documented bootstrap completed successfully using the native ARM uv binary. The standalone external-agent example also completed five API-driven steps against the installed server.

Linux ARM64 clean-container validation and public Linux x86_64 CI are pending;
the release tag will be created only after both pass.
