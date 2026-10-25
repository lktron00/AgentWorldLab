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


## External AI experiments — 2026-10-25 (0.2 validation)

- Full macOS ARM suite after scoped server, permissions, reset tickets, cost ledger
  and SDK transport changes: **75 passed in 149.74 s**. A subsequent metric-only
  increment distinguishes original-signal diffusion from new questions; its
  focused contract/paired-run tests are recorded with the PR validation.
- Real paid-provider end-to-end run used `scripts/experiment --seeds 7 8 --steps 3
  --budget-usd 0.10`, GPT-6 Luna with low effort and the three genuine engines.
  Both pairs restored matching full-world/clock fingerprints from a checkpoint.
- Six completed model calls: 3,358 input tokens, 283 output tokens, no unresolved
  usage. Estimated model cost **US$0.0004773** at the recorded standard rates
  (seed 7: $0.0002499; seed 8: $0.0002274). This excludes infrastructure/taxes and
  Codex/development usage; it is not a billing invoice.
- Baseline/candidate final original-signal sharers: **18/15** for seed 7 and
  **19/19** for seed 8. The candidate did not repost the original signal; it
  requested evidence. Its new question can also diffuse, so aggregate unverified
  counts are kept separate. Two toy seeds establish an executed comparison, not
  predictive validity or general model superiority.
- Additional original-signal metrics were derived from saved engine frames;
  no generation or simulation was repeated. Original report preserved locally.
- [Sanitized real-run summary](docs/ai-validation.json) records per-seed outcomes,
  usage, rates and artifact hashes without credentials or provider response IDs.
  Exact prompts, decisions, provider receipts and engine data stay in gitignored
  `data/experiments/ai-first-run-20261025/`.


## 0.2 release acceptance — 2026-10-25

Runtime candidate: `1aeea6fc893ac612e668263b476e85f78e363d5a`.
Final documentation/screenshots do not change the tested runtime. Exact final
commit/CI/archive/image provenance belongs to the draft release's attached
`validation.json`; see [the requirement audit](docs/release-readiness.md).

| Platform | Final 0.2 verification | Result |
| --- | --- | --- |
| macOS ARM64 | Fresh source archive, managed native Python 3.12.13/3.11.15, full suite | 105 passed in 203.94 s |
| Linux x86_64, Ubuntu 24.04 | Clean public checkout, bootstrap, full suite, offline CLI and audit | [105 passed in 179.16 s](https://github.com/lktron00/AgentWorldLab/actions/runs/40183658456) |
| Linux ARM64, Debian 12 | Archive-built Docker image, non-root UID 10001, full suite with networking disabled | 105 passed in 305.38 s |

Additional checks cover scoped observations, hidden/duplicate repost rejection,
operator/reset capabilities, tunneled alternate protocols, budget exhaustion,
invalid model outputs, unresolved provider calls, journal crash recovery,
escaped HTML, report downloads and read-only catalog paths. The offline paired
CLI checks complete world hashes and costs zero model tokens. A real SIGTERM
integration test confirms the report is saved and its server is stopped.

Bootstrap was exercised with cached Intel Python on an ARM Mac and rejects a
mismatched existing environment without deleting it. Raw Git-blob verification
accepts the byte-identical upstream CRLF source and still rejects real, staged
and untracked modifications. No upstream patch or pin change was used.

Manual 0.2 browser verification includes the actual dashboard comparison,
experiment catalog, real report, recorded example, decisions and scoped
observations. Report/catalog layouts were checked at desktop size and 390 × 844.
No additional paid provider calls were made for these acceptance checks.
