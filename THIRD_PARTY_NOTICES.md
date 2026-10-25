# Third-party notices

This project integrates independently installed upstream libraries. Their source is not copied into the tracked project, except for license texts. The bootstrap script checks out exact revisions under the ignored `vendor/` directory; each upstream retains its own copyright and license notices.

- **AgentSociety 2** — Tsinghua FIB Lab and contributors. Apache License 2.0. Only the active `packages/agentsociety2` SDK is installed. The legacy AgentSociety commercial/community packages are not part of this integration. [Source](https://github.com/tsinghua-fib-lab/AgentSociety).
- **OASIS** — CAMEL-AI.org and contributors. Apache License 2.0. [Source](https://github.com/camel-ai/oasis).
- **OpenEnv** — Hugging Face, Inc., Meta Platforms, Inc. and contributors, as attributed in upstream notices. BSD 3-Clause. [Source](https://github.com/openenv/OpenEnv). The root license names Hugging Face, Inc.; its original text is retained in `licenses/OpenEnv.txt`.
- Transitive Python dependencies retain their respective licenses and are listed in `requirements/`.

New adapter, interface, dashboard and test code in this repository is provided under the Apache License 2.0 in `LICENSE`.
