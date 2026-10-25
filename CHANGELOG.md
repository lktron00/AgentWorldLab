# Changelog

## 0.2.0 — external AI experiments (experimental)

- Server-enforced external-agent observations and visible-post action guards;
  separate local agent/operator capabilities in a dedicated OpenEnv server.
- Optional Responses API policy, deterministic visible-feed baseline and paired
  checkpoint runner (`scripts/experiment`). No paid calls in the normal demo.
- Durable per-call usage/cost journal, total budget reservation, cache/ reasoning
  accounting and readable experiment reports. Ambiguous API failures stop further
  spending and remain unresolved rather than being counted as free.
- Offline audit reconstructs costs from durable responses after interruption,
  flags ambiguous/truncated usage and preserves source artifacts.
- Standalone HTML reports, local experiment catalog, sanitized recorded demo
  and an evidence-bearing synthetic scenario.
- Actionable CLI errors, graceful SIGTERM handling and full-trajectory hashes
  in the offline self-check. Reports include application/source provenance.
- Bootstrap selects explicit architecture/libc Python requests without replacing
  global command links. It rejects incompatible existing environments safely.
- Source verification compares raw Git blobs, including file modes and staged/
  untracked changes, avoiding upstream CRLF normalization false positives without
  patching upstream files or weakening pin validation.
- External account now follows accounts 1 and 2. This adapter change invalidates
  v0.1.0 checkpoints; keep that release to restore earlier experiments.

## 0.1.0 — initial experimental release

- Real AgentSociety 2 scheduling, OASIS social state and OpenEnv sessions in
  isolated, pinned runtimes.
- Local dashboard with stepping, external-agent posts, recorded replay,
  checkpoint restoration, paired policy comparison and JSON export.
- Configurable diffusion scenarios and a multi-seed experiment runner.
- Typed Python client for external agent systems.
- Checkpoint integrity, clock and SQLite validation; failed worlds require
  reset or restore instead of continuing partial ticks.
- Bounded process communication and local browser access protection.
- CPU-only Linux container, real-engine CI and contribution documentation.

This release is an integration laboratory, not a validated model of human
behavior. Baseline agents follow explicit rules; no model key is required.
Checkpoints require the same adapter code and upstream versions. No checkpoint
migration, public hosting or restricted-information agent benchmark is promised.
