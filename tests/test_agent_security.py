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
        try:
            while True:
                message = await socket.receive_json()
                await socket.send_json({"accepted": message["type"]})
        except WebSocketDisconnect:
            pass

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


def test_mcp_tunnel_and_oversized_frames_are_rejected_before_environment(secured):
    with secured.websocket_connect("/ws", headers={"Authorization": "Bearer agent-secret"}) as ws:
        assert ws.receive_json()["view"] == "agent-v1"
        ws.send_json({"type": "mcp", "data": {"jsonrpc": "2.0", "id": 1, "method": "openenv/session/create", "params": {}}})
        assert ws.receive_json()["data"]["code"] == "unsupported_protocol"
        ws.send_json({"type": "step", "data": {"content": "x" * 17000}})
        assert ws.receive_json()["data"]["code"] == "unsupported_protocol"
        ws.send_json({"type": "state"})
        assert ws.receive_json() == {"accepted": "state"}


@pytest.mark.parametrize("operator,agent", [(None, None), ("same", "same"), ("operator", "")])
def test_scoped_app_refuses_missing_capabilities_before_startup(operator, agent):
    from worldlab.agent_server import build_app
    with pytest.raises(ValueError, match="before startup"):
        build_app(operator, agent)
