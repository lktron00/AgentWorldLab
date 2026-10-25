# Agent World Lab 0.2.0 — experimental release

Run an external AI policy in a synthetic social world and compare it with a
visible-feed baseline from the same checkpoint. Every experiment preserves
decisions, state trajectories and estimated model costs.

## Included

- Genuine AgentSociety 2, OASIS and OpenEnv runtimes, isolated and pinned.
- A dedicated agent server with limited observations, visible-post action
  guards, separate operator/agent capabilities and one-use reset tickets.
- `scripts/experiment`: one command starts a local server, runs both branches
  and stops its server. The offline self-check verifies every world-state hash.
- Optional OpenAI policy, recorded prompt/model identity, bounded generation
  budget and durable usage receipts. No paid calls in the normal demo or CI.
- Offline journal auditing and standalone HTML reports, including recovery of
  receipts saved before an interruption. Unverifiable usage is flagged.
- Local experiment catalog, a sanitized recorded example, original-signal
  metrics and JSON scenario configuration.
- Native/Docker setup, automated real-engine tests and extension documentation.

## Quick start

```sh
git clone https://github.com/lktron00/AgentWorldLab.git
cd AgentWorldLab
python3 scripts/bootstrap.py
./scripts/serve
```

Open http://127.0.0.1:8765/experiments to explore the recorded example, or run:

```sh
./scripts/experiment --policy baseline --seeds 7 --steps 3
```

For an optional OpenAI run, configure a private `.env` with `OPENAI_API_KEY`,
then use `./scripts/experiment --seeds 7 8 --steps 3 --budget-usd 0.10`.

## Compatibility and limits

Supported native targets are macOS ARM64 and Linux ARM64/x86_64. Windows users
need a supported Linux/Docker environment. Three Python dependency graphs are
intentionally separate. Old 0.1 checkpoints require their original release.

This is a local developer/research alpha with one social scenario family, one
externally controlled account per world and scripted background agents. It is
not a public multi-tenant service, hostile-code sandbox, calibrated human model
or validated intelligence benchmark. Reward is unset. Reported USD values are
token-based estimates, excluding infrastructure, tax and development credits.

The source archive and SHA256SUMS attached to the release are the portable
distribution. See `docs/release-readiness.md` for final validation evidence.
