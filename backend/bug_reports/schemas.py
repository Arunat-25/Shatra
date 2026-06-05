"""Pydantic-схемы для сообщений о багах."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BugReportCreated(BaseModel):
    id: uuid.UUID
    created_at: datetime


class BugReportSummary(BaseModel):
    id: uuid.UUID
    description: str
    has_screenshot: bool
    username: str | None = None
    client_id: str | None = None
    page_url: str | None = None
    user_agent: str | None = None
    created_at: datetime


class BugReportListResponse(BaseModel):
    items: list[BugReportSummary]
    total: int = Field(ge=0)
