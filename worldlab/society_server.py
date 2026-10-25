"""Private operator-only OpenEnv endpoint for submitted society decisions."""
import os
import secrets
from openenv.core.env_server import create_app
from .agent_server import AgentEnvironment, RESET_TICKETS, TICKET_LOCK
from .common import read_json
from .environment import LabEnvironment
from .models import LabObservation, LabState
from .security import LocalAccessMiddleware
from .server import checkpoint, run_path
from .society_models import SocietyAction
import time
from fastapi import HTTPException


class SocietyEnvironment(AgentEnvironment):
    restricted = False

    def step(self, action: SocietyAction, timeout_s=None, **kwargs):
        with self.lock:
            if self.worker is None or self.latest is None or self.latest['status'] == 'failed':
                raise RuntimeError('Reset a healthy submitted society first')
            self.latest = self._call('society_step', expected_step=action.expected_step,
                                     actions=[a.model_dump() for a in action.actions])
            return self._observation(self.latest)


class OperatorOnly:
    def __init__(self, app, token):
        if not token:
            raise ValueError('An operator capability is required')
        self.app, self.token = app, token

    async def __call__(self, scope, receive, send):
        if scope['type'] not in {'http', 'websocket'} or scope['path'] == '/health':
            return await self.app(scope, receive, send)
        given = dict(scope.get('headers', [])).get(b'authorization', b'')
        if secrets.compare_digest(given, ('Bearer ' + self.token).encode()):
            return await self.app(scope, receive, send)
        if scope['type'] == 'websocket':
            await send({'type': 'websocket.close', 'code': 1008})
        else:
            await send({'type': 'http.response.start', 'status': 403, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'Operator capability required'})


def build_app(token):
    app = create_app(SocietyEnvironment, SocietyAction, LabObservation,
                     env_name='agent_world_lab_society', max_concurrent_envs=1, state_cls=LabState)
    app.add_middleware(OperatorOnly, token=token)
    app.add_middleware(LocalAccessMiddleware)
    app.add_api_route('/lab/runs/{run_id}/checkpoint', checkpoint, methods=['POST'])

    @app.post('/lab/reset-tickets')
    def ticket(parameters: dict):
        if parameters.keys() - {'seed', 'population', 'policy', 'checkpoint_id', 'scenario'}:
            raise HTTPException(422, 'Unknown reset parameter')
        with TICKET_LOCK:
            for key in list(RESET_TICKETS):
                if time.monotonic() - RESET_TICKETS[key]['created'] > 300:
                    del RESET_TICKETS[key]
            if len(RESET_TICKETS) >= 32:
                raise HTTPException(409, 'Too many unused tickets')
            key = secrets.token_urlsafe(32)
            RESET_TICKETS[key] = {'created': time.monotonic(), 'parameters': parameters}
        return {'ticket': key}

    @app.get('/lab/runs/{run_id}/snapshot')
    def snapshot(run_id: str):
        return read_json(run_path(run_id) / 'latest.json')
    return app


def main():
    import uvicorn
    uvicorn.run(build_app(os.environ.get('WORLDLAB_OPERATOR_TOKEN')),
                host='127.0.0.1', port=int(os.environ.get('PORT', '8767')), workers=1)


if __name__ == '__main__':
    main()
