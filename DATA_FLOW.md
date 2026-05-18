# DATA_FLOW.md — Skein

> *Architect + Cartographer.*

---

## Entry Points

Skein has exactly two doors data can come through:

| # | Door | Format | Direction |
|---|------|--------|-----------|
| 1 | `documents` + `chunks` tables (Postgres, with `embedding vector(N)`) | SQL rows | **In, read-only** |
| 2 | `.env` (or env vars) | key=value | **In, config only** |

Outgoing surfaces:

| # | Door | Format | Direction |
|---|------|--------|-----------|
| A | `skein_entities`, `skein_entity_chunks`, `skein_relations`, `skein_build` tables | SQL rows | **Out, owned by Skein** |
| B | CLI stdout via `rich.console` | colored text | **Out, user-facing** |
| C | Caller-provided `log=` callable | strings | **Out, library callers' choice** |

That's it. No file writes, no network destinations beyond Ollama, no
mutation of the parent corpus.

---

## River of Build

```
CLI:  uv run skein build
   skein.cli.build()
      reads .env via python-dotenv
      schema_apply(db_url)
         creates skein_entities, skein_entity_chunks, skein_relations,
         skein_build (idempotent — CREATE TABLE IF NOT EXISTS)
      build_skein(db_url, ollama_url, embed_model, chat_model, ...)

build_skein:
  phase 1 — discover_vocabulary(db_url, ollama_url, chat_model)
    SELECT id, title FROM documents ORDER BY id
    for each document:
      SELECT 6 chunks (stable order: ORDER BY (chunk_index %% 7), chunk_index LIMIT 6)
      ollama_chat(SYSTEM_VOCAB, sampled excerpts) → JSON {entities: [{name, kind, aliases}]}
      parse_vocab_response → merge into global vocab dict
    yields ~D LLM calls total (D = doc count)

  phase 2 — find_mentions(db_url, vocab)
    SELECT id, text FROM chunks (named server-side cursor)
    for each chunk:
      for each (canonical_name, alias_list) in patterns:
        if any alias regex matches: record mention
    yields entity → set[chunk_id]

  phase 3 — compute_entity_embeddings(db_url, mentions)
    all_chunk_ids = union of all mention chunks
    SELECT id, embedding FROM chunks WHERE id = ANY(all_chunk_ids)
    for each chunk: L2-normalize
    for each entity:
      mean(normalized chunk vectors where entity appears)
      L2-normalize the mean
    yields entity_key → unit vector

  phase 4 — build_edges(keys, embeddings, top_k, min_sim)
    sim = unit @ unit.T  (E × E cosine matrix)
    for each entity: keep top_k neighbors above min_sim
    yields list of (i, j, sim)

  phase 5 — snap_predicates(db_url, ollama_url, embed_model, edges, vocab)
    ollama_embed(predicate templates "is <predicate>") once
    for each edge:
      co_chunks = mentions[a] ∩ mentions[b], capped at 8
      for each co_chunk:
        find closest mention pair (smallest gap between regex matches)
        extract text-span between mentions ± window/4
      ollama_embed(spans) batched ~32 at a time
      mean span vector → cosine snap to nearest predicate
    yields (a, b) → (predicate, evidence_chunk_ids)

  phase 6 — persist(db_url, vocab, mentions, embeddings, edges, pred_map, fp)
    one transaction:
      DELETE FROM skein_relations
      DELETE FROM skein_entity_chunks
      DELETE FROM skein_entities
      INSERT vocab → skein_entities
      INSERT (entity_id, chunk_id) pairs → skein_entity_chunks
      INSERT edges with predicates → skein_relations
      INSERT row into skein_build with fingerprint + stats
    COMMIT
```

## River of Lookup

```
CLI:  uv run skein neighbors "Odin"
   neighbors_of(db_url, "Odin", limit=20)
     SELECT id, name, kind, mentions FROM skein_entities WHERE name_norm = lower(name)
     SELECT r.predicate, e.name, e.kind, r.sim, r.evidence_chunk_ids, direction
       FROM skein_relations r JOIN skein_entities e ON ...
       WHERE r.subject_id = E.id OR r.object_id = E.id
       ORDER BY r.sim DESC LIMIT N
     return {found, id, name, kind, mentions, edges: [...]}
   render via rich.Table
```

## River of Stats

```
CLI:  uv run skein stats
   COUNT(*) FROM skein_entities, skein_relations
   GROUP BY kind ORDER BY count
   GROUP BY predicate ORDER BY count
   ORDER BY mentions DESC LIMIT 10
   render via rich.Table
```

---

## Storage Locations and Lifecycles

| Storage | Owner | Lifetime | Invalidation |
|---|---|---|---|
| `documents` table | parent ingest project — Skein READ ONLY | persistent | n/a |
| `chunks` table (id, document_id, text, embedding) | parent — Skein READ ONLY | persistent | n/a |
| `skein_entities` | Skein | persistent | DELETE + INSERT on each build |
| `skein_entity_chunks` | Skein | persistent | DELETE + INSERT on each build |
| `skein_relations` | Skein | persistent | DELETE + INSERT on each build |
| `skein_build` | Skein | persistent, append-only | never deleted (audit trail) |

---

## Boundary Crossings

| # | From | To | Format |
|---|------|----|--------|
| 1 | Postgres | `discover_vocabulary` | rows of (id, title), per-doc samples of `text` |
| 2 | `discover_vocabulary` | Ollama | system + user prompt strings; `format=json` |
| 3 | Ollama | `_parse_vocab_response` | JSON string in `message.content` |
| 4 | Postgres | `find_mentions` | streaming `(id, text)` via named cursor |
| 5 | Postgres | `compute_entity_embeddings` | streaming `(id, embedding)` |
| 6 | Postgres + Ollama | `snap_predicates` | chunk text + embedded predicate templates + embedded text-spans |
| 7 | `persist` | Postgres | single COMMIT transaction with all writes |

---

## Failure Modes

| Failure | Where caught | Behavior |
|---|---|---|
| Ollama unreachable | `_ollama_chat` raises → bubbles up | Whole build fails with stack trace; nothing written (transaction not committed yet) |
| Individual doc vocab call fails | `discover_vocabulary` catches per-doc | Logs warning via `log=`, continues with the rest |
| LLM returns malformed JSON | `_parse_vocab_response` returns `[]` | Doc contributes no entities; logged |
| Postgres unreachable | `psycopg.connect` raises | Build aborts; nothing written |
| No predicate span found for an edge | `snap_predicates` skips that edge | Edge dropped (not persisted), logged |
| Chunk text has no mention of either side of an edge | same as above | Edge dropped |
| Embedding dim mismatch | pgvector cast fails on INSERT | Build aborts mid-transaction; ROLLBACK; nothing persisted |

The persist step is one transaction — either all-or-nothing.
