# docs/bugs/INDEX.md — Skein

> Bug notes from Auditor passes. Open bugs are tracked here. Resolved bugs
> stay in the index with status `RESOLVED`.

**Last Auditor pass:** 2026-05-18 (Sólrún Hvítmynd, session 2)

---

## Open

_None. As of session 3 the entire known bug backlog is closed — 12/12
resolved across two same-day sessions._

## Resolved (Session 2 — 2026-05-18)

| # | Title | Severity | File | Note |
|---|---|---|---|---|
| 0001 | CJK / non-ASCII entity names fail to match due to ASCII `\b` | high | `skein/core.py:86-93` | [bug](0001-non-ascii-word-boundary.md) |
| 0002 | Embedding dimension untrusted in schema format string | high | `skein/schema.py:51-72` | [bug](0002-schema-dim-validation.md) |
| 0003 | `log` callable parameters untyped on public API | medium | `skein/core.py:104,232,349` | [bug](0003-log-callable-typehint.md) |
| 0004 | `build_skein` returns vague `dict`; INTERFACE.md promises a shape | medium | `skein/core.py:350` | [bug](0004-build-stats-typeddict.md) |
| 0005 | Unused imports `Iterable` and `Path` | low | `skein/core.py:23-24` | [bug](0005-unused-imports.md) |
| 0006 | Malformed entity records dropped silently | low | `skein/core.py:96-157` | [bug](0006-dropped-entity-logging.md) |
| 0007 | Default vocabulary English-biased; not documented | medium | `skein/core.py:33-40` + README | [bug](0007-english-bias-disclosed.md) |
| 0008 | Ollama timeout hard-coded; no retry | medium | `skein/core.py:55-65` | [bug](0008-ollama-retry.md) |

## Deferred

_None. Backlog is empty._

## Resolved (Session 3 — 2026-05-18, "kill the backlog")

| # | Title | Severity | File | Note |
|---|---|---|---|---|
| 0009 | `snap_predicates` was 100 lines | medium | `skein/core.py` | Refactored into 5 named helpers (`_embed_predicate_vocabulary`, `_cooccurrence_chunks_per_edge`, `_fetch_chunk_texts`, `_closest_mention_pair_span`, `_collect_predicate_spans`, `_snap_best_predicates`). Orchestrator is now 25 lines. Behavior identical. |
| 0010 | Embedding-dim consistency not validated | medium | `skein/schema.py` | `infer_embedding_dim` now runs `SELECT DISTINCT vector_dims(embedding) FROM chunks WHERE embedding IS NOT NULL` and raises with a clear message if rows disagree on dim. Gracefully falls back if pgvector lacks `vector_dims`. |
| 0011 | Default predicate vocab small + English-biased | low | `skein/core.py` + README + INTERFACE | Resolved as no-action — see [bug note](0011-vocab-enrichment.md). English bias was disclosed in 0007; the vocabulary is configurable via `SKEIN_PREDICATES` by design. |
| 0012 | Named cursor close discipline | low | `skein/core.py` | Resolved as no-action — see [bug note](0012-named-cursor-discipline.md). psycopg's `with` properly closes named cursors. Verified, documented, closed. |

---

## Categories of issues found this session

- **1 silent-loss-of-data** bug (non-ASCII entity names) → fixed with Unicode-aware boundaries
- **1 trust-boundary** issue (embedding dim from DB metadata) → fixed with int + range validation
- **3 type-hint completeness** issues on public API → fixed with `Callable` and `TypedDict`
- **1 observability gap** (silent entity drops) → fixed by counting + logging via `log=`
- **1 doc-honesty gap** (English-only) → fixed in README + INTERFACE
- **1 resilience gap** (no Ollama retry) → fixed with retry-on-transient logic

Skein's overall health is strong — the audit found no violations of its
defining iron laws (per-document LLM, additive only, sourced truth,
idempotent build, sacred source). The findings are around language
coverage, public-API rigor, and observability.
