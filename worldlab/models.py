from typing import Literal

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field, model_validator


class LabAction(Action):
    kind: Literal["wait", "post", "repost"] = "wait"
    content: str = Field(default="", max_length=1000)
    post_id: int | None = Field(default=None, ge=1)
    verified: bool = False

    @model_validator(mode="after")
    def validate_payload(self):
        if self.kind == "post" and not self.content.strip():
            raise ValueError("Post content cannot be empty")
        if self.kind == "repost" and self.post_id is None:
            raise ValueError("A repost requires post_id")
        if self.kind != "post" and (self.content or self.verified):
            raise ValueError("Only posts accept content and a verification label")
        if self.kind != "repost" and self.post_id is not None:
            raise ValueError("Only repost accepts post_id")
        return self


class LabObservation(Observation):
    snapshot: dict = Field(default_factory=dict)


class LabState(State):
    run_id: str | None = None
    status: str = "uninitialized"
