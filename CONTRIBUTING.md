# Contributing

Start with the native installation in README.md, run `./scripts/test -q`, then
make a small pull request describing the behavior that changed and the checks
you ran. Please open an issue before starting a large new world or scheduler.
Bug reports should include OS/architecture, upstream pins, the failing command,
and a small synthetic reproducer. Remove credentials and private run data.

The current release deliberately has one social scenario family and one authoritative
clock. Useful contributions include better experiment protocols, new agent
policies with recorded provenance, additional scenario packages, and evidence
about reproducibility and cost. Claims of human realism need independent data.

## Architecture boundaries

- AgentSociety 2 owns agent workspaces, lifecycle and simulation time.
- OASIS owns the social graph, posts and social action validation.
- OpenEnv owns sessions and the external action/observation contract.
- Agents observe a frozen tick; proposals commit in ascending agent ID order.
- Keep all three Python environments separate. Never replace an upstream with
  a mock to make an integration test pass.

See [docs/extending.md](docs/extending.md) for scenarios and external agents.
Read AGENTS.md before changing runtime code. Run contract tests for API changes
and the live integration tests for persistence, policies or scheduling changes.
No paid model calls belong in the baseline or CI.

Upstream updates require a deliberate commit change in `upstreams.json`, a
review of the relevant runtime lock, and fresh cross-platform integration
results. Preserve upstream licenses. Do not submit vendored source, virtual
environments, API keys, logs or personal experiments.

By submitting a contribution you agree to license it under Apache-2.0, the
project's license. Be respectful, specific and constructive in discussions.


For report/cost changes, test missing and malformed usage, interrupted writes,
recorded-price reconciliation and untrusted text escaping. Rebuild the bundled
example with `python3 scripts/build-example-report.py` and check it with
`--check`. Its source is sanitized recorded data under `examples/recorded-demo`;
do not relabel it as a fresh provider run or replace usage with invented receipts.
Native experiments and the default CI must remain free of paid API calls.
