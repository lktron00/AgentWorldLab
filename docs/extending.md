# Extend an experiment

## Configure a scenario

Copy `scenarios/diffusion.json`, change its initial signal, verification label,
episode length, feed size or friction multiplier, and pass the JSON object to
`client.reset(scenario=parameters, seed=7, population=20)`. Unknown fields and
invalid values are rejected before replacing a running world. The full
configuration is saved in every run and checkpoint.

```sh
.venv-api/bin/python examples/compare.py --seeds 7 8 9 \
  --scenario scenarios/diffusion.json --output data/comparison.json
```

The server must be running. Each seed produces a checkpoint and two branches
from that exact state. The JSON result includes run IDs and metric trajectories
for both policies, plus a descriptive paired mean difference. Each finished
pair is saved immediately. This is an experiment on programmed rules, not an
estimate of how people respond to a real intervention.

Restore with `client.reset(checkpoint_id=id)`. To branch, also pass
`policy="open"` or `policy="friction"`. Other scenario parameters are fixed by
the checkpoint. A ZIP export contains observations and provenance for analysis;
it is not a restorable checkpoint or a complete database backup.

## Connect an AI agent

`examples/external_agent.py` shows the real transport. Replace its action
selection with a call to your own agent framework or model:

```python
observation = result.observation.snapshot
# Your function can invoke a local model, hosted model or existing agent.
proposal = await your_agent.decide(observation)
action = LabAction.model_validate(proposal)
result = await client.step(action)
```

Valid proposals are `{"kind":"wait"}`, `{"kind":"post","content":"..."}`
or `{"kind":"repost","post_id":1}`. Agent 0 is external; background agents
still run through AgentSociety 2. Model calls, credentials and cost tracking
belong to your agent process. The lab never guesses a fallback action when
your external agent fails. Record model/version, prompts and responses with
your experiment if you need an audit trail. LLM continuation is not guaranteed
deterministic, even when the simulated world starts from the same checkpoint.

The current external observation exposes the whole world. Do not present it
as an agent-scoped information test or claim a trained policy generalizes from
this environment. Reward is intentionally unset. Other clients create other
worlds; they do not join the same society automatically.

## Replace the background policy

`worldlab/scripted_agent.py:LabAgent.step` is the AgentSociety extension point.
Its service-proxy context contains the frozen social snapshot, seed, step,
rule and scenario. Set `self.intent` to a supported action, advance the agent
clock once, and preserve workspace serialization. The society applies intents
after all decisions, in agent ID order. Do not write directly to OASIS from a
decision function or start a second clock.

The baseline decision lives in `worldlab/common.py:choose_action`. Add tests
for a new policy's action contract and failure behavior, and include all new
policy modules in `Controller.adapter_hashes()` so an old checkpoint cannot
silently resume with changed behavior. Save additional agent memory in the
workspace. Deliberately changing policy code invalidates prior checkpoints;
start a new experiment rather than editing checkpoint manifests.

## Add another kind of world

The current adapter is social diffusion. A market or resource-allocation world
needs explicit state, legal actions, observation rules and outcome metrics;
changing prompts alone does not supply those mechanics. Keep the OpenEnv
contract and AgentSociety scheduler, then implement and test the environment
module's state transition and checkpoint consistency before adding a UI.
