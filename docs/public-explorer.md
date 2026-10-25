# Public results explorer

[Open the explorer](https://agent-world-lab-explorer.lktron.chatgpt.site).
Anyone can browse without an account or installation. This is a static recording,
with no model key, backend connection, analytics or new model calls. The native
simulation server stays on loopback.

## What visitors can explore

- Nine fictional cases in cloud storage, billing and software security.
- All 102 complete paired comparisons: 20 AI agents, ten turns and two conditions.
- 40,800 applied decisions, including reasons, messages, consulted sources,
  original scoped observations, token usage and recorded cost.
- The original following graph, 1,796 recorded repost events across the complete
  worlds, a turn-by-turn action matrix and paired probability trajectories.
- Both favorable and unfavorable outcomes, the study’s accounting and its limits.

Choose a case and repetition, switch conditions, then select an account or a
matrix cell. Play the ten recorded turns or move the slider. The share button
copies the exact case, seed, condition, turn, account and view. On phones, the
account picker and bottom sheet make decisions accessible without targeting a
small node.

## Reading the maps correctly

**Conexiones** uses the `following` lists in the original agent observations.
A follows B means B is a potential source for A’s chronological feed. Highlighted
arrows point from the followed source toward the follower. A following connection
does not establish that a particular message was shown, read or believed.

**Reenvíos** shows only repost actions, accumulated through the selected turn.
Each arrow goes from the author of the visible source post toward the account
that reposted it. The builder requires that the chosen post exists in that
account’s recorded feed. It does not infer message exposure from network links.
Repeated routes are grouped visually; event counts retain all recorded reposts.
The original following graph remains faintly visible as context.

Node positions are a deterministic visual layout, never geographical locations.
The same pair uses the same layout across conditions. Account 0 is a technical
account and is excluded from the 20 active AI agents.

**Decisiones** is the complete 20-account by ten-turn action matrix for the selected
condition. Colors encode actions or declared probabilities; probabilities are the
models’ judgments, not measured risks at a real company. The trend beneath the
map describes the selected repetition. The nine summary cards aggregate all
complete repetitions of each case.

Four incomplete pairs are preserved in the public source archive but excluded
from these maps and comparisons. The full archive contains 41,770 valid decisions;
this explorer contains the 40,800 decisions belonging to complete pairs.

## Build from the public repository

Python’s standard library builds the site from the committed, sanitized records.
It never reads the ignored private study dataset or starts the engines. Node 22
runs the small model tests; no npm packages are needed.

```sh
python3 scripts/build-study-example.py --check
node --test explorer/test-model.mjs
python3 scripts/build-explorer.py
python3 scripts/build-explorer.py --check
python3 -m http.server 8791 --bind 127.0.0.1 --directory dist/explorer
```

Open `http://127.0.0.1:8791`. Serve the files over HTTP/HTTPS so ES modules and lazy
loading work. The separate `web/recorded-study.html` remains the self-contained
sample for opening directly from a downloaded repository.

The build writes the app, presentation PDF, index and 102 compressed pair files.
A selected pair is loaded on demand and its uncompressed SHA-256 checked before
rendering. A bounded in-memory cache keeps recent worlds. The build verifier
checks the manifest, node identities, graph links, decision coverage, hashes and
every repost against its original visible source. Layout and URL/timeline tests
prevent invalid shared seeds and cross-condition or future repost leakage.

## Hosting and source

Canonical source is in `explorer/` and `scripts/build-explorer.py`. The public
[recorded study](../examples/recorded-study/README.md) remains the data source of
truth. The site serves only generated public artifacts; it cannot start a
simulation, inspect local files or spend the experiment budget.

The deployment uses a dedicated Sites source checkout with a persisted
`.openai/hosting.json` and `static.directory` set to `dist`. Copy a verified build
there, commit and push that exact state, package it, save a version and deploy it.
Keep credentials out of source and archives. The GitHub project is independent of
the hosting provider; `dist/explorer` can be served by an ordinary static host.

## Interpretation

This is an exploratory synthetic study of model behavior, not a validated
prediction about humans or a causal estimate for a real organization. Agents
choose from a bounded action menu and consult limited sources. Offering a more
specific document sometimes reduced error, sometimes increased it and sometimes
made little difference. The viewer exposes those contrasts instead of selecting
only favorable examples.

Confirmed cumulative token-priced usage, including the earlier pilot, was
US$9.9792478750. Seventeen requests without receipts retain their full
US$0.0197201250 reservation: maximum cumulative exposure was US$9.9989680000 under
the original US$10 cap. These are recorded accounting figures, not an exact final
invoice. Browsing the recording does not change them.


## Verification evidence

The [validation record](explorer-validation.json) covers the published build and
its anonymous HTTPS checks. Screenshots show the [desktop repost map](explorer-network.png)
and [mobile explorer](explorer-mobile.png). Browser QA also exercised the mobile
account picker and decision sheet.
