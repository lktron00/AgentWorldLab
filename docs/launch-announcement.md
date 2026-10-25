# Launch copy — draft, publish after the 0.2 release

## English

We built Agent World Lab, an open-source laboratory for reproducible
multi-agent experiments.

Connect an external AI policy to a synthetic social world, give it a limited
view, then compare it with a baseline from the same saved checkpoint. Inspect
the decisions, world trajectories, token usage and estimated cost of each run.

Underneath, AgentSociety 2 schedules the agents, OASIS owns the social state and
OpenEnv provides the agent interface. The included baseline runs offline. An
optional OpenAI policy and a recorded real-run example are ready to explore.

This first experimental release focuses on social diffusion and reproducible
experiments. It does not claim to predict people. Contributions around agent
policies, scenarios and experiment protocols are welcome.

Repository: https://github.com/lktron00/AgentWorldLab

## Español

Creamos Agent World Lab: un laboratorio open source para experimentar con
sistemas multiagente de forma reproducible.

Conecta una política de IA a un mundo social sintético, dale observaciones
limitadas y compárala con un baseline desde el mismo checkpoint. Puedes revisar
las decisiones, cómo cambia el mundo, los tokens y el coste estimado de cada
experimento.

Integra AgentSociety 2, OASIS y OpenEnv. El baseline funciona sin llamadas a
modelos; incluimos una política opcional de OpenAI y un ejemplo grabado de una
ejecución real.

Es una primera versión experimental centrada en difusión social y protocolos
reproducibles. No pretende predecir el comportamiento de personas. Nos gustaría
recibir aportes en políticas de agentes, escenarios y diseño de experimentos.

Repositorio: https://github.com/lktron00/AgentWorldLab

## Demonstration sequence

1. Open `/experiments`, then the bundled recorded example. Explain that it is a
   synthetic recording, not a new live model call.
2. Run `./scripts/experiment --policy baseline --seeds 7 --steps 3`. Open the new
   saved report and show the complete-trajectory self-check and zero model cost.
3. Show the six-call real validation report and its receipts. Explain the
   distinction between original-signal sharing and new questions.
4. Show how an external policy sees only its feed and acts through OpenEnv.
5. Link the README, contribution guide and experimental limits. Invite a small
   reproducible contribution rather than unsupported claims of human realism.
