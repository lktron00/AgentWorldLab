"""Typed OpenEnv client for external agent systems."""
from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient

from .models import LabAction, LabObservation, LabState


class LabClient(EnvClient[LabAction, LabObservation, LabState]):
    def _step_payload(self, action):
        return action.model_dump()

    def _parse_result(self, payload):
        observation = LabObservation.model_validate(payload.get("observation", {}))
        return StepResult(observation=observation, reward=payload.get("reward"), done=payload.get("done", False))

    def _parse_state(self, payload):
        return LabState.model_validate(payload)
