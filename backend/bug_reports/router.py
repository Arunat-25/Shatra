"""Маршруты сообщений о багах."""

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_admin_user, get_optional_user
from backend.bug_reports import service
from backend.bug_reports.schemas import BugReportCreated, BugReportListResponse
from backend.db.models import User
from backend.db.session import get_db

public_router = APIRouter(tags=["bug-reports"])
admin_router = APIRouter(tags=["admin-bug-reports"])


@public_router.post("", response_model=BugReportCreated, status_code=201)
async def submit_bug_report(
    request: Request,
    description: str = Form(...),
    screenshot: UploadFile | None = File(None),
    page_url: str | None = Form(None),
    client_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    user_agent = request.headers.get("user-agent")
    return await service.create_bug_report(
        db,
        description=description,
        screenshot=screenshot,
        user=user,
        client_id=client_id,
        page_url=page_url,
        user_agent=user_agent,
    )


@admin_router.get("", response_model=BugReportListResponse)
async def list_bug_reports(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    return await service.list_bug_reports(db, limit=limit, offset=offset)


@admin_router.get("/{report_id}/screenshot")
async def get_bug_report_screenshot(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    data, mime = await service.get_screenshot_payload(db, report_id)
    return Response(content=data, media_type=mime)
