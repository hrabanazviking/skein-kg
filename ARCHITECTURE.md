# ARCHITECTURE.md — Skein
## *The Bones of the World*

---

## Layout

```
skein-kg/
├── pyproject.toml      ← uv-managed manifest; declares `skein` console script
├── README.md           ← Outward-facing introduction
├── LICENSE             ← MIT
├── .env.example        ← Template (real .env is gitignored)
├── SYSTEM_VISION.md    ← The soul
├── DOMAIN_MAP.md       ← Realm boundaries
├── ARCHITECTURE.md     ← This document
├── PROJECT_LAWS.md     ← Immutable rules
├── INTERFACE.md        ← Public Python API contract
└── skein/
    ├── __init__.py     ← Reexports the public surface
    ├── core.py         ← The algorithm
    ├── schema.py       ← SQL for skein_* tables
    ├── cli.py          ← typer-based command line
    └── README_AI.md    ← Notes for AI maintainers working in this dir
```

---

## The Four-Step Pipeline

```
                                     ┌────────────────────────────────────┐
 ┌────────────────────────┐          │  for each document:                │
 │  1. Vocabulary         │ ◀── LLM ─│    sample 6 chunks                 │
 │     Discovery          │          │    ollama_chat(SYSTEM_VOCAB, ...)  │
 │     (per-doc LLM call) │          │    parse JSON → entities + aliases │
 └───────────┬────────────┘          └────────────────────────────────────┘
             │
             ▼ (vocab: name, kind, aliases)
 ┌────────────────────────┐         ┌─────────────────────────────────────┐
 │  2. Mention Finding    │ ◀── DB ─│  SELECT id, text FROM chunks        │
 │     (regex scan)       │         │  for each chunk:                    │
 └───────────┬────────────┘         │    test each entity's regex pattern │
             │                       └─────────────────────────────────────┘
             ▼ (entity → set of chunk_ids)
 ┌────────────────────────┐         ┌─────────────────────────────────────┐
 │  3. Entity Embeddings  │ ◀── DB ─│  SELECT embedding FROM chunks WHERE │
 │     (mean of vectors)  │         │    id = ANY(<mention chunks>)       │
 └───────────┬────────────┘         │  L2-normalize, average, re-normalize│
             │                       └─────────────────────────────────────┘
             ▼ (entity → unit vector)
 ┌────────────────────────┐         ┌─────────────────────────────────────┐
 │  4a. Edges             │         │  sim = E @ E.T                      │
 │      (top-K cosine)    │         │  for each row: keep top-K above min │
 └───────────┬────────────┘         └─────────────────────────────────────┘
             │
             ▼ (candidate edges: (a, b, sim))
 ┌────────────────────────┐         ┌──────────────────────────────────────┐
 │  4b. Predicate Snapping│ ◀── Embed│ for each edge:                       │
 │      (no autoregressive│         │   gather co-occurrence chunks        │
 │       LLM!)            │         │   extract text-between-mentions      │
 └───────────┬────────────┘         │   embed those spans                  │
             │                       │   cosine-snap to nearest in vocab    │
             ▼                       └──────────────────────────────────────┘
 ┌────────────────────────┐
 │  5. Persist            │
 │     skein_entities,    │
 │     skein_entity_chunks│
 │     skein_relations,   │
 │     skein_build        │
 └────────────────────────┘
```

---

## The LLM Budget

For a corpus of `D` documents and `C` chunks, Skein issues:

| Phase | Calls | Type |
|-------|-------|------|
| Vocabulary discovery | `D` | autoregressive chat (with `format=json`) |
| Predicate spans | one batch per edge, batched ~32 at a time | embedding (cheap, single-pass) |
| Predicate vocabulary | one batch at startup | embedding |

For 33 documents and ~20,000 chunks the build is dominated by the 33 chat
calls (each ~30-60 seconds with a small llama on a 2060) and the embedding of
predicate spans (a few thousand embeddings, fast). Total: ~15-20 minutes on
the reference hardware.

**There are no per-chunk LLM calls.** That is the entire point.

---

## Rivers of Flow

### River of Build

```
CLI `skein build`
   → cli.build()
      → schema_apply(db_url)              [creates tables if missing]
      → build_skein(...)
         → discover_vocabulary(...)        [D LLM calls]
         → find_mentions(...)              [server-side cursor scan of chunks]
         → compute_entity_embeddings(...)  [server-side cursor scan + numpy mean]
         → build_edges(...)                [pure numpy]
         → snap_predicates(...)            [embedding calls only]
         → persist(...)                    [single transaction]
   → CLI prints stats
```

### River of Neighbor Lookup

```
CLI `skein neighbors "Odin"`
   → cli.neighbors()
      → neighbors_of(db_url, name, limit=20)
         → SQL: SELECT … FROM skein_relations r JOIN skein_entities e …
      → CLI renders a Rich table
```

---

## Key Connectors

| From | To | Protocol |
|------|----|----------|
| `skein.core` | Postgres | `psycopg` (one connection per phase, named cursors for the scans) |
| `skein.core` | Ollama | `httpx` with explicit timeouts (120-300s) |
| `skein.cli` | `skein.core` | direct Python import |
| External callers | `skein.*` | imports listed in `__init__.py` |

---

## Determinism

Each stage that has randomness in it is seeded:

- The sampling of chunks per document is deterministic (`ORDER BY (chunk_index %% 7), chunk_index LIMIT N`).
- UMAP is seeded with `random_state=42` — actually that's a Bifröst concern;
  Skein itself doesn't UMAP-project.
- Ollama is invoked with `temperature=0.1`; identical inputs produce
  near-identical outputs (the small remaining variance is in tokenizer
  sampling, which `format=json` further constrains).

Given identical chunks, embeddings, vocabulary, and LLM, Skein produces the
same graph across runs.

---

## What can change safely

- The default predicate vocabulary (`DEFAULT_PREDICATES`).
- The sampling strategy in `discover_vocabulary` (currently 6 chunks per doc).
- The edge top-K and minimum similarity defaults.
- New CLI commands (`uv run skein <name>`).

## What must NOT change without redrawing this map first

- The shape of the public `skein_entities` / `skein_relations` schema. Other
  consumers (Bifröst, Skry, future tools) depend on it.
- The fingerprint format in `skein_build`. Bifröst's skein-graph cache keys
  off of it.
- The function signatures listed in `INTERFACE.md`.
