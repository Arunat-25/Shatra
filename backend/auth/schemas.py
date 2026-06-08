"""Pydantic-схемы аутентификации."""

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.auth.constants import DISTRICTS, USERNAME_PATTERN


def _validate_username(v: str) -> str:
    if not USERNAME_PATTERN.fullmatch(v):
        raise ValueError("Имя пользователя: 3–32 символа, буквы (рус/лат), цифры и _")
    return v


def _validate_password(v: str) -> str:
    if not re.search(r"[A-Za-zа-яА-ЯёЁ]", v) or not re.search(r"\d", v):
        raise ValueError("Пароль должен содержать букву и цифру")
    return v


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    district: str | None = None

    @field_validator("username")
    @classmethod
    def valid_username(cls, v: str) -> str:
        return _validate_username(v)

    @field_validator("password")
    @classmethod
    def valid_password(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("district")
    @classmethod
    def valid_district(cls, v: str | None) -> str | None:
        if v is not None and v not in DISTRICTS:
            raise ValueError("Выберите район из списка")
        return v


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def valid_password(cls, v: str) -> str:
        return _validate_password(v)


class ProfileUpdateRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=32)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    district: str | None = None

    @field_validator("username")
    @classmethod
    def valid_username(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_username(v)

    @field_validator("district")
    @classmethod
    def valid_district(cls, v: str | None) -> str | None:
        if v is not None and v not in DISTRICTS:
            raise ValueError("Выберите район из списка")
        return v


class UserPublic(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str | None
    last_name: str | None
    district: str | None
    is_admin: bool = False
    rating: int = 1200
    rated_games_count: int = 0

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserPublic


class MessageResponse(BaseModel):
    message: str


class DistrictsResponse(BaseModel):
    districts: list[str]


class FinishedGameSummary(BaseModel):
    id: uuid.UUID
    room_id: str
    room_type: str
    finished_at: datetime
    started_at: datetime | None
    my_color: Literal["белый", "черный"]
    result: Literal["win", "loss", "draw"]
    reason: str | None
    opponent_display: str
    moves_count: int
    time_control: int | None
    increment: int | None
    is_rated: bool = False
    rating_delta: int | None = None


class UserGamesListResponse(BaseModel):
    items: list[FinishedGameSummary]
    total: int
    limit: int
    offset: int
