# DOMAIN_MAP.md — Skein
## *Cartography of Realms*

> A boundary is a kindness to the next reader. Crossing one is shouting in a
> library.

---

## The Realms

### 1. The Algorithm — `skein/core.py`

**Responsibility:** The four-step pipeline. Vocabulary discovery, mention
finding, entity-embedding aggregation, edge construction, predicate
snapping, persistence.

**Knows about:** numpy, psycopg, httpx, the schema declared in `skein/schema.py`.

**Forbidden from:**
- Doing I/O outside well-named, narrowly-scoped helpers.
- Holding open DB connections beyond a single function call.
- Embedding LLM-prompt strings outside the named module-level constants
  (`SYSTEM_VOCAB`, `DEFAULT_PREDICATES`). Future maintainers must be able to
  audit "what is this library asking the LLM?" by reading just those constants.

### 2. The Schema — `skein/schema.py`

**Responsibility:** SQL that creates `skein_entities`, `skein_entity_chunks`,
`skein_relations`, `skein_build`. Embedding dimensionality inferred from the
existing `chunks` table.

**Knows about:** psycopg, pgvector, the parent project's schema (one column:
`chunks.embedding`).

**Forbidden from:**
- Altering the parent's `chunks` or `documents` tables.
- Hardcoding embedding dimensionality.
- Writing migrations. Skein's schema is idempotent; if a column needs to
  change shape, document it under PROJECT_LAWS and bump the version prefix
  in `skein_build.fingerprint`.

### 3. The Command Door — `skein/cli.py`

**Responsibility:** `typer`-based CLI surfaces: `build`, `stats`, `neighbors`.
Reads `.env` for defaults. Pretty-prints with `rich`.

**Knows about:** Typer, Rich, the public API in `skein.core` and `skein.schema`.

**Forbidden from:**
- Implementing any algorithm logic. The CLI is a thin shell over the library.
- Direct DB access except via library helpers.

### 4. The Public API — `skein/__init__.py`

**Responsibility:** Reexports the small, stable surface: `build_skein`,
`neighbors_of`, `schema_apply`. This is the contract — see `INTERFACE.md`.

**Forbidden from:**
- Reexporting internals. If a function is not in `__all__`, it is private.
  Renaming/removing private functions is not a breaking change.

### 5. The Deep Memory — Postgres (read & write, scoped)

**Responsibility:** The host project's `documents` + `chunks` tables (READ
ONLY from Skein's perspective), and Skein's own `skein_*` tables (read/write).

**Forbidden from (Skein's perspective):** mutating the parent project's tables.

---

## What This Library Owns

```
skein_entities       — one row per unique named thing
skein_entity_chunks  — many-to-many: entity ↔ source chunk
skein_relations      — one row per (subject, predicate, object) triple
skein_build          — append-only build log with fingerprint + stats
```

## What This Library Reads

```
documents (id, title)              — for vocabulary-discovery sampling
chunks    (id, document_id, text, embedding)  — the substrate
```

## What This Library Does Not Touch

- Any other tables in the host database.
- Files on disk except `.env` for config.
- Network destinations other than Ollama at the configured URL.

---

## Why these boundaries

Skein lives in a host database it does not own. Its first responsibility is
to be a *good guest*: read what it needs, write only into its own clearly-named
namespace, never modify the host's data. If a future contributor wishes Skein
could clean up `documents` or rewrite `chunks`, the answer is no — those
belong to the Ingest project, and Skein is downstream of them.

The algorithm/CLI/schema split mirrors the same wisdom at the package level.
The CLI exists so humans can run Skein; the algorithm exists so other code
can. Neither should reach into the other.
