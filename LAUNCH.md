# 0.2 launch acceptance

Target: an experimental open-source laboratory that another developer can
install, run locally and use to compare an external AI policy with a visible-feed
baseline, while preserving reproducibility and honest cost accounting.

The public announcement is planned for the next user session. Prepare the
release and its assets as a **draft**; do not publish it during preparation.

## Acceptance gates

- [x] Real AgentSociety 2 scheduling/clock, OASIS state and OpenEnv transport;
  pinned dependencies remain isolated. Failure, recovery and concurrency checks
  pass on the final source revision.
- [x] Agent-only observations and permissions hold across reset, step, state
  and alternate protocol paths. Operator configuration and full data require a
  separate capability. Invalid actions do not advance the clock.
- [x] Paired experiments restore the same checkpoint world and clock. Offline
  baseline self-check compares complete trajectories and requires no key or
  model calls. Configuration errors are actionable and fail before spending.
- [x] The optional model policy preserves prompts, public decisions, usage,
  recorded prices and per-experiment costs. Budget and unresolved-call handling
  fail closed. The real-provider execution is auditable from saved artifacts.
- [x] A read-only post-crash audit reconstructs known costs from the durable
  journal, flags incomplete/ambiguous calls, and never starts models or workers.
- [x] A standalone readable report shows paired outcomes, trajectories,
  decisions and costs. The local dashboard can discover saved experiments.
  Report content is escaped; no credentials enter reports or release assets.
- [x] Fresh source-archive installation and the documented commands work on
  macOS ARM64 and Linux x86_64/ARM64 as claimed. The final Docker image runs as
  non-root, with loopback-only host publication, and supports an offline
  experiment with networking disabled after installation.
- [x] README, extension guide, security policy, version metadata, release notes,
  known limitations and contribution path describe the final behavior. Browser
  checks cover the dashboard and experiment report at desktop/mobile sizes.
- [x] Final commit has passing public CI. A reproducible source archive and
  checksum are attached to a draft 0.2 release, with the target commit recorded.
  The source tree and assets contain no secrets, environments or private runs.
- [x] Launch copy and a final requirement-by-requirement evidence record are
  ready for the user. Publishing the draft remains the final launch action.

## Scope and limits

This is a developer/research alpha, with a social-diffusion scenario and one
externally controlled account in each world. Background policies are explicit
scripted rules. No human predictive validity, general model superiority,
training-ready reward, hostile-code sandbox, public multi-tenant service,
Windows-native support or arbitrary upstream-version compatibility is claimed.
Old 0.1 checkpoints require 0.1 code. The default baseline remains offline.

## Evidence

See [the final requirement audit](docs/release-readiness.md). The runtime
candidate passed all 105 tests on fresh macOS ARM64, Linux x86_64 CI and an
offline Linux ARM64 Docker image. The actual six-call model experiment
reconciles to US$0.0004773. Browser/report checks and install fixes are recorded
there as well.

The distribution gates are certified by `validation.json` attached to the
draft release: exact final commit, successful public CI, source archive hash,
image identity and round-trip asset verification. Match it to the release
target before publishing; this file alone is not evidence for a later commit.

Publication and announcements remain deliberately deferred to the next user
session. After publishing, verify anonymous access to the release assets.
