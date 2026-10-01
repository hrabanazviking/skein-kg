"""Serialize complete builds and protect the previous graph from bad coverage."""
from __future__ import annotations

from contextlib import contextmanager
import json
import math
import os
from pathlib import Path

import psycopg

DEFAULTS = json.loads(Path(__file__).with_name("build.defaults.json").read_text())


class Vocabulary(list):
    def __init__(self, values, total: int, failed: int):
        super().__init__(values)
        self.total_documents, self.failed_documents = total, failed


def coverage(vocabulary: list) -> dict:
    total = getattr(vocabulary, "total_documents", 0)
    failed = getattr(vocabulary, "failed_documents", 0)
    maximum = float(os.getenv("SKEIN_MAX_FAILED_DOCUMENTS_PERCENT", str(DEFAULTS["max_failed_documents_percent"])))
    if not math.isfinite(maximum) or not 0 <= maximum <= 100:
        raise ValueError("SKEIN_MAX_FAILED_DOCUMENTS_PERCENT must be between 0 and 100")
    percentage = 100. * failed / total if total else 0.
    if percentage > maximum:
        raise RuntimeError(f"Vocabulary discovery failed for {failed}/{total} documents; previous graph preserved")
    return {"total_documents": total, "failed_documents": failed, "failed_percent": round(percentage, 2)}


@contextmanager
def build_lock(db_url: str):
    timeout = int(os.getenv("SKEIN_DB_CONNECT_TIMEOUT", "5"))
    with psycopg.connect(db_url, autocommit=True, connect_timeout=timeout) as conn:
        namespace = DEFAULTS["lock_namespace"]
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(hashtextextended(%s,0))", (namespace,))
            if not cur.fetchone()[0]:
                raise RuntimeError("Another Skein build owns this database; retry after it finishes")
        try:
            yield conn
        finally:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(hashtextextended(%s,0))", (namespace,))


def ensure_lock(conn: psycopg.Connection) -> None:
    """Do not publish after a lost locking session."""
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
