# 0.2 release readiness — 2026-10-25

The 0.2 release is prepared as a **draft**, for publication in the next user
session. The announcement remains a draft. The source is public; preparing
this release does not publish the release or send an announcement.

Runtime source tested below: `1aeea6fc893ac612e668263b476e85f78e363d5a`.
The final release adds documentation/screenshots to that source. Its exact
commit, CI run, archive SHA-256 and image identity are recorded in
`validation.json` attached to the draft release. Match that manifest to the
release target before publishing; it avoids putting a self-referential commit
hash or archive hash inside the archive itself.

| Acceptance gate | Evidence | Result |
| --- | --- | --- |
| Three real engines | Pinned AgentSociety 2 2.9.3, OASIS 0.2.5 and OpenEnv 0.10.1.dev0; doctor verifies package versions and raw pinned Git blobs; full real-engine suites | Passed |
| Agent boundary | Separate bearer capabilities, one-use reset tickets, limited observations, visible-post guards; `/ws` also rejects tunneled MCP and oversized frames before reaching an environment | Passed |
| Reproducibility | Actual checkpoint restoration and complete baseline/candidate trajectory hashes; CLI self-check asserts both trajectories match | Passed |
| Optional model and costs | Six real provider receipts; 3,358 input / 283 output tokens; US$0.0004773; zero unresolved calls; saved pricebook reconciliation | Passed |
| Interrupted accounting | Tests recover a durable response without a charge event; pending/truncated receipts remain unknown; contradictions fail closed; read-only audit preserves source files | Passed |
| CLI lifecycle | Real SIGTERM after a committed step preserves the report and reaps its owned server; invalid configuration fails before starting model calls | Passed |
| Reports and local UI | Desktop dashboard created/stepped/checkpointed a real world and completed both policy branches; real/recorded reports opened; decisions and limited observations expanded; report/catalog checked at 390 × 844 without horizontal overflow | Passed |
| Fresh macOS installation | Clean archive; native ARM managed Python 3.12.13/3.11.15; all engines healthy; 105 passed in 203.94 s; documented baseline experiment completed with zero model calls | Passed |
| Linux x86_64 installation | Public clean-checkout bootstrap; 105 passed in 179.16 s; offline CLI and journal audit in [CI](https://github.com/lktron00/AgentWorldLab/actions/runs/40183658456) | Passed |
| Linux ARM64 Docker | Clean source-archive build; non-root UID 10001; 105 passed in 305.38 s with `--network none`; complete offline CLI experiment with zero model calls and equal trajectories | Passed |
| Distribution | Final CI, deterministic source archive, checksums and authenticated round-trip asset verification are recorded in the attached `validation.json`; release remains draft | See release manifest |
| Launch handoff | README, AI/extension guides, security/contribution policy, license notices, version 0.2.0, release notes and English/Spanish launch copy are included | Ready |

## Install defects found and fixed

A clean Apple Silicon installation exposed a cached Intel Python selected by a
bare version request. Bootstrap now requests the OS/architecture/libc explicitly,
checks existing environments, and does not overwrite global Python command
links or delete mismatched environments.

An upstream AgentSociety commit contains CRLF Python blobs despite its LF
attributes. Git's normalized status could incorrectly mark a byte-identical
checkout dirty. Bootstrap/doctor now compare raw Git blob hashes, file modes,
staged changes and untracked files. Tests prove real modifications are still
rejected. Upstream files and commits were not patched.

## Real-provider execution

The saved execution uses the real OpenAI Responses API and all three real
engines: seeds 7/8, three decisions each. Original-signal sharers were 18/15 and
19/19 (baseline/candidate). The candidate asked for evidence and did not repost
the original signal. Two toy seeds show an executed comparison; they do not
establish human predictive validity or general model superiority.

[The sanitized summary](ai-validation.json) and
[recorded example](../examples/recorded-demo/README.md) preserve original usage
and synthetic outcomes. Provider/call identifiers are explicitly sanitized.
Rebuilding or auditing the example makes no paid calls. No additional paid
inference was used during this release-readiness pass. USD values are estimates
from recorded reported usage, excluding compute, tax and development credits.

## Browser and artifact checks

[Dashboard](dashboard.png), [experiment catalog](experiments.png) and
[recorded report](report.png) screenshots show the actual rendered interface.
The recorded example is labeled as a recording. A private live report's HTTP
JSON download was checked for the attachment header and six reconciled receipts.
HTML/JSON example regeneration is deterministic and checked in CI. Report text
is escaped; catalog paths reject traversal and symlink escapes. Tracked source
and the release archive are checked for the configured credential and excluded
private/runtime files before upload.

## Deliberate limits

One externally controlled account per world; scripted background policies; one
social scenario family; local operator trust; no public multi-tenant service,
hostile-code sandbox, validated human predictor or training reward. The
operator dashboard is unauthenticated and stays local. Old 0.1 checkpoints
require the 0.1 release. Native targets are macOS ARM64 and Linux ARM64/x86_64;
Windows-native and Intel macOS are unverified. Installation needs networking;
the baseline works offline after installation.

Publishing the draft release and announcing it remain the launch actions for
the next user session. Draft assets require an authenticated maintainer;
check anonymous release-asset downloads after publication.
