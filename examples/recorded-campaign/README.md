# Recorded Nube Norte campaign

This is a recording of an actually executed synthetic campaign, not a browser
simulation or a live model call. AgentSociety 2, OASIS and OpenEnv executed
**1,000 pairs / 2,000 worlds**, with 50 background accounts and eight steps per
branch: **800,000 scripted account decisions**.

The campaign ran on 2026-10-25 in about 16 minutes 41 seconds with two isolated
workers. Model calls and model API cost were zero. Local compute, infrastructure
and development credits are not priced in that value.

At minute 8, the normal branch averaged **39.043** sharing accounts out of 50;
the pause branch averaged **7.623**. The paired mean difference was **31.42**
accounts, or **80.475%** relative to the normal mean. These counts include the
initial author. This is the consequence of an explicitly imposed sharing rule,
not a measured effect in people, a confirmation feature or a real company.

`report.json` retains all 1,000 seed trajectories and world hashes, summary
statistics and one full illustrative world pair. `verification.json` records
checks of **all 18,000 saved frames and 2,000 real OASIS SQLite worlds**, distinct
seeds/world IDs, checkpoint identity, source hashes and journal reconciliation.
The raw databases, per-account workspaces and complete journal stay in the local
gitignored campaign directory. This fixture contains only synthetic content;
no API credentials or private provider identifiers were used.

Rebuild the portable interactive example, with no engines or paid calls:

```sh
python3 scripts/build-campaign-example.py
python3 scripts/build-campaign-example.py --check
```

The resulting `web/nubenorte-report.html` is labeled as a recording. A fresh
installation links it from `/campaigns`. To execute a new campaign, see
[the scenario guide](../../docs/campaigns.md).
