# Changelog

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
