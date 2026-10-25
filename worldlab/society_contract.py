"""Dependency-free validation of complete, frozen-observation society ticks."""
from .observations import agent_view, validate_agent_action


def validate_batch(snapshot, actions, expected_step):
    if type(expected_step) is not int or expected_step != snapshot['step']:
        raise ValueError('Stale or invalid expected_step; no account was committed')
    if snapshot['done']:
        raise ValueError('Episode finished; reset to start another')
    count = snapshot['scenario']['population']
    if not isinstance(actions, list) or len(actions) != count:
        raise ValueError('Exactly one action for every active account is required')
    result = {}
    for proposal in actions:
        if not isinstance(proposal, dict) or set(proposal) != {'actor', 'action'}:
            raise ValueError('Each proposal needs only actor and action')
        actor, action = proposal['actor'], proposal['action']
        if type(actor) is not int or not 1 <= actor <= count or str(actor) in result:
            raise ValueError('Missing, duplicate or invalid active account')
        if not isinstance(action, dict) or set(action) != {'kind', 'content', 'post_id'}:
            raise ValueError('Only kind, content and post_id are permitted')
        kind, content, post = action['kind'], action['content'], action['post_id']
        if kind not in {'wait', 'post', 'repost', 'inspect_status', 'inspect_record'} or not isinstance(content, str):
            raise ValueError('Invalid account action')
        if kind == 'post':
            if not 1 <= len(content.strip()) <= 1000 or post is not None:
                raise ValueError('Post requires 1–1000 characters and no post_id')
        elif content:
            raise ValueError('Only post accepts content')
        if kind == 'repost':
            if type(post) is not int:
                raise ValueError('Repost requires an integer post_id')
            validate_agent_action(action, agent_view(snapshot, actor))
        elif post is not None:
            raise ValueError('Only repost accepts post_id')
        result[str(actor)] = dict(action)
    return result
