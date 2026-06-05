"""Сервис сообщений о багах."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.bug_reports.schemas import BugReportCreated, BugReportListResponse, BugReportSummary
from backend.db.models import BugReport, User
from backend.message_codes import (
    BUG_REPORT_DESCRIPTION_TOO_LONG,
    BUG_REPORT_DESCRIPTION_TOO_SHORT,
    BUG_REPORT_INVALID_SCREENSHOT,
    BUG_REPORT_NO_SCREENSHOT,
    BUG_REPORT_NOT_FOUND,
    BUG_REPORT_SCREENSHOT_TOO_LARGE,
)

ALLOWED_SCREENSHOT_MIMES = frozenset({"image/png", "image/jpeg", "image/webp"})
MAX_SCREENSHOT_BYTES = 3 * 1024 * 1024
MIN_DESCRIPTION_LEN = 10
MAX_DESCRIPTION_LEN = 5000


def _validate_description(description: str) -> str:
    text = description.strip()
    if len(text) < MIN_DESCRIPTION_LEN:
        raise HTTPException(status_code=400, detail=BUG_REPORT_DESCRIPTION_TOO_SHORT)
    if len(text) > MAX_DESCRIPTION_LEN:
        raise HTTPException(status_code=400, detail=BUG_REPORT_DESCRIPTION_TOO_LONG)
    return text


async def _read_screenshot(screenshot: UploadFile | None) -> tuple[bytes | None, str | None]:
    if screenshot is None or not screenshot.filename:
        return None, None

    content_type = (screenshot.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_SCREENSHOT_MIMES:
        raise HTTPException(status_code=400, detail=BUG_REPORT_INVALID_SCREENSHOT)

    data = await screenshot.read()
    if not data:
        return None, None
    if len(data) > MAX_SCREENSHOT_BYTES:
        raise HTTPException(status_code=400, detail=BUG_REPORT_SCREENSHOT_TOO_LARGE)
    return data, content_type


async def create_bug_report(
    db: AsyncSession,
    *,
    description: str,
    screenshot: UploadFile | None,
    user: User | None,
    client_id: str | None,
    page_url: str | None,
    user_agent: str | None,
) -> BugReportCreated:
    text = _validate_description(description)
    screenshot_data, screenshot_mime = await _read_screenshot(screenshot)

    report = BugReport(
        description=text,
        screenshot=screenshot_data,
        screenshot_mime=screenshot_mime,
        user_id=user.id if user else None,
        client_id=(client_id or None),
        page_url=(page_url or None)[:512] if page_url else None,
        user_agent=(user_agent or None)[:512] if user_agent else None,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return BugReportCreated(id=report.id, created_at=report.created_at)


def _to_summary(report: BugReport) -> BugReportSummary:
    username = report.user.username if report.user else None
    return BugReportSummary(
        id=report.id,
        description=report.description,
        has_screenshot=report.screenshot is not None,
        username=username,
        client_id=report.client_id,
        page_url=report.page_url,
        user_agent=report.user_agent,
        created_at=report.created_at,
    )


async def list_bug_reports(
    db: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
) -> BugReportListResponse:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    total = await db.scalar(select(func.count()).select_from(BugReport)) or 0
    result = await db.execute(
        select(BugReport)
        .options(selectinload(BugReport.user))
        .order_by(BugReport.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [_to_summary(row) for row in result.scalars().all()]
    return BugReportListResponse(items=items, total=total)


async def get_bug_report(db: AsyncSession, report_id: uuid.UUID) -> BugReport:
    result = await db.execute(
        select(BugReport)
        .options(selectinload(BugReport.user))
        .where(BugReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail=BUG_REPORT_NOT_FOUND)
    return report


async def get_screenshot_payload(db: AsyncSession, report_id: uuid.UUID) -> tuple[bytes, str]:
    report = await get_bug_report(db, report_id)
    if not report.screenshot or not report.screenshot_mime:
        raise HTTPException(status_code=404, detail=BUG_REPORT_NO_SCREENSHOT)
    return report.screenshot, report.screenshot_mime
