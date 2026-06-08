"""Fixtures for rating unit tests with PostgreSQL."""

import uuid

import psycopg2
import pytest

from backend.db.models import User
from backend.db.session import get_session_factory
from tests.test_env import SYNC_DB_URL


@pytest.fixture(autouse=True)
def clean_rating_tables():
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE finished_games, refresh_tokens, users CASCADE")
    conn.close()
    yield


async def create_test_user(username: str | None = None) -> uuid.UUID:
    name = username or f"rating_{uuid.uuid4().hex[:8]}"
    user_id = uuid.uuid4()
    factory = get_session_factory()
    async with factory() as session:
        session.add(
            User(
                id=user_id,
                username=name,
                username_normalized=name.lower(),
                password_hash="hash",
            )
        )
        await session.commit()
    return user_id
