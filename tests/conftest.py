"""
Pytest configuration — routes all tests to the ``quant_test`` database.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")
os.environ["MONGO_DB_NAME"] = "quant_test"


def _mongo_uri_configured() -> bool:
    """Return True when a MongoDB URI is available in the environment."""
    return bool(os.getenv("MONGO_URI") or os.getenv("MONGODB_URI"))


def _reload_mongo() -> None:
    """Reset and reconnect the MongoDB singleton for tests."""
    import quant.storage.mongo_client as mc

    mc._client = None  # noqa: SLF001
    mc._db = None  # noqa: SLF001
    if _mongo_uri_configured():
        mc.db = mc.get_database()
    else:
        mc.db = None


_reload_mongo()


@pytest.fixture(scope="session")
def mongo_db():
    """
    Provide the test database handle.

    Yields:
        Database: ``quant_test`` MongoDB database.
    """
    from quant.storage.mongo_client import db

    if db is None:
        pytest.skip("MONGO_URI not configured")
    yield db


@pytest.fixture
def requires_mongo(mongo_db):
    """Skip test when MongoDB is unavailable."""
    return mongo_db
