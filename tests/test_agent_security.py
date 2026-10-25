import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from worldlab.agent_server import CapabilityMiddleware


@pytest.fixture
def secured():
    app = FastAPI()
    app.add_middleware(CapabilityMiddleware, operator_token="operator-secret", agent_token="agent-secret")

    @app.get("/lab/runs")
    def runs():
        return {"private": "operator-only"}

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        await socket.send_json({"view": "agent-v1"})

    @app.websocket("/harness")
    async def harness(socket: WebSocket):
        await socket.accept()
    with TestClient(app) as client:
        yield client


def test_agent_capability_cannot_access_operator_data_or_other_protocols(secured):
    header = {"Authorization": "Bearer agent-secret"}
    assert secured.get("/lab/runs", headers=header).status_code == 403
    with pytest.raises(WebSocketDisconnect):
        with secured.websocket_connect("/harness", headers=header):
            pass
    with secured.websocket_connect("/ws", headers=header) as ws:
        assert ws.receive_json() == {"view": "agent-v1"}
    assert secured.get("/lab/runs", headers={"Authorization": "Bearer operator-secret"}).json()["private"] == "operator-only"


def test_missing_or_wrong_capability_denies_http_and_ws(secured):
    assert secured.get("/lab/runs").status_code == 403
    with pytest.raises(WebSocketDisconnect):
        with secured.websocket_connect("/ws", headers={"Authorization": "Bearer wrong"}):
            pass
