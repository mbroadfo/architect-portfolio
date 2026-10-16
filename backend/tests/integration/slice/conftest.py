"""Integration fixtures: the real MongoDB single-node replica set from local/compose.yaml.

``python scripts/verify.py --unit walking-slice`` starts this checkout's isolated verification
stack and runs these tests in the ``slice-it`` Linux container on its network
(``SLICE_IT_MONGO_URI=mongodb://mongo:27017/?directConnection=true``). To run them by hand,
start a replica set and point ``SLICE_IT_MONGO_URI`` at it.

Each test gets its own throwaway database, dropped afterwards. Nothing here touches the
live Atlas cluster or any cloud service (team practice).
"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from portfolio_api.slice.mongo import ensure_indexes
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

MONGO_URI = os.environ.get("SLICE_IT_MONGO_URI", "mongodb://127.0.0.1:27017/?directConnection=true")
PRIMARY_WAIT_SECONDS = 60

Document = dict[str, Any]


@pytest.fixture(scope="session")
def mongo_client() -> Iterator[MongoClient[Document]]:
    client: MongoClient[Document] = MongoClient(
        MONGO_URI, tz_aware=True, serverSelectionTimeoutMS=2000
    )
    deadline = time.monotonic() + PRIMARY_WAIT_SECONDS
    while True:
        try:
            if client.admin.command("hello").get("isWritablePrimary"):
                break
        except PyMongoError:
            pass
        if time.monotonic() > deadline:
            client.close()
            pytest.fail(
                f"no writable MongoDB primary at {MONGO_URI}; start it with "
                "`docker compose -f local/compose.yaml up -d mongo mongo-init`"
            )
        time.sleep(1)
    yield client
    client.close()


@pytest.fixture
def database(mongo_client: MongoClient[Document]) -> Iterator[Database[Document]]:
    name = f"slice_it_{uuid.uuid4().hex[:12]}"
    db = mongo_client[name]
    ensure_indexes(db)
    yield db
    mongo_client.drop_database(name)
