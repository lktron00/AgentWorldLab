# Working on Agent World Lab

- Use the three real upstream engines. Never silently fall back to synthetic replacement implementations.
- Do not merge the Python environments: their dependencies conflict.
- AgentSociety owns the clock and agent lifecycle; OASIS owns social state. Preserve the frozen-observation/ordered-commit boundary.
- Run `./scripts/test tests/test_contracts.py -q` for contract changes and `./scripts/test tests/test_integration.py -q` for runtime or persistence changes.
- The default experiment is offline and scripted. Do not introduce paid model calls or telemetry into the baseline.
- Do not claim scientific validity from the toy diffusion scenario.
- Never edit `vendor/` implicitly. Pin deliberate upstream upgrades in `upstreams.json`, refresh the appropriate runtime lock and run integration tests.
- Keep the native server bound to loopback until authentication and tenant isolation are implemented. Containers may listen on their isolated network, but host port publishing must use `127.0.0.1` (as in `compose.yaml`). Never recommend public hosting.
