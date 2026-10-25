"""Registered through AgentSociety's public registry in every Ray worker."""
from datetime import datetime
from pathlib import Path

from agentsociety2.agent.base import AgentBase

from worldlab.common import choose_action, read_json, write_json


class LabAgent(AgentBase):
    """A reproducible policy agent, persisted and scheduled by AgentSociety 2."""

    async def step(self, tick: int, t: datetime) -> str:
        context = self._service_proxy.env
        self.intent = choose_action(context["snapshot"], self.id, context["seed"], context["step"], context["policy"], context["scenario"])
        self._step_count += 1
        self._current_time = t
        return self.intent["kind"]

    async def to_workspace(self, workspace_path: Path) -> None:
        path = workspace_path / "AGENT.json"
        meta = read_json(path)
        meta.update(step_count=self._step_count, current_time=self._current_time.isoformat(), intent=self.intent)
        write_json(path, meta)

    async def ask(self, message: str, readonly: bool = True, *, t=None) -> str:
        return "Scripted policy agent; inspect its saved intent and observations."
