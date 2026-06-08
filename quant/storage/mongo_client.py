"""
Singleton MongoDB client for Quant.

Loads connection settings from environment variables via python-dotenv.
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConfigurationError, ConnectionFailure, OperationFailure

load_dotenv()

_client: Optional[MongoClient] = None
_db: Optional[Database] = None


def get_client() -> MongoClient:
    """
    Return the singleton MongoClient, creating it on first access.

    Returns:
        MongoClient: Connected pymongo client.

    Raises:
        RuntimeError: If MONGO_URI is missing or connection fails.
    """
    global _client

    if _client is not None:
        return _client

    mongo_uri = (
        os.getenv("MONGO_URI")
        or os.getenv("MONGODB_URI")
        or os.getenv("CONNECTION_STRING")
    )
    if not mongo_uri:
        raise RuntimeError(
            "MONGO_URI (or MONGODB_URI) is not set. Copy .env.example to .env "
            "and set your MongoDB Atlas URI."
        )

    try:
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
        _client.admin.command("ping")
    except (ConnectionFailure, ConfigurationError, OperationFailure) as exc:
        raise RuntimeError(
            "Failed to connect to MongoDB. Check your MONGO_URI in .env "
            "(credentials, network access, and cluster hostname)."
        ) from exc

    refresh_db()
    return _client


def refresh_db() -> Optional[Database]:
    """
    Re-resolve the module-level ``db`` handle after a successful client connect.

    Returns:
        Optional[Database]: Connected database, or None if unavailable.
    """
    global _db, db

    try:
        db_name = os.getenv("MONGO_DB_NAME") or os.getenv("MONGODB_DB", "quant")
        _db = get_client()[db_name]
        db = _db
    except RuntimeError:
        _db = None
        db = None  # type: ignore[assignment]
    return db


def get_database() -> Database:
    """
    Return the configured Quant database (default name: ``quant``).

    Returns:
        Database: pymongo Database handle.
    """
    global _db

    if _db is not None:
        return _db

    db_name = os.getenv("MONGO_DB_NAME") or os.getenv("MONGODB_DB", "quant")
    _db = get_client()[db_name]
    return _db


# Module-level database handle used by pipelines and tests.
try:
    db: Database = get_database()
except RuntimeError:
    # Allow importing modules in environments without Mongo (e.g. static analysis).
    db = None  # type: ignore[assignment]
