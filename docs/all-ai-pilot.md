# Nube Norte: all active accounts decide with AI

This is a deliberately small synthetic experiment, separate from the scripted 1,000-pair campaign. It studies decisions made by language models under these prompts, roles, topology and information fixtures. It does not predict how real customers behave.

## Run and inspect

Configure `OPENAI_API_KEY` in the ignored, private `.env`, then run:

```sh
./scripts/pilot --population 20 --steps 10 --pairs 10 --budget-usd 10 \
  --output data/pilots/nubenorte-luna-20x10
```

The runner makes up to 4,000 valid model decisions: 20 accounts × 10 turns × two conditions × 10 repetitions. It never overwrites an existing output. It has no automatic model retry or scripted fallback. If a model response is invalid or a provider call is uncertain, the run stops with its saved evidence. An interrupted run is not automatically resumed; preserve and reconcile its costs before starting another paid run. The US$10 gate applies to this runner's generation requests, not other applications using the same provider account.

Open the native loopback server with `./scripts/serve`, then visit `http://127.0.0.1:8765/campaigns`. The pilot view supports repetition, condition, turn and account filters. Each decision shows its visible feed, own history, private role/observations, status checks, action, short public justification, self-reported probability of permanent loss, token counts and provider response ID. Downloads include all decisions, results, cost reservations/receipts and the final independent audit.

## Experimental design

A fictional synchronization incident makes some folders disappear from the application. The initial post expresses concern about data loss. Twenty accounts have different roles and objectives: customers, support and integration technicians. All accounts use `gpt-6-luna` with low reasoning effort, the same action schema and the same instructions across both conditions. Account 0 is a dormant technical account inherited from the base adapter; it makes no decisions and is excluded from the active population.

For each repetition, both branches restore exactly the same step-0 checkpoint and use the same assignment of roles. Branch execution order alternates. The model sees neither condition names nor global outcomes, verification labels, hidden truth or other accounts' private observations. Model sampling is not deterministic: matching initial observations does not guarantee matching decisions, including before the intervention.

- **Generic status:** the status page says synchronization problems are under investigation.
- **Consultable diagnosis:** from minute 2, the same page adds a synthetic technical attachment describing a sample of 10,000 stored objects, successful direct downloads and a delayed folder index. Its limited sample is stated explicitly.

The fixture's operator truth is a delayed index without permanent loss. It is never inserted into model observations. It is a designed incident fixture, not a diagnosis obtained from a real storage service. Agents may infer a cause from their own observations and consulted evidence.

A model chooses exactly one action per turn: wait, post, repost an eligible visible post, or inspect the status page. A consultation returns a private result for the following turn; the agent chooses whether to publish anything about it. The consultation consumes its turn in both conditions. A same-time public notice announces that the page was updated at minute 2. There is no sharing-rate multiplier, preferred action, global reward or rule telling an agent to share less.

The coordinator gives each account its scoped observation at a frozen tick boundary. It does not give models operator credentials. A separate authenticated OpenEnv endpoint accepts exactly one action per active account. It rejects a stale, incomplete, duplicate or invisible-post batch before changing the world. AgentSociety 2 schedules and persists every account; OASIS applies social actions in account-ID order. Consultations are local fixture reads and add no hosted tool fee. The scripted baseline and its offline CLI do not invoke paid APIs.

## Outcomes and interpretation

The report displays every pair and describes signed diagnosis-minus-generic differences, including positive, negative and zero results. It shows initial-message sharers (including its initial author), original-message reposts, action counts, and each model's self-reported probability of permanent loss. New post content is available for inspection but is not automatically labeled true or false. A lower number of initial-message sharers alone does not establish improved decisions; that initial message expresses uncertainty. Self-reported probabilities are not validated or calibrated against people. Ten repetitions, one model family and a small set of network patterns support exploration, not general causal or behavioral claims.

## Budget and audit

Each request first uses the exact input-token counter. Before generation the shared Decimal-based ledger reserves counted input at the larger of standard input/cache-write rates plus the configured maximum output (2,048 tokens, including reasoning). Already spent cost and every simultaneous reservation count toward the cap. No request starts if its maximum would exceed the remaining budget. Up to eight calls run concurrently by default. There is no retry on timeouts or rate limits. Calls without verified usage retain their reservation and block further spending.

Every provider response is durably stored before an action is parsed. Cost is reconstructed from provider-reported input/cache/output token counts and the saved price book. Reasoning tokens are already part of output and are not charged twice. This is a usage-based cost calculation, not access to a final billing invoice. It excludes local infrastructure, tax and Codex development credits.

The first 100 decisions form a calibration sample within the planned 4,000 calls. Their average cost is extrapolated and displayed, with a warning that later memories and feeds can grow. The live budget gate continues to govern every subsequent request.

At successful completion, the independent offline auditor reconciles every model receipt, replays the concurrent budget gate, reconstructs every account's exact observation and memory, checks all committed actions against the model proposals, verifies paired initial worlds and all saved engine frame hashes, and checks the final OASIS databases:

```sh
.venv-api/bin/python -m worldlab.pilot_audit data/pilots/nubenorte-luna-20x10
```

Artifacts stay in the ignored `data/pilots/` directory. Source snapshots, upstream pins and dependency lock contents are saved with each pilot. Local browsing and auditing never trigger model calls. Keep the service bound to loopback; public hosting still requires authentication and tenant isolation.

## Recorded real run — 2026-10-25

The first completed run used 20 active Luna accounts, 10 turns and 10 paired repetitions. All 4,000 model decisions were applied and independently reconciled against their original provider requests/responses, 220 saved engine frames and 20 final OASIS databases. It took 1,461.568 seconds. The complete native suite passed 121 tests; the strengthened auditor regression also passed after that suite.

Provider-reported usage was 6,162,516 input tokens and 270,852 output tokens (including 170 reasoning tokens). Recorded API usage cost was **US$0.8736880250**, with zero unresolved calls. The maximum of already charged cost plus simultaneous reservations was US$0.8801498000, below the shared US$10 cap.

| Outcome across 10 complete pairs | Generic status | Consultable diagnosis |
| --- | ---: | ---: |
| Mean initial-message sharers, including the initial author | 1 | 1 |
| New posts | 356 | 370 |
| Reposts of other messages | 161 | 161 |
| Status consultations | 571 | 583 |
| Wait decisions | 912 | 886 |
| Mean final self-reported probability of permanent loss | 15.6% | 5.035% |

No account reposted the initial message in either condition. The diagnosis did not reduce total reposts in this run. It changed the models' declared estimates, with a mean paired difference of −10.565 percentage points; all ten paired differences were negative. These results describe this model, these roles and this fixture. They do not establish effects on people or calibrated loss probabilities.

The compact [validation recording](pilot-validation.json) preserves every pair's costs and final metrics, full aggregate results, token accounting, artifact hashes and the independent auditor's source hash. The execution source snapshot was captured at run start; the independent auditor was subsequently strengthened and records its own implementation hash. Full local observations, provider responses and engine data are retained in `data/pilots/nubenorte-luna-20x10/`. No additional model calls are needed to inspect or re-audit them.
