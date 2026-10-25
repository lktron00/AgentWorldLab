# Compare an external AI policy with a visible-feed baseline

This experiment uses the real AgentSociety 2 scheduler, OASIS state and OpenEnv
client. The model runs in a separate external process. Background agents remain
scripted and offline; the normal dashboard and `examples/compare.py` never make
paid calls.

## Run an experiment

After the normal bootstrap, put your OpenAI API key in the project-root `.env`:

```dotenv
OPENAI_API_KEY=your_key_here
```

`.env` is ignored by Git. Keep it private (`chmod 600 .env`). Do not put the key
in scenario files, command arguments, reports or the browser. You can instead
set `OPENAI_API_KEY` in the shell or use `--env-file /private/path/experiment.env`.
This is an API credential, independent of the model selected in Codex.

```sh
./scripts/experiment --seeds 7 8 9 --steps 5 --budget-usd 0.10
```

No existing server is required. This command creates a new directory under
`data/experiments/`, starts its own server on a random loopback port, runs both
branches, writes the JSON/Markdown/HTML results and stops that server. Reports are also discoverable at `/experiments` in the local dashboard. It does not interrupt the
dashboard on port 8765. `--output data/experiments/my-run` chooses a NEW output
directory. Existing directories are rejected to prevent silent cost-journal
overwrites and accidental mixing of runs.

Defaults: GPT-6 Luna, low reasoning effort, 1,024 maximum output tokens per
decision, three seeds, 20 background accounts, two warmup steps and five
experimental steps per branch. For another recorded price-book model:

```sh
./scripts/experiment --model gpt-6.1-sol --effort medium \
  --seeds 7 --steps 3 --budget-usd 0.10
```

Use `--policy baseline --seeds 7 --steps 3` for an offline end-to-end self-check.
Both branches then use the SAME deterministic policy. It makes no model calls,
requires identical full-world hashes at every step and is clearly labeled
`offline-baseline-self-check`. It is not evidence of a real AI run.

## What the agent observes and may do

The dedicated agent server always returns `agent-v1`, on reset and every step:

- Its account identity, current step/time and own last 12 posts.
- IDs of accounts it follows (initially accounts 1 and 2).
- The bounded chronological feed from those accounts, with public post fields
  and an eligibility flag for reposting.
- Episode termination/status and the action names.

It does not receive the global graph, hidden posts, global share counts,
scenario seed/rules, metrics or the operator's `verified` annotations. References
to original post IDs inside visible reposts are public lineage; their hidden
rows and annotations are not exposed. Reposting requires the EXACT eligible
`post_id` in the current feed. A guessed hidden ID and an already-shared root
are rejected before either engine or the simulation clock changes. Only the
operator may assign ground-truth annotations; the AI cannot self-certify posts.

The runner creates distinct ephemeral bearer tokens for agent and operator.
The agent token grants ONLY the OpenEnv `/ws` protocol. Reset also requires
an operator-issued one-use ticket (expires after five minutes). Only the operator
chooses scenario, seed, annotations and checkpoint; the agent cannot elevate its
view or alter those parameters through a reset payload. HTTP run listing,
snapshots, checkpoints, frames, exports, docs, MCP and harness endpoints are
not available with that token. The operator reads full state for the report;
that state is never passed to `OpenAIPolicy`. Tokens stay in memory/process
environment and are not saved in the artifacts. The simulation subprocess
does not receive `OPENAI_API_KEY`.

This is a local capability boundary, not an OS sandbox for hostile Python
programs running as the same user. A trusted model receives only its prompt
and one action tool; it has no filesystem, network or operator tools. Local
files and the default dashboard's operator API remain trusted operator tools.
Use the dedicated server/runner for restricted observations.

## What is compared

Each seed creates one warmup world and checkpoint. The baseline and candidate
restore that exact checkpoint. The runner checks a SHA-256 fingerprint of the
entire social world, clock and step before either branch advances. Both retain
the SAME `open` background policy and scenario. Only account 0's policy changes.

The deterministic baseline (`first-visible-repost-v1`) reposts the newest
eligible visible item, otherwise waits. The candidate is instructed to share
cautiously and require concrete supporting evidence in visible text; it can
also wait or ask for evidence. Both have the same observations/actions. This is
a simple behavioral comparison, not a calibrated human model or a validated
intelligence benchmark. No reward is assigned. A `verified` label is a scenario
annotation, not an automated factuality judgment: an unlabeled question is also
counted as unverified. Reported count differences do not establish misinformation
reduction, persuasion or a causal effect in people.

