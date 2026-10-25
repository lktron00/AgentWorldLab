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

A completed but invalid model action retains its original usage receipt. Up to two additional model samples of the identical observation may be attempted. There is no scripted action fallback. Three invalid samples stop that pair and move to the next case; the cost remains allocated to that case. Transport failures with missing usage retain their maximum reservation and stop new spending for reconciliation.

AgentSociety 2 schedules and persists all active accounts, OASIS owns social state, and an operator-only OpenEnv endpoint commits validated account-ID-ordered actions. All decisions use a frozen pre-tick world. A missing, duplicate, stale or invisible-post batch changes no state. Account 0 remains a dormant technical account.

## Outcomes and dataset

The dashboard separates each case and shows complete-pair counts, both conditions' final declared probabilities, signed Brier-error differences, and allocated API cost. The Brier score is `(declared_probability - fixture_truth)²`, averaged over active accounts and then paired repetitions. Lower is better; a positive diagnostic-minus-generic difference means the attachment increased error in that experiment. The score is computed by the evaluator and is not a model reward or input.

The score describes model judgments against a known synthetic state. It does not validate human behavior, real-world incident rates or calibrated probabilities. Network topology has the base adapter's three limited patterns. The seed schedule advances by nine for a case, so each case retains one topology across its repetitions; comparisons across cases also change the domain, prompt and topology. Both conditions within a pair share the same topology and independently sample the same model family. Accounts within a world influence each other, so decision counts are not counts of independent replicates; the paired world is the repetition unit. Initial messages and private clues are fixture conditions. New post content is inspectable but not independently semantically labeled true or false.

The study maintains append-only `decisions.jsonl` and `costs.jsonl` journals. A derived `decisions.sqlite` index provides fast case/seed/condition/turn/account filtering. The index can be queried while the study runs and downloaded after its WAL is checkpointed at shutdown. Rows distinguish applied actions from uncommitted proposals. An incomplete final pair is preserved but excluded from paired aggregate outcomes. This also makes budget censoring explicit rather than treating unfinished trajectories as completed experiments.

## Cost controls and audit

The new generation ledger has one shared remaining budget. Exact input counts and up to 2,048 output tokens, including reasoning, are reserved before each generation. Confirmed spend plus every simultaneous reservation must fit within the remaining budget. Input reservations use the larger input/cache-write rate. A token-based pacer smooths requests; up to 20 account decisions can be in flight. When a temporary reservation blocks another call, the runner waits for known calls to settle before declaring the budget exhausted.

The ledger includes every paid attempt, cache writes and reported output. Reasoning is already included in output and is never charged twice. Amounts are usage-based cost calculations, not final billing invoices. Tax, local infrastructure and Codex development credits are excluded. The gate may leave a small unused balance when another bounded request cannot fit; it does not waste tokens to hit a round dollar amount.

At shutdown the offline auditor independently reconciles original provider requests/responses and all paid attempts, includes the verified prior debit, replays the simultaneous-reservation budget gate, reconstructs all applied observations and private checks, verifies every engine action and frame hash, compares OASIS databases, and checks the derived decision index. It permits explicitly marked uncommitted proposals from the final partial tick, never counts them as applied actions, and records the auditor's source hash.

```sh
.venv-api/bin/python -m worldlab.study_audit data/studies/nine-cases-10usd
```

Full local data stays under the ignored study directory. Source snapshots and upstream/dependency pins are retained with the execution. Do not delete, restart or bypass a cost ledger to reclaim reservations. Keep the native server on loopback until production authentication and tenant isolation exist.


## Recovering a stopped run

`./scripts/study-resume --output data/studies/nine-cases-10usd` accepts only a failed or interrupted study with a completely reconciled, untruncated journal and unchanged case definitions, prompts, model and prices. It audits the dataset first, restores the confirmed spend and contexts from the existing ledger, reuses the existing SQLite index, and continues at the next scheduled case/seed. It never creates a fresh budget. A writer lock prevents two resume processes.

The interrupted pair and its paid, unapplied proposals remain in the dataset and stay excluded from paired aggregates. Resumption metadata retains the prior report, audit, server log, ledger hash and a fresh source snapshot under `resumptions/`. The original source snapshot remains intact. While running again, the prior audit is archived so it cannot be mistaken for the final full audit.

The [input-count endpoint](https://developers.openai.com/api/docs/guides/token-counting) counts the request before sending it to the model. After an input-count endpoint timeout, the same count-only request can retry twice before any generation reservation. Model generation still has SDK retries disabled. A generation without a usage receipt blocks resumption; its reservation must be reconciled rather than assumed free.
