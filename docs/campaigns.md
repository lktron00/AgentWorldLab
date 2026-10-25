# Nube Norte: understanding a rumor across 1,000 paired experiments

Nube Norte is an invented file-storage platform. A synthetic account posts that
it cannot find its folders. The experiment asks how many accounts share that
unverified message during its first eight simulated minutes.

The scenario does not simulate a data loss, a technical investigation, a
company statement or a real customer population. Its purpose is to make a
social-diffusion mechanism and repeated, paired experiments easy to inspect.

## What is executed

The default campaign contains **1,000 pairs: 2,000 complete worlds**, each with
50 scripted background accounts and an inactive external account. Eight ticks
per branch produce **800,000 background account decisions** through actual
AgentSociety 2 tasks, OASIS actions/SQLite and OpenEnv WebSocket transport.
These are not 1,000 simultaneous agents, nor 800,000 LLM calls.

For each seed, the operator creates a fresh world and a checkpoint before the
rumor spreads. One branch keeps the normal programmed probability of sharing
(0.6–0.9 per minute when an eligible post is in the account's followed feed).
The other restores the identical checkpoint and multiplies that probability
by 0.2 for unverified content, making it 0.12–0.18. Both branches retain the
same seed, clock, accounts, graph and counter-based random draws.

The lower probability is imposed by the experiment. No account checks facts or
understands the text with a model. A reduction in sharing shows a consequence
of that rule; it does not establish a real confirmation prompt's effectiveness.

## Run it locally

Bootstrap as described in the repository README. No existing server or API key
is required. Start with a small run:

```sh
./scripts/campaign --pairs 10 --output data/campaigns/nubenorte-small
```

Then execute the full campaign:

```sh
./scripts/campaign --pairs 1000 --output data/campaigns/nubenorte-1000
```

The two default workers own separate loopback servers, controllers, databases,
checkpoints and output roots. Each controller retains its real OASIS interpreter
between worlds, explicitly closing the previous database before opening the
next one. This avoids repeated heavyweight imports; social state is not reused.
The normal experiment runner retains its original fresh-worker behavior.
Use `--workers 1` to reduce concurrent resource use. `--population` accepts 4–100;
`--steps` must fit inside the case's configured horizon. Upstream source is not
patched and the three dependency environments stay separate.

Every completed pair is appended and fsynced to `pairs.jsonl`. The overview is
updated every five pairs. Stop with Ctrl-C, then resume with the same settings:

```sh
./scripts/campaign --pairs 1000 --output data/campaigns/nubenorte-1000 --resume
```

Resume verifies the scenario, seed range, upstream pins and relevant source
hashes. It skips completed seeds, preserves their records and starts new worlds
for unfinished pairs. Configuration/source changes, duplicate seeds, mismatched
starting hashes or an incomplete journal line fail closed. A partially executed
pair is not counted as complete. Engine evidence from that attempt is retained.

## Read the result

Open `report.html` directly, or start `./scripts/serve`, visit `/campaigns` and
select a saved campaign. The same report is available at
`/campaigns/nubenorte-1000`. Opening it makes no model calls and starts no worlds.
The bundled recorded example works on a fresh installation without generating
new results.

The interface separates the aggregate from an individual execution:

- Counts include the original publishing account plus accounts that reposted
  the rumor. They exclude inactive external account 0. They do not count views,
  beliefs, persuasion, churn or reputation.
- The trajectory shows mean and P10–P90 across synthetic runs, or one chosen
  seed. The bands are descriptive dispersion, not confidence about real people.
- The concrete message/account walkthrough uses the middle pair after sorting
  by final paired difference and seed. It does not select the largest effect.
- The histogram includes positive differences, ties and negative differences.
  Differences subtract the pause branch from the normal branch in the same seed.
- Relative reduction is the paired mean difference divided by the mean normal
  endpoint, not an average of per-seed percentages.

There are only three graph patterns: the ring's longer-link offset depends on
`seed % 3`. Seeds also vary the sharing draws. A thousand executions do not
represent a thousand calibrated social networks or customer populations.

## Costs, provenance and stored evidence

Each pair records zero model calls and zero model API USD, plus measured elapsed
seconds. Local compute cost is **unknown/not priced**, not zero. Worker overlap,
startup and shutdown mean the sum of pair durations differs from campaign wall
time; the report records execution segments separately. No `.env` is read by
this command and no paid policy is instantiated. The controller's `NoLLM`
client rejects accidental model calls.

`report.json` contains trajectories, per-tick world hashes and one illustrative
full world pair. `pairs.jsonl` retains every final OASIS world. Under
`worker-N/engine`, each branch keeps SQLite, agent workspaces/replay, saved
frames and provenance; checkpoints retain integrity manifests. OASIS diagnostics
in reuse mode remain in the first world's worker log. Nothing is auto-deleted.
These runtime artifacts remain gitignored. The recorded public fixture is a
separately labeled snapshot of synthetic data.

Runtime cleanup now closes the adapter-owned replay sink explicitly. Changed
adapter hashes deliberately prevent old checkpoints from silently resuming with
new code. Use the published `v0.2.0` code for checkpoints created by that release.
The new campaign work does not alter the published 0.2 source archive or tag.

## Recorded execution shipped with this example

The completed campaign used seeds 1000–1999 and took 1001.327 seconds (about
16 min 41 s) on the validation machine with two workers. At minute 8, mean
sharing counts were 39.043/50 for the normal rule and 7.623/50 for the pause
rule. The paired mean difference was 31.42 accounts. The difference's P10–P90
range was 24–39 accounts; all 1,000 observed differences were positive. That is
a descriptive result of this imposed rule, network family and horizon.

All 18,000 saved world frames and all 2,000 SQLite databases were checked.
Source hashes match the recorded runtime, all initial branch fingerprints
match their checkpoint worlds, and summary statistics reconcile with the
complete journal. The fixture and checks are in
[examples/recorded-campaign](../examples/recorded-campaign/README.md).

The full native suite passed 111 tests in 383.45 seconds while the large
campaign was running. An additional real SIGTERM/resume test passed in 79.45
seconds. CI collects that additional test as part of the complete suite.

An additional application-entrypoint check exercises `/campaigns`, the recorded
HTML and the JSON attachment through the actual operator app; the catalog
checks passed 2 tests in 2.06 seconds.
