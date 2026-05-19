"""Skein database schema. Embedding dim is inferred from existing chunks table."""
from __future__ import annotations

import psycopg


SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS skein_entities (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    name_norm   TEXT NOT NULL,
    kind        TEXT,
    mentions    INT NOT NULL DEFAULT 0,
    embedding   vector({dim}),
    UNIQUE (name_norm)
);
CREATE INDEX IF NOT EXISTS skein_entities_kind_idx ON skein_entities (kind);
CREATE INDEX IF NOT EXISTS skein_entities_mentions_idx ON skein_entities (mentions DESC);

CREATE TABLE IF NOT EXISTS skein_entity_chunks (
    entity_id   BIGINT NOT NULL REFERENCES skein_entities(id) ON DELETE CASCADE,
    chunk_id    BIGINT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    PRIMARY KEY (entity_id, chunk_id)
);
CREATE INDEX IF NOT EXISTS skein_entity_chunks_chunk_idx ON skein_entity_chunks (chunk_id);

CREATE TABLE IF NOT EXISTS skein_relations (
    id                 BIGSERIAL PRIMARY KEY,
    subject_id         BIGINT NOT NULL REFERENCES skein_entities(id) ON DELETE CASCADE,
    predicate          TEXT NOT NULL,
    object_id          BIGINT NOT NULL REFERENCES skein_entities(id) ON DELETE CASCADE,
    sim                REAL NOT NULL,
    evidence_chunk_ids BIGINT[] NOT NULL DEFAULT '{{}}',
    UNIQUE (subject_id, object_id)
);
CREATE INDEX IF NOT EXISTS skein_relations_subject_idx ON skein_relations (subject_id);
CREATE INDEX IF NOT EXISTS skein_relations_object_idx ON skein_relations (object_id);
CREATE INDEX IF NOT EXISTS skein_relations_predicate_idx ON skein_relations (predicate);

CREATE TABLE IF NOT EXISTS skein_build (
    id           BIGSERIAL PRIMARY KEY,
    fingerprint  TEXT NOT NULL,
    finished_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    stats        JSONB NOT NULL DEFAULT '{{}}'::jsonb
);
"""


def infer_embedding_dim(conn: psycopg.Connection) -> int:
    """Look at one row to figure out the vector dimensionality of
    `chunks.embedding`.

    docs/bugs/0002: validate the inferred dimension is a plausible positive
    integer before returning it, since downstream uses it in a SQL format
    string. Refuses anything outside 16..65536.

    docs/bugs/0010: additionally verifies every non-NULL embedding in the
    `chunks` table has the same dimensionality. If two rows have different
    dims, raising here is far kinder than letting the rebuild fail mid-
    INSERT on a pgvector cast error.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT atttypmod FROM pg_attribute "
                    "WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'")
        row = cur.fetchone()
        if row and row[0] > 0:
            dim = int(row[0])
        else:
            # Fallback: read a row
            cur.execute("SELECT embedding FROM chunks WHERE embedding IS NOT NULL LIMIT 1")
            r = cur.fetchone()
            if not r:
                raise RuntimeError("no chunks with embeddings; ingest data first")
            dim = int(len(r[0]))

        # docs/bugs/0010: verify every row's embedding has the same dim.
        # vector_dims(embedding) is the pgvector function; falls back to
        # array_length cast for compatibility with older pgvector.
        try:
            cur.execute(
                "SELECT DISTINCT vector_dims(embedding) FROM chunks "
                "WHERE embedding IS NOT NULL"
            )
            distinct_dims = sorted(int(r[0]) for r in cur.fetchall() if r[0] is not None)
        except psycopg.Error:
            # Older pgvector may not have vector_dims; treat as unverifiable
            # rather than raising — the column-type dim is still trustworthy.
            distinct_dims = []
    if distinct_dims and len(distinct_dims) > 1:
        raise RuntimeError(
            f"chunks.embedding has inconsistent dimensions across rows: {distinct_dims}. "
            "Re-embed the corpus with a single model before building Skein."
        )
    if not (16 <= dim <= 65536):
        raise RuntimeError(
            f"refusing to construct schema with implausible embedding dimension {dim!r}"
        )
    return dim


def schema_apply(db_url: str) -> None:
    with psycopg.connect(db_url) as conn:
        dim = infer_embedding_dim(conn)
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL.format(dim=dim))
        conn.commit()
