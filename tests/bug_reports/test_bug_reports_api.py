"""API tests for bug reports."""

import psycopg2

from backend.message_codes import (
    BUG_REPORT_DESCRIPTION_TOO_SHORT,
    BUG_REPORT_INVALID_SCREENSHOT,
    BUG_REPORT_RATE_LIMIT,
    BUG_REPORT_SCREENSHOT_TOO_LARGE,
)
from backend.bug_reports.router import BUG_REPORT_RATE_LIMIT_COUNT
from tests.bug_reports.conftest import MINIMAL_PNG
from tests.test_env import SYNC_DB_URL


def _submit_report(client, **fields):
    headers = fields.pop("headers", None)
    data = {
        "description": fields.pop("description", "Something is broken on the board."),
        "page_url": fields.pop("page_url", "http://localhost/game/abc"),
        "client_id": fields.pop("client_id", "client-test-1"),
    }
    files = fields.pop("files", None)
    return client.post("/api/bug-reports", data=data, files=files, headers=headers)


class TestSubmitBugReport:
    def test_anonymous_submit_without_screenshot(self, client):
        r = _submit_report(client)
        assert r.status_code == 201, r.text
        body = r.json()
        assert "id" in body
        assert "created_at" in body

        conn = psycopg2.connect(SYNC_DB_URL)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM bug_reports")
            assert cur.fetchone()[0] == 1
        conn.close()

    def test_authenticated_submit_with_screenshot(self, client, regular_headers):
        r = _submit_report(
            client,
            files={"screenshot": ("shot.png", MINIMAL_PNG, "image/png")},
            headers=regular_headers,
        )
        assert r.status_code == 201, r.text

        conn = psycopg2.connect(SYNC_DB_URL)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT screenshot IS NOT NULL, screenshot_mime, user_id IS NOT NULL FROM bug_reports"
            )
            has_shot, mime, has_user = cur.fetchone()
        conn.close()
        assert has_shot is True
        assert mime == "image/png"
        assert has_user is True

    def test_description_too_short(self, client):
        r = _submit_report(client, description="short")
        assert r.status_code == 400
        assert r.json()["detail"] == BUG_REPORT_DESCRIPTION_TOO_SHORT

    def test_invalid_screenshot_mime(self, client):
        r = _submit_report(
            client,
            files={"screenshot": ("bad.txt", b"hello", "text/plain")},
        )
        assert r.status_code == 400
        assert r.json()["detail"] == BUG_REPORT_INVALID_SCREENSHOT

    def test_screenshot_too_large(self, client):
        big = b"\x89PNG" + (b"x" * (3 * 1024 * 1024))
        r = _submit_report(
            client,
            files={"screenshot": ("big.png", big, "image/png")},
        )
        assert r.status_code == 400
        assert r.json()["detail"] == BUG_REPORT_SCREENSHOT_TOO_LARGE

    def test_rejects_javascript_page_url(self, client):
        r = _submit_report(client, page_url="javascript:alert(1)")
        assert r.status_code == 201, r.text
        conn = psycopg2.connect(SYNC_DB_URL)
        with conn.cursor() as cur:
            cur.execute("SELECT page_url FROM bug_reports ORDER BY created_at DESC LIMIT 1")
            assert cur.fetchone()[0] is None
        conn.close()

    def test_rejects_data_url_page_url(self, client):
        r = _submit_report(client, page_url="data:text/html,<script>alert(1)</script>")
        assert r.status_code == 201
        conn = psycopg2.connect(SYNC_DB_URL)
        with conn.cursor() as cur:
            cur.execute("SELECT page_url FROM bug_reports ORDER BY created_at DESC LIMIT 1")
            assert cur.fetchone()[0] is None
        conn.close()

    def test_keeps_https_page_url(self, client):
        url = "https://example.com/game/abc"
        r = _submit_report(client, page_url=url, client_id="client-url-1")
        assert r.status_code == 201
        conn = psycopg2.connect(SYNC_DB_URL)
        with conn.cursor() as cur:
            cur.execute("SELECT page_url FROM bug_reports ORDER BY created_at DESC LIMIT 1")
            assert cur.fetchone()[0] == url
        conn.close()

    def test_rate_limit_by_client_id(self, client):
        cid = "rate-limit-client"
        for _ in range(BUG_REPORT_RATE_LIMIT_COUNT):
            assert _submit_report(client, client_id=cid).status_code == 201
        blocked = _submit_report(client, client_id=cid)
        assert blocked.status_code == 429
        assert blocked.json()["detail"] == BUG_REPORT_RATE_LIMIT

    def test_rate_limit_independent_per_client_id(self, client):
        for i in range(BUG_REPORT_RATE_LIMIT_COUNT):
            assert _submit_report(client, client_id=f"independent-{i}").status_code == 201


class TestAdminBugReports:
    def test_list_forbidden_for_regular_user(self, client, regular_headers):
        _submit_report(client)
        r = client.get("/api/admin/bug-reports", headers=regular_headers)
        assert r.status_code == 403

    def test_list_and_screenshot_for_admin(self, client, admin_headers):
        created = _submit_report(
            client,
            files={"screenshot": ("shot.png", MINIMAL_PNG, "image/png")},
        )
        assert created.status_code == 201
        report_id = created.json()["id"]

        listed = client.get("/api/admin/bug-reports", headers=admin_headers)
        assert listed.status_code == 200
        body = listed.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["id"] == report_id
        assert item["has_screenshot"] is True
        assert "Something is broken" in item["description"]

        shot = client.get(f"/api/admin/bug-reports/{report_id}/screenshot", headers=admin_headers)
        assert shot.status_code == 200
        assert shot.headers["content-type"].startswith("image/png")
        assert shot.content == MINIMAL_PNG
