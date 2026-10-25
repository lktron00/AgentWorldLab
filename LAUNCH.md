# 0.2 launch acceptance

Target: an experimental open-source laboratory that another developer can
install, run locally and use to compare an external AI policy with a visible-feed
baseline, while preserving reproducibility and honest cost accounting.

The public announcement is planned for the next user session. Prepare the
release and its assets as a **draft**; do not publish it during preparation.

## Acceptance gates

- [ ] Real AgentSociety 2 scheduling/clock, OASIS state and OpenEnv transport;
  pinned dependencies remain isolated. Failure, recovery and concurrency checks
  pass on the final source revision.
- [ ] Agent-only observations and permissions hold across reset, step, state
  and alternate protocol paths. Operator configuration and full data require a
  separate capability. Invalid actions do not advance the clock.
- [ ] Paired experiments restore the same checkpoint world and clock. Offline
  baseline self-check compares complete trajectories and requires no key or
  model calls. Configuration errors are actionable and fail before spending.
- [ ] The optional model policy preserves prompts, public decisions, usage,
  recorded prices and per-experiment costs. Budget and unresolved-call handling
  fail closed. The real-provider execution is auditable from saved artifacts.
- [ ] A read-only post-crash audit reconstructs known costs from the durable
  journal, flags incomplete/ambiguous calls, and never starts models or workers.
- [ ] A standalone readable report shows paired outcomes, trajectories,
  decisions and costs. The local dashboard can discover saved experiments.
  Report content is escaped; no credentials enter reports or release assets.
- [ ] Fresh source-archive installation and the documented commands work on
  macOS ARM64 and Linux x86_64/ARM64 as claimed. The final Docker image runs as
  non-root, with loopback-only host publication, and supports an offline
  experiment with networking disabled after installation.
- [ ] README, extension guide, security policy, version metadata, release notes,
  known limitations and contribution path describe the final behavior. Browser
  checks cover the dashboard and experiment report at desktop/mobile sizes.
- [ ] Final commit has passing public CI. A reproducible source archive and
  checksum are attached to a draft 0.2 release, with the target commit recorded.
  The source tree and assets contain no secrets, environments or private runs.
- [ ] Launch copy and a final requirement-by-requirement evidence record are
  ready for the user. Publishing the draft remains the final launch action.

## Scope and limits

This is a developer/research alpha, with a social-diffusion scenario and one
externally controlled account in each world. Background policies are explicit
scripted rules. No human predictive validity, general model superiority,
training-ready reward, hostile-code sandbox, public multi-tenant service,
Windows-native support or arbitrary upstream-version compatibility is claimed.
Old 0.1 checkpoints require 0.1 code. The default baseline remains offline.

## Evidence

Initial state for this readiness pass: feature commit `f2b1586`, PR #1, 76 passing
Linux tests and a real six-call experiment whose provider-reported token cost
estimate is US$0.0004773. These establish the starting point, not completion of
new readiness gates. Final evidence belongs in `docs/release-readiness.md`.
