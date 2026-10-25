# 0.2 release readiness — work in progress

This file records evidence for the final 0.2 source revision. The previous 0.1
release remains public; 0.2 is being prepared as a draft for the next user
session. No release publication or launch announcement has been performed.

| Gate | Required evidence | Current state |
| --- | --- | --- |
| Real engines | Final native and Linux tests, exact upstream pins | Native targeted integration passed; final full suite running |
| Agent boundary | Observations/actions, reset tickets, alternate protocol tests | Scoped tests pass; explicit `/ws` MCP tunnel guard added |
| Reproducibility | Equal starting hashes and complete baseline self-check | Complete-trajectory checks implemented; integration passed |
| Model/cost path | Saved real-provider receipts and offline reconciliation | Six real calls, US$0.0004773; saved receipts reconcile |
| Interrupted costs | Durable-response recovery, pending/truncated cases | New audit tests pass; no model calls during audit |
| CLI cleanup | Actual SIGTERM after a committed step | Passed; report persisted and owned server exited |
| Report/UI | Escaping, read-only catalog and rendered desktop/mobile checks | Backend tests pass; browser verification pending |
| Clean installation | Fresh source archive on supported native/Linux targets | Pending final archive |
| Docker | Exact archive, non-root, offline suite/experiment | Pending final image |
| Public checks | CI on the exact release candidate | Pending updated candidate |
| Distribution | Archive, SHA256SUMS, exact commit and draft release | Pending final source |
| Launch handoff | Notes, limits and announcement draft | Drafts prepared; final audit pending |

## Existing real-provider evidence

The recorded validation uses the real OpenAI Responses API and real
AgentSociety/OASIS/OpenEnv engines: seeds 7/8, three decisions each, 3,358 input
tokens and 283 output tokens, with no unresolved usage. It is preserved in
`docs/ai-validation.json` and `examples/recorded-demo`. Sanitized provider/call
IDs are explicitly labeled; original usage and synthetic outcomes are retained.
No additional paid run is necessary to regenerate or audit this example.

## Limits for the announcement

One externally controlled account per world; scripted background policies; one
social scenario family; local operator trust; no public multi-tenant service,
hostile-code sandbox, validated human predictor or training reward. Old 0.1
checkpoints require the 0.1 release. Native targets are macOS ARM64 and Linux
ARM64/x86_64. USD estimates exclude compute, tax and development/Codex credits.
