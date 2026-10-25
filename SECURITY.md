# Security policy

Agent World Lab 0.1 is a local research prototype. It has no authentication or
tenant isolation and must not be publicly hosted. Run the native server on
loopback, or use `docker compose up --build`, whose published port binds to
`127.0.0.1`. The container runs as a non-root user. Do not change the published
address to `0.0.0.0` on the host.

HTTP and WebSocket requests enforce local Host and same-origin browser access.
This reduces drive-by browser access and DNS rebinding; it does not protect
against other users or processes already on the same machine.

Checkpoints are trusted local artifacts. Hashes detect corruption and version
mismatch, not malicious authorship. Keep their agent state, social content and
logs private when necessary. Do not import checkpoints from untrusted people.
Exports contain experiment data; review them before sharing.

Please report vulnerabilities through the repository's **Security → Report a
vulnerability** feature. Do not include working secrets in public issues.
If private reporting is unavailable, open an issue requesting a private contact
without disclosing exploit details. Security fixes target the latest release.
