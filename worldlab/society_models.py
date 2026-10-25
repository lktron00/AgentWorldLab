"""Separate OpenEnv contract for an operator coordinating all active accounts."""
from typing import Literal
from openenv.core.env_server.types import Action
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .client import LabClient


class AccountAction(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    kind: Literal['wait', 'post', 'repost', 'inspect_status']
    content: str = Field(default='', max_length=1000)
    post_id: int | None = Field(default=None, ge=1)

    @model_validator(mode='after')
    def payload(self):
        if self.kind == 'post' and not self.content.strip():
            raise ValueError('Post content cannot be empty')
        if self.kind != 'post' and self.content:
            raise ValueError('Only post accepts content')
        if (self.kind == 'repost') != (self.post_id is not None):
            raise ValueError('Only repost requires post_id')
        return self


class AccountProposal(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    actor: int = Field(ge=1, le=100)
    action: AccountAction


class SocietyAction(Action):
    expected_step: int = Field(ge=0, strict=True)
    actions: list[AccountProposal] = Field(min_length=4, max_length=100)


class SocietyClient(LabClient):
    """Uses the real OpenEnv simulation WebSocket with SocietyAction payloads."""
