# Security policy

Agent World Lab 0.2 is an experimental **local** laboratory. It is not a public
multi-tenant service or a sandbox for hostile programs running as the same OS
user. Keep the native server on loopback. Docker Compose publishes only on
`127.0.0.1` and runs as a non-root user; do not change the host binding to
`0.0.0.0`.

## Operator and agent boundaries

The normal dashboard/API is a trusted local operator interface. It exposes full
world state, saved runs and experiment reports without user authentication.
HTTP and WebSocket requests enforce local Host and same-origin browser access,
reducing drive-by browser access and DNS rebinding. These checks do not protect
against other processes already running on the same machine.

`scripts/experiment` starts a separate server with distinct ephemeral operator
and agent bearer capabilities. The agent capability grants only OpenEnv `/ws`;
operator data, alternate protocols and reset configuration require the operator
capability. A reset consumes an operator-issued one-use ticket. Observations
and action permissions are enforced server-side, on every step. The model is
given only the scoped observation and one action tool, with no filesystem,
network or operator tools.

The simulation subprocess does not receive `OPENAI_API_KEY`. Store that key in
the private, gitignored `.env` or the external policy's environment. Never place
it in scenarios, source files, browser inputs, issues or report attachments.
Docker build contexts exclude `.env*`, local runs and virtual environments.

## Artifacts and model spending

Checkpoints are trusted local artifacts. Hashes detect corruption and version
mismatch, not malicious authorship. Do not import checkpoints from untrusted
people. Keep agent state, social content and logs private when needed. JSON,
HTML reports and exports can contain the experiment's visible text and public
decision justifications; review them before sharing. Report text is escaped,
and dynamically served reports use a restrictive content-security policy.

The baseline and CI make no paid model calls. Optional model experiments use
budget reservations, bounded output and no automatic SDK retry. Estimates use
reported tokens and recorded prices; they are not a provider account spending
limit or invoice. A failed generation can have been billed. Missing receipts
remain unresolved. `scripts/report` audits saved journals without starting an
engine or model, and preserves source artifacts.

## Reporting a vulnerability

Use the repository's **Security → Report a vulnerability** feature. Do not
include working secrets in public issues. If private reporting is unavailable,
open an issue requesting a private contact without exploit details. Security
fixes target the latest release.
