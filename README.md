# Agent World Lab

[![Real engine integration](https://github.com/lktron00/AgentWorldLab/actions/workflows/ci.yml/badge.svg)](https://github.com/lktron00/AgentWorldLab/actions/workflows/ci.yml)

An open-source laboratory for testing AI decisions in reproducible multi-agent
social worlds. Compare conditions from the same checkpoint, inspect what each
agent could observe, and trace decisions, trajectories and model costs.
Recorded examples are available without a model key or engine installation.

**AgentSociety 2** schedules the agents and owns the simulation clock. **OASIS**
owns social state. **OpenEnv** provides the external agent interface. These are
real, pinned runtimes connected through small adapters.

[![Explore the recorded agent networks](docs/explorer-network.png)](https://agent-world-lab-explorer.lktron.chatgpt.site)

**Status: experimental 0.2.** The default dashboard and baseline run offline.
Optional OpenAI experiments use a separately configured key and explicit
budget. The default background agents follow scripted rules. Optional all-AI
studies let every active account choose through a model. The project does not
claim to predict people or provide a validated intelligence benchmark.
The current main branch includes development after the v0.2.0 release.

## Explore the completed work without paying for models

**[Open the public results explorer](https://agent-world-lab-explorer.lktron.chatgpt.site)** — no account, download, API key or engine installation. Explore the original agent networks, recorded message routes, every complete repetition and each agent’s scoped observations. The viewer works on desktop and mobile; browsing creates no model charges. [How the maps and static build work](docs/public-explorer.md).

- **[Project presentation in Spanish](docs/presentacion/README.md)** — a seven-page introduction for nontechnical readers, in PDF and editable Word, with diagrams and real results.
- **[Nine-case all-AI study](examples/recorded-study/README.md)** — 102 complete paired comparisons, all 41,770 valid decisions; the online explorer includes all 40,800 decisions from the 102 complete pairs. The separate offline recording includes a 3,600-decision sample.
- **[First all-AI pilot](examples/recorded-pilot/README.md)** — all 4,000 recorded Luna decisions across ten pairs, including a result with no change in initial-rumor sharing.
- **[1,000-pair scripted campaign](examples/recorded-campaign/README.md)** — 800,000 programmed decisions with zero model API calls. Its reduction in sharing follows an explicitly imposed rule.

Open [`web/recorded-study.html`](web/recorded-study.html) after downloading the repository. This self-contained recording needs a modern browser, no server, no API key and no new model calls. After starting the local dashboard, `/campaigns` also links to it.

The nine-case study's **confirmed cumulative usage was US$9.9792478750**, including the earlier pilot. Seventeen unreceipted requests retain their full US$0.0197201250 reservation; **maximum cumulative exposure was US$9.9989680000** under the original US$10 cap. This ceiling is not an exact invoice. Synthetic results describe model behavior, not validated human predictions.

Validate the published data and rebuild the recording checks with the Python standard library:

```sh
python3 scripts/build-study-example.py --check
```

## Quick start

Requires Git and [uv](https://docs.astral.sh/uv/getting-started/installation/). Supported installation targets are macOS ARM64 and Linux ARM64/x86_64; see [VALIDATION.md](VALIDATION.md) for completed platform checks. Bootstrap downloads Python 3.11/3.12, pinned upstream source and dependencies, including CPU PyTorch. Allow several GB of disk space and network access to fetch dependencies. No API key or model download is needed for the baseline and dashboard; experiments then run offline unless the optional model policy is selected.

```sh
git clone https://github.com/lktron00/AgentWorldLab.git
cd AgentWorldLab
python3 scripts/bootstrap.py
./scripts/serve
```

On Debian/Ubuntu, install native libraries first:
`sudo apt-get install build-essential libmagic1 libcairo2 libgomp1`. On Apple Silicon, use a
native ARM build of uv; bootstrap selects the ARM interpreter explicitly and rejects incompatible existing environments without deleting them.

With Docker Compose, use `docker compose up --build` from the cloned repository.
The first build downloads the same pinned dependencies; subsequent starts reuse
the image. Data persists in a named volume. The published port is bound to
`127.0.0.1`; keep that binding. Stop with `docker compose down` (without `-v` to
preserve experiments). Docker Desktop needs enough memory for Python and Ray;
8 GB allocated to Docker is a starting recommendation, not a measured minimum.
To select another host port: `WORLDLAB_PORT=8768 docker compose up --build`.

Open **http://127.0.0.1:8765** for the laboratory, or **http://127.0.0.1:8765/experiments** for saved reports and a recorded real-run example. The first world may take 30–90 seconds to start Ray and import upstream modules. Later ticks are much faster.

1. Click **Crear mundo** with seed 7 and 20 agents.
2. Advance two steps, then **Guardar checkpoint**.
3. Click **Comparar abierta / fricción**. Each branch advances five steps from that checkpoint.
4. Publish as the external agent, inspect the feed and network, move through recorded frames, or export the run.

To use another port: `PORT=8766 ./scripts/serve`. To store runs elsewhere: `WORLDLAB_DATA=/absolute/path ./scripts/serve`. Use one server process; each WebSocket session has its own controller and world, with a maximum of two simultaneous sessions in this prototype. Close sessions before stopping the server.

## What each engine actually does

| Component | Integration used | Responsibility |
| --- | --- | --- |
| AgentSociety 2, 2.9.3 | `AgentSociety`, `AgentBase`, `EnvBase`, `RouterBase`, `ServiceProxy`, `ReplayProxy`, native Ray tasks and registry | Agent lifecycle, batched decisions, simulation clock, agent workspaces and native replay timeline |
| OASIS, 0.2.5 | Original `Platform.sign_up`, `follow`, `create_post`, `repost` and its SQLite schema/trace | Authoritative social graph, posts, share counts and action validation |
| OpenEnv, 0.10.1.dev0 | Original `Environment`, `create_app` and `EnvClient` | Typed reset/step/state API, session lifecycle and external agent connection |
| Agent World Lab | Small adapters, scripted policy, checkpoint coordinator and dashboard | Cross-engine consistency, synchronous observation boundary, policy comparisons and exports |

OASIS's built-in recommender and CAMEL/LLM agent orchestration are **not used** in this prototype. The adapter constructs a chronological feed from posts by followed accounts, with a 12-post limit. AgentSociety schedules agents; OASIS handles social actions. This avoids two independent agent schedulers or simulation clocks.

The default world contains 20 scripted agents plus external agent 0. A seeded directed graph has local and longer-range links. One initial unverified signal is posted by agent 1. Agents have fixed sharing probabilities (0.6–0.9). The `friction` policy multiplies the probability for unverified content by 0.2. This mechanism is explicit and intentionally simple: the comparison demonstrates a rule's effect, not an empirical discovery.

The verification flag is a **scenario annotation**, not fact-checking. No language model judges text, and no scientific or reward claim is attached to that flag. Reward is left unset. Metrics count unique accounts that **shared** content, not exposure, beliefs or persuasion.

## External AI experiment (optional API usage)

The one-command runner now connects an external OpenAI policy through a
server-enforced, agent-scoped view and compares it with a deterministic
visible-feed baseline from the exact same checkpoint. Both branches use the
same background policy. Per-decision tokens, estimated USD cost, decisions and
paired trajectories are saved. The normal demo remains offline. No existing server is required for the command.

```sh
# Set OPENAI_API_KEY in a private, gitignored .env first.
./scripts/experiment --seeds 7 8 9 --steps 5 --budget-usd 0.10
# No key/cost: run the deterministic policy on both sides as a self-check.
./scripts/experiment --policy baseline --seeds 7 --steps 3
```

Each run writes `report.html`, `report.json`, `decisions.jsonl` and a durable
`costs.jsonl`. Open the HTML directly or find it in the local experiment
catalog. The offline self-check requires complete world trajectories to match.
To audit/rebuild an existing report without an engine or model call:

```sh
./scripts/report data/experiments/YOUR_EXPERIMENT
./scripts/report data/experiments/YOUR_EXPERIMENT --check
```

![A recorded external-policy experiment and its cost audit](docs/report.png)

The bundled example is a sanitized recording, not a new inference. Its six
real GPT-6 Luna calls used an estimated **US$0.0004773** at the recorded rates;
this is one tiny synthetic run, not a general price/performance promise.

The runner starts/stops its own loopback server. `WORLDLAB_DATA` selects the
shared data directory for the dashboard and default experiment output. See
[AI experiments, observation permissions and cost accounting](docs/ai-experiments.md).

## A concrete case with 1,000 paired experiments (development)

The Nube Norte campaign follows an unverified file-loss rumor through a fictional
storage platform. It executes 1,000 pairs, 2,000 real-engine worlds and 800,000
scripted account decisions, then explains the mean, variation and one concrete
message/repost history. No paid model calls are made.

```sh
./scripts/campaign --pairs 10 --output data/campaigns/first-campaign
# Full campaign; this can take several minutes and saves each completed pair.
./scripts/campaign --pairs 1000 --output data/campaigns/nubenorte-1000
```

Open `/campaigns` on the local server, or the saved standalone `report.html`.
See [the scenario, interpretation, resume and costs guide](docs/campaigns.md).
This is a programmed-rule experiment, not a calibrated prediction about people.
The campaign feature is development after the published 0.2.0 release.

![Recorded Nube Norte campaign with 1,000 paired comparisons](docs/nubenorte.png)

## External agent API

Run the example while the server is running:

```sh
.venv-api/bin/python examples/external_agent.py
```

Or use the typed client from the project root:

```python
import asyncio
from worldlab.client import LabClient
from worldlab.models import LabAction

async def main():
    async with LabClient(
        base_url="http://127.0.0.1:8765", message_timeout_s=180
    ) as client:
        result = await client.reset(seed=7, population=20)
        result = await client.step(LabAction(
            kind="post", content="A synthetic signal from my agent"
        ))
        print(result.observation.snapshot["metrics"])
        print(await client.state())

asyncio.run(main())
```

Actions: `wait`, `post(content, verified=False)`, `repost(post_id)`. Each action advances the society by one simulated minute. The caller always controls agent 0; it cannot impersonate the other accounts. Replace the example's policy selection with any agent system. The supplied runtime itself never calls an LLM.

The dashboard server exposes the **whole world for experiment debugging**. Use the dedicated `scripts/experiment` runner for scoped observations and separate agent/operator capabilities. One client controls one world; several clients do not automatically share a society.

OpenEnv wire protocol at `/ws`:

```json
{"type":"reset","data":{"seed":7,"population":20,"policy":"open"}}
{"type":"step","data":{"kind":"wait"}}
{"type":"state"}
```

Operator endpoints (separate from agent actions):

| Endpoint | Purpose |
| --- | --- |
| `GET /docs` | Interactive OpenAPI documentation |
| `GET /schema` | OpenEnv action/observation/state contracts |
| `GET /lab/runs` | Recent saved runs |
| `GET /lab/runs/{id}/frames` | Recorded world snapshots |
| `POST /lab/runs/{id}/checkpoint` | Save a healthy connected world at a tick boundary |
| `GET /lab/runs/{id}/export` | ZIP of JSON state, events and provenance |

Restore or branch with `client.reset(checkpoint_id="…", policy="friction")`. Omit `policy` to retain the saved rule. Restoring creates a **new run**, preserving the previous run's data. The saved seed and population override reset defaults.

## Architecture and reproducibility

For JSON scenarios, multi-seed comparisons and connecting your own AI agent,
see [Extending an experiment](docs/extending.md). For example:

```sh
.venv-api/bin/python examples/compare.py --seeds 7 8 9 \
  --scenario scenarios/diffusion.json --output data/comparison.json
```

```text
Dashboard / external agent
            │ OpenEnv WebSocket
            ▼
OpenEnv environment             Python 3.12 · .venv-api
            │ JSON-lines process boundary
            ▼
AgentSociety controller + Ray    Python 3.12 · .venv
  1. Apply external action
  2. Freeze observations
  3. Run all agent decisions
  4. Apply proposals in ID order
  5. Advance one clock; persist
            │ JSON-lines process boundary
            ▼
OASIS Platform + SQLite         Python 3.11 · .venv-oasis
```

The environments are intentionally isolated. AgentSociety requires MCP 2.x, while the pinned OASIS requires MCP 1.29 and Python <3.12. OpenEnv/FastMCP has a separate dependency graph. No upstream code is patched or replaced with a mock. Exact source revisions live in `upstreams.json`; installed runtime versions are pinned under `requirements/`.

Agent decisions read the same frozen snapshot within a tick; they cannot observe another agent's partially applied actions. Random draws derive from `(seed, step, agent_id, root_post_id)`, so scheduling order does not consume a shared random generator. OASIS uses its discrete clock; its step comes from AgentSociety. Applied actions are committed in ascending agent ID order.

Checkpoints use SQLite's backup API and copy agent state, clock metadata, configuration, events and replay data. Files have SHA-256 integrity hashes. Checkpoints are created only between steps and finalized by an atomic directory rename. A failed tick marks the controller unusable until reset/restore; it is not silently retried. Live runs are not fully transactional across engines: resume from an explicit valid checkpoint after a process crash.

Recorded replay means reading saved frames. Re-running means executing policies again. They are distinct operations; exact continuation is tested for the included deterministic policy and pinned runtime. It is not a determinism guarantee for future LLM agents, other hardware or upgraded dependencies.

## Project layout

```text
worldlab/             Controller, adapters, contracts and typed client
web/                  Local dashboard (HTML/CSS/JS, no CDN or build step)
examples/             External agent and paired experiment runners
scenarios/            Editable JSON scenario definitions
tests/                Contract tests + real three-engine WebSocket integration
requirements/         Separate runtime locks
upstreams.json        Immutable source revisions
vendor/               Upstream checkouts fetched by bootstrap (gitignored)
data/runs/            Independent run directories (gitignored)
data/checkpoints/     Complete saved worlds (gitignored)
data/logs/            Controller diagnostics (gitignored)
```

## Verification

```sh
python3 scripts/doctor.py
./scripts/test tests/test_contracts.py -q
./scripts/test tests/test_integration.py -q
./scripts/test -q
```

Integration tests start a local TCP server, connect the real `EnvClient`, schedule real Ray tasks, and inspect real OASIS SQLite rows. They verify state continuity, identical continuation, policy divergence, external actions, rejection without clock advancement, replay/export and recovery in a fresh process. Initial imports make the first test slower.

## What to contribute next

- Multiple external agents in one shared world, with an explicit simultaneous-action contract.
- Scenario packages beyond social diffusion; benchmark against observed data before claiming realism.
- Scalable shared worker infrastructure and additional platform coverage.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and
[release readiness](docs/release-readiness.md) for contribution boundaries,
security assumptions and the final release evidence. The recorded demo can be
rebuilt offline with `python3 scripts/build-example-report.py`.

The native server binds to loopback; Docker Compose publishes only on the host's loopback interface. HTTP and WebSocket requests enforce local Host and same-origin browser access. There is no authentication or tenant isolation. Keep it local; public hosting requires additional work. Local checkpoints contain data and trusted code provenance, and are not an untrusted artifact import format. See [SECURITY.md](SECURITY.md).

Contributions are welcome: [CONTRIBUTING.md](CONTRIBUTING.md),
[release notes](CHANGELOG.md), and [issues](https://github.com/lktron00/AgentWorldLab/issues).

## License

New project code: Apache-2.0. AgentSociety 2 and OASIS: Apache-2.0. OpenEnv: BSD-3-Clause. See `THIRD_PARTY_NOTICES.md`. MiroFish source is not included in this project.

## All-AI incident pilot (development branch)

The explicit paid runner controls every active account with GPT-6 Luna. Each pair starts from the same checkpoint, with the same roles and goals. The two conditions differ only in the information returned by an optional status-page consultation. No scripted sharing multiplier or cautious-sharing policy is used in this pilot.

```sh
./scripts/pilot --population 20 --steps 10 --pairs 10 --budget-usd 10
```

This plans 4,000 model decisions and keeps one shared generation budget, including concurrent reservations. Set `OPENAI_API_KEY` in the private `.env` first. The offline default experiment remains free of model calls. Open `/campaigns` on the local server to find a pilot, inspect each account's observation/action, compare pairs and download usage receipts. See [the pilot guide](docs/all-ai-pilot.md) for accounting and limitations.

### Balanced nine-case study (development branch)

After the recorded Luna pilot, `./scripts/study --budget-total-usd 10` uses only the verified unspent remainder of that cumulative cap. Nine predeclared file, payment and software-integrity fixtures include real problems, false alarms, limited samples and stale/wrong-version evidence. Every active account decides with Luna. The local study dashboard exposes actions, observations, evidence references, paired Brier differences and exact usage allocations; a SQLite dataset and offline auditor support deeper analysis. See [the study guide](docs/multi-case-study.md).
