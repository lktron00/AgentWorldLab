# Nine-case all-AI study within one cumulative US$10 budget

This study extends the recorded 20-account Luna pilot. Its budget is **US$10 total**, including the prior US$0.8736880250. The new runner independently reconciles the prior receipts, pins their hash and permits at most US$9.1263119750 in additional generation cost. It never resets an existing output directory or overwrites its ledger.

```sh
./scripts/study --budget-total-usd 10 --max-pairs 200 \
  --output data/studies/nine-cases-10usd
```

This is explicitly paid. Configure the ignored private `.env` first. Inspect `/studies/nine-cases-10usd` on the loopback dashboard; the `/campaigns` catalog links to it. Refresh reads a saved snapshot and never triggers model calls.

## Predeclared cases

| Domain | Case | Fixture state | Public attachment |
| --- | --- | --- | --- |
| Files | Delayed folder index | No permanent loss | Relevant sample and delayed index |
| Files | Deletion without recoverable copies | Permanent loss | Convergent storage, replication and restore records |
| Files | Stale reassurance | Permanent loss | A clean sample taken before the incident |
| Payments | Pending authorization | No duplicate settled charge | Authorization distinguished from settlement |
| Payments | Two settled captures | Duplicate settled charge | Two capture IDs for one order, no reversal |
| Payments | Very small sample | No duplicate settled charge | Two orders from one branch, with explicit limits |
| Software | Scanner false positive | Artifact intact | Matching digest and signed manifest |
| Software | Modified package | Unauthorized modification | Digest mismatch and invalid signature |
| Software | Audit of the wrong version | Unauthorized modification | A clean audit of the previous version |

All companies, records, hashes, payments and incidents are synthetic. There are no real charges, package installations, attacks or customer messages. The state is designed by the fixture; models receive only their role, goal, scoped social feed, own history, memory and information they choose to consult. They never receive fixture truth, global outcomes or the condition name.

The model stays `gpt-6-luna` with low reasoning effort. Each pair uses 20 active accounts for 10 turns in two conditions. Both conditions share an exact step-0 checkpoint, the same role assignment and private records. The page initially offers a generic status. In the diagnostic condition, a case-specific attachment becomes available at minute 2; it may be useful, incomplete, stale or about the wrong version. A public update notice appears in both conditions. Execution order alternates across repetitions. Cases are scheduled round-robin until the cumulative budget cannot reserve another bounded model request.

## Agent actions and observations

Each account chooses one action per turn: wait, post, repost an eligible visible message, inspect the public status, or inspect its own private record. A consultation consumes the turn and returns its result for the next turn. Private record identifiers are scoped to an account; a normalized local identifier does not grant access to another account's data. Some accounts observe no local anomaly even when the global problem is real.

No sharing-rate multiplier, target number of reposts or preferred answer is supplied. Models declare the probability that the case's question is true, assess observed evidence as insufficient/supporting/contradictory/mixed, and may cite visible post/document IDs. Invalid references are recorded as a data-quality flag. A brief public justification is stored; internal reasoning is not exposed.

A completed but invalid model action retains its original usage receipt. Up to two additional model samples of the identical observation may be attempted. There is no scripted action fallback. Three invalid samples stop that pair and move to the next case; the cost remains allocated to that case. A worker stops after a transport failure with missing usage. The supervisor audits the saved data, quarantines the entire maximum reservation and continues at the next scheduled case. It never repeats an unknown request or calls it free.

AgentSociety 2 schedules and persists all active accounts, OASIS owns social state, and an operator-only OpenEnv endpoint commits validated account-ID-ordered actions. All decisions use a frozen pre-tick world. A missing, duplicate, stale or invisible-post batch changes no state. Account 0 remains a dormant technical account.

## Outcomes and dataset

The dashboard separates each case and shows complete-pair counts, both conditions' final declared probabilities, signed Brier-error differences, and allocated API cost. The Brier score is `(declared_probability - fixture_truth)²`, averaged over active accounts and then paired repetitions. Lower is better; a positive diagnostic-minus-generic difference means the attachment increased error in that experiment. The score is computed by the evaluator and is not a model reward or input.

The score describes model judgments against a known synthetic state. It does not validate human behavior, real-world incident rates or calibrated probabilities. Network topology has the base adapter's three limited patterns. The seed schedule advances by nine for a case, so each case retains one topology across its repetitions; comparisons across cases also change the domain, prompt and topology. Both conditions within a pair share the same topology and independently sample the same model family. Accounts within a world influence each other, so decision counts are not counts of independent replicates; the paired world is the repetition unit. Initial messages and private clues are fixture conditions. New post content is inspectable but not independently semantically labeled true or false.

The study maintains append-only `decisions.jsonl` and `costs.jsonl` journals. A derived `decisions.sqlite` index provides fast case/seed/condition/turn/account filtering. The index can be queried while the study runs and downloaded after its WAL is checkpointed at shutdown. Rows distinguish applied actions from uncommitted proposals. An incomplete final pair is preserved but excluded from paired aggregate outcomes. This also makes budget censoring explicit rather than treating unfinished trajectories as completed experiments.

## Cost controls and audit

The new generation ledger has one shared remaining budget. Exact input counts and up to 2,048 output tokens, including reasoning, are reserved before each generation. Confirmed spend plus every simultaneous reservation must fit within the remaining budget. Input reservations use the larger input/cache-write rate. A token-based pacer smooths requests; up to 20 account decisions can be in flight. When a temporary reservation blocks another call, the runner waits for known calls to settle before declaring the budget exhausted.

