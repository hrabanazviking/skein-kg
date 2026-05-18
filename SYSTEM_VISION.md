# SYSTEM_VISION.md — Skein
## *The Genesis Scroll*

> *Sacred and unchanging.* If a future change to this project does not serve
> what follows, the change is wrong — not this scroll.

---

## Name and Nature

**Skein** — a coil of threads connecting names. A loose, woven knot.

Skein is a Python library that builds a knowledge graph from a corpus that
*already lives in a vector store*, **without** running a generative LLM on
every chunk. It treats the embeddings as the primary substrate and uses an
LLM only sparingly — once per document — to discover what the named things
even are.

It is **not** an LLM. It is **not** an embedding model. It is **not** a
database. It is a single algorithm with a small handful of moving pieces
and one stubborn opinion: *generative models are too expensive to be used
indiscriminately when the meaning is already encoded in the vectors*.

---

## Purpose — The Great Why

To make a knowledge graph affordable on a laptop.

Conventional KG-extraction pipelines run a generative LLM on every chunk,
asking it to read the text and produce structured JSON triples. For a
20,000-chunk corpus on consumer hardware this takes **days** of sustained
GPU load and shortens the life of the machine. Skein achieves ~75% of the
graph quality at ~1/500 of the computational cost by routing the work
through three cheaper substrates: a single LLM call per document for
vocabulary discovery, plain regex for mention-finding, and embedding
arithmetic for entity centroids, edges, and predicate selection.

The aim is **not** to compete with state-of-the-art KG extractors. The aim
is to make *some* knowledge graph available *at all* in a budget where
none was previously possible.

---

## Primary Rite — Core User Interaction

> ```bash
> uv run skein build      # ~15-20 minutes for ~20k chunks
> uv run skein stats      # see counts, top entities, top predicates
> uv run skein neighbors "Odin"   # one entity, its connections, its predicates
> ```

Or, used as a library:

```python
from skein import build_skein, neighbors_of
build_skein(db_url, ollama_url=..., embed_model=..., chat_model=...)
neighbors_of(db_url, "Odin", limit=20)
```

If the Primary Rite ever becomes harder than that — wrong.

---

## Feeling / Vibe

- **Quietly clever.** Skein is the friend who solves the problem in a way
  that makes you go "wait, that's allowed?"
- **Honest about what it gives up.** Predicates come from a fixed vocabulary;
  Skein will never invent `sacrificed_eye_to`. The README and docs say so
  plainly.
- **Friendly to small machines.** A travel laptop should be able to run the
  full pipeline without overheating.

---

## Unbreakable Vows

1. **The Loom Shall Not Grind on Every Chunk.** The number of generative
   LLM calls is bounded by the number of *documents*, not chunks. If a
   future change requires per-chunk generation, it is not a Skein change
   — it belongs in a different tool.

2. **The Loom Shall Be Honest About Its Bounds.** Skein cannot produce
   predicates outside its vocabulary. The vocabulary is configurable
   (`SKEIN_PREDICATES`) and visible. No hidden "smart picks."

3. **The Loom Shall Source Every Fact.** Every `(subject, predicate,
   object)` triple in `skein_relations` carries `evidence_chunk_ids`. The
   user can always click through to the chunks that justified the claim.

4. **The Loom Shall Be Reproducible.** Given the same chunks, the same
   embeddings, the same vocabulary, and the same LLM (with low
   temperature), Skein produces the same graph. Determinism is a feature.

5. **The Loom Shall Be Idempotent.** Re-running `skein build` on an
   already-built graph deletes the old rows in one transaction and
   rebuilds. There is no half-built state.

6. **The Loom Shall Not Touch the Source.** Skein reads from `documents`
   and `chunks` and writes only to `skein_*`. The source-of-truth tables
   are sacred.

---

## What This Project Is Not

- Not an LLM. (Uses one *briefly*, per document.)
- Not a vector store. (Reads from one; never embeds.)
- Not a query-time tool. (See [`skry-kg`](https://github.com/hrabanazviking/skry-kg)
  for instant entity lookups.)
- Not a 3D viewer. (See [Bifröst](https://github.com/hrabanazviking) for that.)
- Not a general-purpose graph database. The schema is opinionated: one row
  per entity, one row per edge, one row per build.

Skein is one focused algorithm, well-bounded, well-tested, well-documented.
That is the whole offer.
