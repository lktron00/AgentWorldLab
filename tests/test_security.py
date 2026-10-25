import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from worldlab.security import LocalAccessMiddleware


@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(LocalAccessMiddleware)

    @app.get("/")
    def index():
        return {"ok": True}

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        await socket.send_json({"ok": True})

    with TestClient(app, base_url="http://localhost:8765") as test:
        yield test


@pytest.mark.parametrize("headers", [
    {"Origin": "https://untrusted.example"}, {"Origin": "null"},
    {"Origin": "http://localhost:9000"}, {"Host": "localhost.attacker.example"},
    {"Host": "127.0.0.1@attacker.example"}, {"Sec-Fetch-Site": "cross-site"},
])
def test_browser_cannot_drive_local_service_from_another_origin(client, headers):
    assert client.get("/", headers=headers).status_code == 403
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("ws://localhost:8765/ws", headers=headers):
            pass


def test_native_clients_and_same_origin_browser_remain_usable(client):
    assert client.get("/").json() == {"ok": True}
    assert client.get("/", headers={"Origin": "http://localhost:8765"}).status_code == 200
    with client.websocket_connect("ws://localhost:8765/ws", headers={"Origin": "http://localhost:8765"}) as ws:
        assert ws.receive_json() == {"ok": True}
