"""Маршруты сообщений о багах."""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_admin_user, get_optional_user
from backend.bug_reports import service
from backend.bug_reports.schemas import BugReportCreated, BugReportListResponse
from backend.db.models import User
from backend.db.session import get_db
from backend.message_codes import BUG_REPORT_RATE_LIMIT
from backend.rate_limit import check_sliding_window_rate_limit

public_router = APIRouter(tags=["bug-reports"])
admin_router = APIRouter(tags=["admin-bug-reports"])

BUG_REPORT_RATE_LIMIT_COUNT = 5
BUG_REPORT_RATE_WINDOW_SECONDS = 600


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
    rate_key_id = (client_id or "").strip()
    if not rate_key_id:
        rate_key_id = request.client.host if request.client else "unknown"
    allowed = await check_sliding_window_rate_limit(
        f"bug_report_rate:{rate_key_id}",
        limit=BUG_REPORT_RATE_LIMIT_COUNT,
        window_seconds=BUG_REPORT_RATE_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(status_code=429, detail=BUG_REPORT_RATE_LIMIT)

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
