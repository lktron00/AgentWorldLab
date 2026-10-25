# Release validation — 2026-10-24

Tested locally on macOS ARM64 using the exact upstream commits and dependency versions in `upstreams.json` and `requirements/`.

`./scripts/test -q`: **51 passed** (96.49 seconds, macOS ARM64).

| Platform | Verification | Result |
| --- | --- | --- |
| macOS ARM64 | Full suite; three integration tests repeated after provenance changes | 51 passed; targeted rerun 3 passed in 118.14 s |
| Linux x86_64, Ubuntu 24.04 | Fresh public GitHub Actions checkout and bootstrap | [51 passed](https://github.com/lktron00/AgentWorldLab/actions/runs/40153478917) |
| Linux ARM64, Debian 12 container | Clean Docker build; non-root user; runtime network disabled | 51 passed in 152.86 s |

The container test used `docker run --network none --shm-size=512m` with the
built image and `./scripts/test -q`. Installation requires network access;
the baseline simulation and all tests ran offline after installation.
`scripts/doctor.py` verified all three package versions and source commits on
both native macOS and the ARM Linux image. Python versions were 3.12.2/3.11.15
on macOS, 3.12.13/3.11.15 in x86 CI, and 3.12.12/3.11.14 in the ARM image.

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

Docker Compose also built and started successfully with a named data volume,
healthy HTTP endpoint and host port restricted to `127.0.0.1`. The multi-seed
example completed seeds 7 and 8: endpoints were 20/10 and 20/14 unverified
sharers (open/friction), with a descriptive paired mean difference of 8.

No human-population calibration, paid LLM run, public server exposure,
Windows-native support, Intel macOS support or large-scale load test is claimed.
Checkpoints from earlier adapter revisions deliberately require their original
code. There is no checkpoint migration in this release.