The ledger includes every paid attempt, cache writes and reported output. Reasoning is already included in output and is never charged twice. Amounts are usage-based cost calculations, not final billing invoices. Tax, local infrastructure and Codex development credits are excluded. The gate may leave a small unused balance when another bounded request cannot fit; it does not waste tokens to hit a round dollar amount.

At shutdown the offline auditor independently reconciles every saved provider request/response and known paid attempt, includes the verified prior debit, replays the simultaneous-reservation budget gate, reconstructs all applied observations and private checks, verifies every engine action and frame hash, compares OASIS databases, and checks the derived decision index. It permits explicitly marked uncommitted proposals, never counts them as applied actions, and records the auditor's source hash. Unknown requests retain their original maximum in every replayed budget check. `usage_complete=false` identifies a cost interval rather than an exact usage total; `budget_bounds_verified=true` verifies the ceiling, including all unknown maxima.

```sh
.venv-api/bin/python -m worldlab.study_audit data/studies/nine-cases-10usd --allow-quarantined
```

Full local data stays under the ignored study directory. Source snapshots and upstream/dependency pins are retained with the execution. Never delete or reset a cost ledger to reclaim reservations. Keep the native server on loopback until production authentication and tenant isolation exist.


## Recovering a stopped run

`./scripts/study-resume --output data/studies/nine-cases-10usd` accepts only a failed or interrupted study with a completely reconciled, untruncated journal and unchanged case definitions, prompts, model and prices. It audits the dataset first, restores the confirmed spend and contexts from the existing ledger, reuses the existing SQLite index, and continues at the next scheduled case/seed. It never creates a fresh budget. A writer lock prevents two resume processes.

The interrupted pair and its paid, unapplied proposals remain in the dataset and stay excluded from paired aggregates. Resumption metadata retains the prior report, audit, server log, ledger hash and a fresh source snapshot under `resumptions/`. The original source snapshot remains intact. While running again, the prior audit is archived so it cannot be mistaken for the final full audit.

The [input-count endpoint](https://developers.openai.com/api/docs/guides/token-counting) counts the request before sending it to the model. After an input-count endpoint timeout, the same count-only request can retry twice before any generation reservation. Model generation still has SDK retries disabled. A generation without a usage receipt blocks ordinary resumption. The explicit `--quarantine-unknown` recovery option preserves its full maximum and excludes it from active-request capacity, while retaining it in the shared budget. No usage or zero-cost receipt is fabricated. A later genuine provider receipt can replace the bound.


## Recorded validation

The full source suite passed **127 tests** in 359.70 seconds after the recovery change, without paid model calls. A dated, explicitly provisional snapshot is saved in `docs/study-progress-validation.json`; `docs/study-running.png` shows the running dashboard.

An offline audit verified the first nine pairs (3,600 model decisions, 18 OASIS worlds and 198 engine frames). After a later input-count timeout, another audit verified 9,379 provider responses and US$2.9288145750 cumulative usage. It identified 19 paid proposals from an uncommitted tick. Those proposals remain inspectable and labeled, and resumption preserves the original budget ledger. The native viewer was checked on that tick: 19 registered proposals, zero applied actions.

These are historical progress checks. The study completed on 2026-10-25 with 102 complete pairs and 41,770 valid decisions across all nine cases. An independent final reconstruction matched `audit.json`; `verified=true` and `budget_bounds_verified=true`. Confirmed cumulative usage is US$9.9792478750, including the prior pilot. Seventeen unreceipted requests retain US$0.0197201250 in full reservations, so `usage_complete=false` and maximum cumulative exposure is US$9.9989680000. Four incomplete pairs and 50 unapplied valid proposals remain preserved and excluded from paired outcomes. Final checks and the screenshot are recorded in `docs/study-completion-validation.json` and `docs/study-finished.png`; the local dataset contains `results.md`, `audit.json` and `completion.json`.


## Finite job independent of the chat

```sh
./scripts/study-job --detach --output data/studies/nine-cases-10usd --max-pairs 200
```

The supervisor starts in its own OS session with redirected streams and no terminal dependency. It owns `.job.lock`, writes `job.json` heartbeats every five seconds and launches a worker that owns `.writer.lock`. One original ledger is shared by every recovery. At most 12 transient restarts are permitted by default; authentication errors, failed preflight audits and explicit interruptions require attention. An interrupted pair remains incomplete and the next scheduled seed is used. This is a finite job, not a new recurring paid experiment.

`costs.jsonl` adds a `quarantined` event referencing the unchanged reservation. Confirmed spend plus quarantined maxima plus all currently active reservations must fit within the original budget. The auditor independently recomputes the request maximum from the recorded rates and token limits and rejects a lost context that was regenerated. Quarantine is a conservative liability, never a confirmed charge.

The native catalog checks writer liveness instead of trusting a stale running flag. It shows recovery or required reconciliation when a writer disappears. Complete JSONL/SQLite exports wait until the job stops; the scoped decision viewer stays available throughout. At successful closure, `audit.json`, `completion.json` and `results.md` record the final outcomes, confirmed cost and maximum possible cost. The page labels confirmed cost explicitly.

For this local execution a finite macOS idle-sleep assertion follows the supervisor PID; it expires with that process and does not change permanent settings. A thread heartbeat named “Completar simulación AgentWorldLab” checks progress quietly, verifies final artifacts, reports completion or a concrete blocker. It was removed after verified completion; the chat and dashboard remain open.
