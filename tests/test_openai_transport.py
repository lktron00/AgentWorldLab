"""SDK wire-contract fixture only. This does NOT claim a real model inference."""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from openai import AsyncOpenAI

from worldlab.ai_policy import OpenAIPolicy
from worldlab.costs import CostLedger


def test_real_sdk_token_count_function_call_and_usage_transport(tmp_path):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, body))
            if self.path.endswith("/input_tokens"):
                result = {"object": "response.input_tokens", "input_tokens": 450}
            else:
                result = {"id": "resp_protocol_fixture", "object": "response", "created_at": 1,
                          "status": "completed", "model": "gpt-6-luna", "service_tier": "default",
                          "parallel_tool_calls": False,
                          "output": [{"id": "fc_fixture", "type": "function_call", "status": "completed",
                                      "call_id": "call_fixture", "name": "choose_action",
                                      "arguments": json.dumps({"kind": "wait", "content": "", "post_id": None,
                                                               "reason": "Need supporting evidence"})}],
                          "usage": {"input_tokens": 450, "output_tokens": 80, "total_tokens": 530,
                                    "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                                    "output_tokens_details": {"reasoning_tokens": 10}}}
            encoded = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    ledger = CostLedger(tmp_path / "costs.jsonl", "0.10")

    async def exercise():
        async with AsyncOpenAI(api_key="local-test-fixture-only", base_url=f"http://127.0.0.1:{server.server_port}/v1",
                               max_retries=0, timeout=5) as sdk:
            action, receipt = await OpenAIPolicy(sdk, ledger).decide({"view": "agent-v1", "feed": []})
            assert action.kind == "wait"
            assert receipt["estimated_cost_usd"] == "0.0000850000"

    try:
        asyncio.run(exercise())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert [path for path, body in requests] == ["/v1/responses/input_tokens", "/v1/responses"]
    assert requests[0][1]["input"] == requests[1][1]["input"]
    assert requests[1][1]["store"] is False
