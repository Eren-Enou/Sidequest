"""Library input validation and stable response fields; lifecycle writes are explicit."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Energy = Literal["low", "medium", "high"]
SocialMode = Literal["solo", "social", "both"]
Experience = Literal["progression", "chill", "challenge", "novelty"]
GoalStatus = Literal["active", "completed", "archived"]
GoalReadiness = Literal["current", "later"]
Title = Annotated[str, Field(min_length=1, max_length=200)]
Interest = Annotated[int, Field(strict=True, ge=1, le=5)]
Friction = Annotated[int, Field(strict=True, ge=0, le=5)]
Priority = Annotated[int, Field(strict=True, ge=1, le=3)]
SQLITE_INTEGER_MAX = 2**63 - 1
PositiveInt = Annotated[int, Field(strict=True, gt=0, le=SQLITE_INTEGER_MAX)]
Tags = Annotated[list[Experience], Field(min_length=1, max_length=4)]


class LibraryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    @field_validator("title", mode="before", check_fields=False)
    @classmethod
    def trim_title(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("experience_tags", check_fields=False)
    @classmethod
    def canonical_tags(cls, value):
        return sorted(set(value)) if value is not None else value


class GameCreate(LibraryModel):
    title: Title
    notes: str | None = None
    current_interest: Interest = 3
    friction: Friction = 0
    energy_required: Energy
    social_mode: SocialMode
    experience_tags: Tags


class PatchModel(LibraryModel):
    @model_validator(mode="after")
    def reject_required_nulls(self):
        for name in self.model_fields_set - {"notes"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null; omit it to leave it unchanged")
        return self


class GamePatch(PatchModel):
    title: Title | None = None
    notes: str | None = None
    current_interest: Interest | None = None
    friction: Friction | None = None
    energy_required: Energy | None = None
    social_mode: SocialMode | None = None
    experience_tags: Tags | None = None


class GameRead(GameCreate):
    id: int
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class GoalCreate(LibraryModel):
    game_id: PositiveInt
    title: Title
    notes: str | None = None
    estimated_minutes: PositiveInt
    priority: Priority = 2
    readiness: GoalReadiness = "current"


class GoalPatch(PatchModel):
    title: Title | None = None
    notes: str | None = None
    estimated_minutes: PositiveInt | None = None
    priority: Priority | None = None
    readiness: GoalReadiness | None = None


class GoalRead(GoalCreate):
    id: int
    status: GoalStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
