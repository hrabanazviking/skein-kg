# INTERFACE.md — Skein
## *Public Python API — Contract*

> This is the surface other code may rely on. Functions not listed here are
> private; renaming or removing them is not a breaking change.

---

## Importing

```python
from skein import build_skein, neighbors_of, schema_apply
```

Or under a namespace:

```python
import skein
skein.build_skein(...)
```

---

## `schema_apply(db_url: str) -> None`

Creates the `skein_entities`, `skein_entity_chunks`, `skein_relations`, and
`skein_build` tables if they do not already exist. The embedding dimension
is inferred from the host database's `chunks.embedding` column.

**Inputs:**
- `db_url` — a libpq connection string (e.g. `postgresql:///knowledge`).

**Outputs:** none.

**Side effects:** issues `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF
NOT EXISTS` statements against the database.

**Errors:** raises `psycopg.OperationalError` on connection failure,
`RuntimeError` if no chunks with embeddings exist (cannot infer dim).

**Idempotent:** yes.

---

## `build_skein(db_url, *, ollama_url, embed_model, chat_model, predicates=None, top_k=6, min_sim=0.55, window=120, log=print) -> dict`

Runs the four-step pipeline end to end. Wipes any prior Skein rows and
rebuilds the graph from scratch.

**Inputs:**
- `db_url` — Postgres libpq connection string.
- `ollama_url` — base URL of the Ollama server (e.g. `http://localhost:11434`).
- `embed_model` — name of the embedding model (e.g. `nomic-embed-text`).
- `chat_model` — name of the chat model for vocabulary discovery (e.g. `llama3.2:3b`).
- `predicates` — optional list of predicate strings; if `None`, uses
  `skein.core.DEFAULT_PREDICATES`.
- `top_k` — number of nearest-neighbor edges per entity (default 6).
- `min_sim` — minimum cosine similarity for an edge to be kept (default 0.55).
- `window` — span width in characters around each mention pair, used for
  predicate snapping (default 120).
- `log` — callable accepting a single string, called at each major stage
  (default `print`).

**Outputs:** a dict with build statistics:
```python
{"n_entities": int, "n_mentions": int, "n_edges": int, "build_seconds": float}
```

**Side effects:**
- One Ollama chat call per document.
- One Ollama embed call per ~32 predicate spans + one for the predicate vocab.
- Writes to `skein_entities`, `skein_entity_chunks`, `skein_relations`,
  `skein_build`.

**Errors:** raises on Postgres/Ollama unreachability. Individual per-document
vocabulary failures are logged and skipped, not raised.

**Idempotent:** yes — re-running produces an equivalent graph (modulo small
non-determinism in LLM output).

---

## `neighbors_of(db_url: str, name: str, *, limit: int = 20) -> dict`

Convenience lookup: given an entity name, return its neighbors and the
predicates connecting them.

**Inputs:**
- `db_url` — Postgres libpq connection string.
- `name` — entity name (case-insensitive; matched against `name_norm`).
- `limit` — max number of neighbors to return.

**Outputs:**
```python
{
    "found": True,
    "id": int,
    "name": str,
    "kind": str,
    "mentions": int,
    "edges": [
        {"predicate": str, "other": str, "kind": str,
         "sim": float, "evidence": [int, ...], "direction": "in" | "out"},
        ...
    ],
}
```
Or `{"found": False, "name": name}` if no match.

**Errors:** raises on Postgres unreachability.

---

## Stability promise

These three functions are **version-stable**: their signatures will not
change in any 0.x.y release. Adding new optional keyword arguments may
happen; removing or renaming existing arguments will not, except in a major
version bump.

Internal helpers (`discover_vocabulary`, `find_mentions`, `build_edges`,
etc.) are exposed in `skein.core` for advanced use, but their signatures
may change in any release.

## Language scope

The default `SYSTEM_VOCAB` prompt and `DEFAULT_PREDICATES` list are tuned
for **English-language narrative content**. The entity-matching regex IS
Unicode-aware — Norse names with þ, ð, æ, ö, ó match correctly. But for
non-English corpora (Arabic, Mandarin, Russian, etc.) the LLM-driven
vocabulary discovery and the predicate vocabulary will under-perform.

To use Skein on a non-English corpus:

1. Override the predicate vocabulary via the `SKEIN_PREDICATES` env var
   with verbs/predicates appropriate to the target language.
2. (Advanced) edit `SYSTEM_VOCAB` in `skein/core.py` to instruct the LLM
   in the target language.

See [`docs/bugs/0007-english-bias-disclosed.md`](docs/bugs/0007-english-bias-disclosed.md)
for the full history of this disclosure.
