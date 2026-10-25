"""Dedicated local OpenEnv server with scoped agent and operator capabilities."""
import os
import secrets
import threading
import time

from fastapi import HTTPException

from openenv.core.env_server import create_app

from .environment import LabEnvironment
from .models import LabAction, LabObservation, LabState
from .security import LocalAccessMiddleware
from .server import checkpoint, export, frames, list_runs, run_path
from .common import read_json


RESET_TICKETS = {}
TICKET_LOCK = threading.Lock()


class AgentEnvironment(LabEnvironment):
    restricted = True

    def reset(self, seed=None, episode_id=None, **kwargs):
        if seed is not None or set(kwargs) != {"ticket"} or not isinstance(kwargs["ticket"], str):
            raise ValueError("Agent reset requires only an operator-issued one-use ticket")
        with TICKET_LOCK:
            ticket = RESET_TICKETS.pop(kwargs["ticket"], None)
        if ticket is None or time.monotonic() - ticket["created"] > 300:
            raise ValueError("Unknown, expired or consumed reset ticket")
        return super().reset(**ticket["parameters"])

    @property
    def state(self):
        state = super().state
        if state.error:
            state.error = "World failed; reset or restore a checkpoint"
        return state


class CapabilityMiddleware:
    """Agent bearer grants /ws only. Operator APIs require a separate bearer."""
    def __init__(self, app, operator_token, agent_token):
        if (not operator_token or not agent_token or operator_token == agent_token):
            raise ValueError("Distinct operator and agent tokens are required")
        self.app, self.operator_token, self.agent_token = app, operator_token, agent_token

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            return await self.app(scope, receive, send)
        path = scope["path"]
        if path == "/health" and scope["type"] == "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        bearer = headers.get(b"authorization", b"")
        operator = secrets.compare_digest(bearer, ("Bearer " + self.operator_token).encode())
        agent = secrets.compare_digest(bearer, ("Bearer " + self.agent_token).encode())
        allowed = operator or (agent and path == "/ws" and scope["type"] == "websocket")
        if allowed:
            return await self.app(scope, receive, send)
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
        else:
            await send({"type": "http.response.start", "status": 403,
                        "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": b'{"detail":"Capability required"}'})


def build_app(operator_token, agent_token):
    app = create_app(AgentEnvironment, LabAction, LabObservation,
                     env_name="agent_world_lab_scoped", max_concurrent_envs=1, state_cls=LabState)
    app.add_middleware(CapabilityMiddleware, operator_token=operator_token, agent_token=agent_token)
    app.add_middleware(LocalAccessMiddleware)
    app.add_api_route("/lab/runs", list_runs, methods=["GET"])
    app.add_api_route("/lab/runs/{run_id}/frames", frames, methods=["GET"])
    app.add_api_route("/lab/runs/{run_id}/checkpoint", checkpoint, methods=["POST"])
    app.add_api_route("/lab/runs/{run_id}/export", export, methods=["GET"])

    @app.post("/lab/reset-tickets")
    def reset_ticket(parameters: dict):
        if parameters.keys() - {"seed", "population", "policy", "checkpoint_id", "scenario"}:
            raise HTTPException(422, "Unknown reset parameter")
        with TICKET_LOCK:
            for key in list(RESET_TICKETS):
                if time.monotonic() - RESET_TICKETS[key]["created"] > 300:
                    del RESET_TICKETS[key]
            if len(RESET_TICKETS) >= 32:
                raise HTTPException(409, "Too many unused reset tickets")
            token = secrets.token_urlsafe(32)
            RESET_TICKETS[token] = {"created": time.monotonic(), "parameters": parameters}
        return {"ticket": token}

    @app.get("/lab/runs/{run_id}/snapshot")
    def snapshot(run_id: str):
        # latest.json is atomically replaced at a committed boundary.
        return read_json(run_path(run_id) / "latest.json")
    return app


def main():
    import uvicorn
    app = build_app(os.environ.get("WORLDLAB_OPERATOR_TOKEN"), os.environ.get("WORLDLAB_AGENT_TOKEN"))
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8766")), workers=1)


if __name__ == "__main__":
    main()
