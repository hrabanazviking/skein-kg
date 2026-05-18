# DEVLOG.md — Skein

> *Scribe. Append-only.*

---

## 2026-05-18 — Inception

**Crew:** Volmarr Wyrd (Architect-in-chief), Claude Opus 4.7 (Master
Craftsman).

Skein was **invented** in this session. Not adapted from upstream, not
ported from a paper — composed from scratch in response to a problem.

### The problem

Volmarr was running a llama-per-chunk knowledge-graph extractor against a
~23 000-chunk corpus on a 6 GB RTX 2060 (laptop). 13 minutes in, the batch
had processed 200 chunks (0.9%). Linear extrapolation: ~76 hours of
sustained GPU. The laptop was visibly warming. The architect asked:

> "Is there some new... perhaps slightly less good results, but vastly less
> load to do something kinda similar but in like 1/1000th the workload?"

### The invention

Together we sketched an alternative pipeline that:

1. Does the expensive operation (autoregressive LLM) **once per document**,
   not per chunk.
2. Substitutes regex for per-chunk text understanding (entities are
   typically capitalized noun phrases; regex finds them fine).
3. Aggregates per-entity embeddings as the mean of the embeddings of chunks
   the entity appears in.
4. Derives edges from top-K cosine between entity-embeddings, not from
   text reasoning.
5. **Snaps predicates** to a fixed vocabulary by embedding the text-span
   between two co-occurring mentions and finding the closest vocabulary
   verb by cosine. (This was the genuinely novel step — neither of us had
   seen it packaged that way.)

This bounded the LLM budget by *D* (document count, ~33 for the test
corpus) rather than *C* (chunk count, ~23 000). A ~700× reduction in
autoregressive calls.

The result on the test corpus: **276 entities, 124 194 mentions, 855
relations** built in **17.8 minutes** wall time. Quality: top entities make
sense (Odin, Aesir, Runes, Helheim, Tietäjä, wyrd), top predicates make
sense (worshipped_as, created, depicted_as, associated_with, synonym_of,
ruled, defeated, received_from, located_in). Rough edges (e.g. "9th
century" picked up as an entity, abstract nouns like "knowledge" promoted)
but well within the "75% of LLM-per-chunk quality at 1/500 the cost"
contract.

### Naming

Together with the architect we considered:
- **Skein + Skry** (Norse, alliterative, paired) ← chosen
- **Loom + Lens**
- **Wyrd + Beholden**
- **VibeGraph + LiveLens**

Skein won for sound + meaning fit: a skein is a loose coil of thread, and
also a flock of geese in flight. Both fit: the woven web of entities, and
the way related concepts move together through a corpus.

### Implementation

- `skein/core.py` — the four-step pipeline (vocabulary → mentions →
  embeddings → edges + predicate snapping), `persist()`, `neighbors_of()`
- `skein/schema.py` — `skein_entities`, `skein_entity_chunks`,
  `skein_relations`, `skein_build` with embedding dim inferred from the
  parent `chunks.embedding` column
- `skein/cli.py` — typer-based CLI: `build`, `stats`, `neighbors`
- `skein/__init__.py` — reexports the public surface

Total source: ~500 lines including comments and docstrings.

### Bugs found during inception (and how we fixed them — additively)

**BUG-001: psycopg `%` in SQL is interpreted as a placeholder.** The
deterministic sampling query was:
```sql
ORDER BY (chunk_index % 7), chunk_index LIMIT %s
```
psycopg treated the `%` as a parameter prefix and raised `ProgrammingError:
incomplete placeholder: '%'`. **Fix:** double it to `%%`. Documented in
`core.py:128`. (Additive: did not remove or rework the modulo trick;
escaped the literal.)

### Decisions

- **Why one LLM call per document, not per chunk-cluster?** Documents have
  natural human-meaningful titles and stable topical coherence; an
  unsupervised cluster does not. Per-doc vocab is much easier to debug:
  "the entities from doc 17 came from doc 17's title and excerpts."
- **Why fix predicate vocabulary?** Snapping is fast (`O(P)` cosine per
  edge, P ~ 30) and predictable. An open vocabulary would require either
  (a) more LLM calls or (b) noisy clustering of verb tokens. Both
  contradict Skein's identity.
- **Why no incremental mode?** The persist step is a single transaction —
  all rows or none. Adding "incremental" introduces partial-state hazards
  and adds complexity for a feature that doesn't pay for itself: full
  builds take 15-20 minutes.

### Pushed

Published as MIT-licensed public repository at
[`hrabanazviking/skein-kg`](https://github.com/hrabanazviking/skein-kg).
Initial commit + ME docs (SYSTEM_VISION, DOMAIN_MAP, ARCHITECTURE,
PROJECT_LAWS, INTERFACE, skein/README_AI) pushed in the same session.

### Lessons recorded

1. **The expensive step in any LLM pipeline is autoregressive generation,
   not embedding.** Embedding is one forward pass; chat generation is one
   forward pass per output token. For a 700-token JSON description that's
   ~700× more compute per item.
2. **Embeddings already encode the structure.** Anything that re-derives
   that structure through generation is paying twice.
3. **Bounded predicate vocabularies, when snapped via embedding cosine,
   give surprisingly good results.** This is the most novel ingredient and
   the one most worth writing up.

### Open threads

- Auditor pass on `core.py` per the Mythic Engineering bug-hunt rite —
  findings to live in `docs/bugs/`.
- Robustness pass: type-hint audit; method-length check; cross-platform
  audit (regex behavior under different locales, etc.).
- Invariant test scaffold under `tests/`.
- Consider a `--sample-larger` flag for documents where 6 excerpts isn't
  representative.

---

## 2026-05-18 — Session Two: Full Mythic Engineering Treatment

Triggered by the architect pointing at the canonical Mythic Engineering
repo and asking for the full doctrine + bug hunt + robustness rites
applied. This session adds PHILOSOPHY, DATA_FLOW, DEVLOG (this file),
MYTHIC_ENGINEERING, the Auditor's bug notes under `docs/bugs/`, and the
first round of invariant tests.
