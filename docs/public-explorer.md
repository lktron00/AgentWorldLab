# Public web application moved

**[Use the public explorer](https://agent-world-lab-explorer.lktron.chatgpt.site)** ·
**[Open-source web application](https://github.com/lktron00/AgentWorldLab-Web)** ·
**[Web build and map documentation](https://github.com/lktron00/AgentWorldLab-Web/blob/main/docs/public-explorer.md)**

The viewer source, frontend tests, static builder and screenshots now live in
AgentWorldLab-Web. The public URL and all shared case/turn/account links continue
to work. Its engine dependency is pinned by commit and public input hashes.

This repository retains the real simulation engines, CLI/API, original
[public study](../examples/recorded-study/README.md), pilot and campaign examples,
publication auditors and the self-contained sample `web/recorded-study.html`.
Run `python3 scripts/build-study-example.py --check` to verify these public records.

The web repository contains the roadmap for visual scenario creation and hosted
execution. The current public app is a read-only recording; the native operator
server remains private and bound to loopback.
