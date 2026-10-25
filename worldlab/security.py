"""Local-only host and same-origin protection for HTTP and WebSocket sessions."""
from urllib.parse import urlsplit


class LocalAccessMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            return await self.app(scope, receive, send)
        headers = {key.lower(): value.decode("latin-1") for key, value in scope.get("headers", [])}
        host = headers.get(b"host", "")
        origin = headers.get(b"origin")
        allowed = False
        try:
            parsed_host = urlsplit("http://" + host)
            allowed = (parsed_host.hostname in {"127.0.0.1", "localhost", "::1"}
                       and parsed_host.netloc == host and not parsed_host.path
                       and not parsed_host.username and not parsed_host.password)
            if origin is not None:
                parsed_origin = urlsplit(origin)
                allowed = (allowed and parsed_origin.scheme in {"http", "https"}
                           and parsed_origin.netloc == host and not parsed_origin.path
                           and not parsed_origin.query and not parsed_origin.fragment)
            if headers.get(b"sec-fetch-site") == "cross-site":
                allowed = False
        except ValueError:
            pass
        if not allowed:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                body = b'{"detail":"Use the local address and the same browser origin"}'
                await send({"type": "http.response.start", "status": 403,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": body})
            return
        return await self.app(scope, receive, send)