Model calls use the Responses API and a strict `choose_action` function. The
exact observation and prompt, public action justification, function arguments,
response ID, returned model, usage and latency are recorded. Internal reasoning
items are not recorded. Feed text is explicitly treated as untrusted data.
No tools other than choosing one action are available to the model. There is no
fallback to scripted decisions and no automatic retry after a failed call.

## Cost accounting and failure behavior

`report.html` is the standalone visual report, with trajectories, costs,
decisions and the agent's limited observations. `report.md` is the text summary; `report.json` includes trajectories, run and
checkpoint IDs, world fingerprints, per-branch/per-seed costs and the paired
mean differences. `signal_sharers` tracks only accounts sharing the original
scenario signal (root post 1), excluding account 0. `external_signal_reposts`
counts that agent's amplification of the same signal. These distinguish the
original signal from new questions or other posts. `unverified_sharers` remains
a separate annotation-based count. `decisions.jsonl` records decisions and their application.
`costs.jsonl` is an append-only, flushed journal with price book, reservations,
responses and usage receipts. Native engine data lives under `engine/`.

Before generation, the runner uses the official input-token counting endpoint
on the exact prompt/tool schema. It reserves counted input at the higher of
normal input/cache-write rates plus the configured maximum output. Input is
limited to 32,000 tokens, below the long-context price threshold. The model
request explicitly selects the global standard endpoint/tier, `store=False`,
bounded output and no automatic SDK retries.

Recorded USD costs are ESTIMATES from provider-reported usage and the price book
checked on 2026-10-25. Cache reads and writes have separate rates; reasoning
tokens are already part of output and are not counted twice. Rates and source
links are copied into every report. The estimates exclude tax, currency
conversion, compute/storage, development/Codex credits and any account-specific
discounts. They are not an invoice or a provider-enforced account spending cap.
Token-count requests are recorded as preflight, not generation usage receipts.
Review provider billing for any charges outside returned generation usage.

An invalid/refused/incomplete model response is still accounted for before its
action is parsed. If a generation times out, the process is interrupted or
usage is missing, its reservation remains unresolved; it is NOT reported as a
free call and no further paid call is attempted. Previously saved experiment
results survive. On abrupt termination, the `reserved` event without a matching
receipt in `costs.jsonl` identifies the uncertain request; reconcile it with
provider billing. Re-running creates a new experiment rather than retrying an
ambiguous billed request. Checkpoints permit world branching; LLM decisions are
not guaranteed deterministic.

OpenAI reference sources:

- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Responses input-token counting and usage](https://developers.openai.com/api/reference/python/resources/responses)
- [GPT-6 Luna standard rates](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [GPT-6.1 Sol standard rates](https://developers.openai.com/api/docs/models/gpt-6.1-sol)


## Audit or rebuild a report after interruption

```sh
./scripts/report data/experiments/YOUR_EXPERIMENT --check
./scripts/report data/experiments/YOUR_EXPERIMENT
```

The first command is read-only. The second writes derivative `report.html` and
`audit.json`; it does not overwrite the source report, decisions or cost journal.
Neither command starts a worker or contacts a model. A response saved before its
`charged` event can supply a recovered receipt at the **recorded** prices. A
reservation with no verifiable response remains unresolved. A truncated tail is
flagged and contradictory complete events fail closed. An unfinished source
report is labeled unfinished; the auditor does not infer whether its process
is still running. Check the process before starting another experiment.

The local catalog hides stale cost estimates when the journal is newer than its
saved summary. Opening the report performs an offline audit. Read-only JSON is
at `/lab/experiments/{name}/report.json`. Content is escaped, and the HTML page
does not execute model-supplied markup. The default dashboard is a trusted
operator interface; agent capabilities do not grant these endpoints.

## Explore an evidence-bearing scenario

`scenarios/evidence.json` includes an explicitly invented test record in the
visible text. Pass it with `--scenario scenarios/evidence.json` to compare
decisions under a different information condition. The operator annotation is
still hidden from the agent; textual evidence is not independently verified.
This changes scenario inputs, not the world mechanics or the model's tools.
Every new report records the application version, policy/wrapper source hashes
and upstream revisions in addition to native engine provenance.
