# Launch acceptance and evidence

Objective: make Agent World Lab usable by other people as an open-source project and publish a verified release. A working local demo alone does not complete this objective.

## Required before announcing the release

- [ ] Fresh installation from the published source, with pinned upstream revisions and no dependence on the author's filesystem.
- [ ] macOS ARM and Linux runtime verification of AgentSociety 2, OASIS and OpenEnv; document any unsupported platform accurately.
- [x] Reliable reset, step, recovery, checkpoints, replay and export, including failure and concurrency tests.
- [x] Agent policies and scenarios that users can extend; a documented path for real external AI agents, with honest separation from the scripted baseline.
- [x] Working dashboard, API documentation and runnable examples, including resuming a saved experiment.
- [x] Default local exposure protected against cross-origin browser access; no credentials, private logs or run data published.
- [x] License, third-party notices, contribution instructions, security reporting, release notes and public automated checks.
- [ ] Public GitHub repository with the tested commit, passing CI and a downloadable tagged release.
- [ ] Verify the published links and installation instructions as an unauthenticated reader.

## Current authoritative starting point

- Initial prototype commit: `7e3c0fc`.
- Main checkout and release worktree (`codex/launch`): use `git worktree list` to locate them.
- Existing prototype validation: 14 tests on macOS ARM, including the three real engines. This does not establish Linux support or readiness for public exposure.
- GitHub CLI authenticated as `lktron00`; repository `lktron00/AgentWorldLab` did not exist at the initial launch audit.
- Docker daemon available on Linux ARM64; independent Linux validation is possible locally.

Update this file with concrete evidence as gates are satisfied. Keep unfinished requirements explicit; do not relabel missing work as completed.

## Release preparation evidence

- macOS ARM64: 51 tests passed, including real engines, failure recovery and
  concurrent session/checkpoint tests. See VALIDATION.md.
- Dashboard: created a world, saved step 2, compared five-step branches;
  the rendered results were 20 vs 10 unverified sharers. Screenshot in
  `docs/dashboard.png` contains synthetic experiment data only.
- `examples/compare.py` completed seeds 7 and 8 via the live API, producing
  endpoint counts 20/10 and 20/14 and a paired mean difference of 8.
- Public repository created at https://github.com/lktron00/AgentWorldLab;
  anonymous GitHub API access confirms `private: false`. Private vulnerability
  reporting is enabled. Release and final platform checks remain pending.
