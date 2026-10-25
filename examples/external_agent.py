"""Run with .venv-api/bin/python examples/external_agent.py while server is on."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from worldlab.client import LabClient
from worldlab.models import LabAction


async def main():
    async with LabClient(base_url="http://127.0.0.1:8765", message_timeout_s=180) as client:
        result = await client.reset(seed=7)
        print("Created", result.observation.snapshot["run_id"])
        for index in range(5):
            # Replace this selection with your own agent's policy/model/tool loop.
            action = LabAction(kind="post", content="Synthetic correction: Orion remains operational.", verified=True) if index == 1 else LabAction()
            result = await client.step(action)
            print(result.observation.snapshot["metrics"])


if __name__ == "__main__":
    asyncio.run(main())
