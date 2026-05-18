# PHILOSOPHY.md — Skein

> *Written by the Skald.*

---

## The Wound This Project Salves

Knowledge-graph extraction at scale, the way the field practices it, is
**absurdly expensive for the value it returns.**

The standard pipeline asks a generative language model to *read every chunk*
and *write structured JSON* describing the entities and relations it
contains. For 20 000 chunks on consumer hardware, that's days of
sustained GPU load, gigawatt-hours of electricity globally, and a quiet
assumption that whoever runs this pipeline owns either an H100 farm or a
fat cloud account.

A laptop owner with a 6 GB GPU and a thousand pieces of text gets nothing.

This is a category error. The meaning is **already in the embeddings**.
The vectors *are* the substrate of similarity, of clustering, of relation.
The job of "extracting" the graph is largely the job of *naming* what is
already encoded — and naming is a much cheaper operation than describing.

Skein refuses the expensive pattern. It does the cheap operations
(vocabulary discovery, mention finding, embedding averaging, cosine top-K,
predicate snapping by embedded text-spans) and bounds the expensive one
(generative LLM use) to **once per document**, not once per chunk.

The result: ~75% of the graph quality at ~1/500 the compute. The laptop
owner gets a real knowledge graph. The cloud account is not required.

---

## Core Ethos

**Embeddings are substrate, not output.** They are the medium in which
meaning is already encoded. Reasoning over them does not require
regenerating their content through an LLM.

**Bound the expensive operation; lean on the cheap ones.** One LLM chat call
per document is cheap. Twenty thousand chat calls is not. Embedding lookups
are cheap. Regex is cheap. Mean-of-vectors is cheap. Compose these.

**Honesty about the trade.** Skein cannot invent predicates outside its
vocabulary. It cannot disambiguate `Odin` from `Wotan` from `Allfather`
without help. It loses subtle event semantics. The README and PHILOSOPHY say
so plainly. A user who needs those things should use a different tool — or
do a per-chunk LLM pass *on top of* Skein for the parts that need it.

**Reproducibility is a feature.** Same chunks + same embeddings + same
vocabulary + low LLM temperature → same graph. Across runs, across machines,
across operators. The fingerprint scheme in `skein_build` makes this
auditable.

---

## Values

| Value | What it means in practice |
|---|---|
| **Bounded LLM budget** | Calls scale with documents (D), not chunks (C). D ≪ C in any real corpus. |
| **Cheap operations only** | Regex, cosine, mean — no clever Python tricks, no exotic libraries. |
| **Sourced truth** | Every relation row carries `evidence_chunk_ids`. The user can always click through. |
| **Determinism** | Sampling order-stable, LLM temperature low, sklearn seeded — same input, same output. |
| **Single purpose** | Skein builds graphs. It does not query them, visualize them, or extract them at query time. Refuse the urge to grow. |

---

## Iron Laws

1. **The number of autoregressive LLM calls per build is bounded by the
   number of documents.** Any contribution that adds per-chunk generation
   is not Skein — it belongs in a different repository.

2. **Predicates come from a fixed vocabulary.** No invented predicates.
   The snapping algorithm returns the *nearest* predicate by cosine; the
   row records the similarity so the user can judge.

3. **Every relation carries evidence.** No row written without at least one
   `evidence_chunk_ids` entry. Unsourced claims are forbidden.

4. **Reads from `documents` and `chunks`; writes only to `skein_*`.** The
   parent corpus is sacred. Skein touches no schema it did not create.

5. **Idempotent builds.** `skein build` wipes prior `skein_*` rows in one
   transaction and rebuilds. No partial state. No "incremental" mode.

6. **No `print()` in library code.** Progress is reported through the
   `log=` callable that callers provide.

7. **The public surface is version-stable.** The three reexported functions
   in `skein/__init__.py` (`build_skein`, `neighbors_of`, `schema_apply`)
   do not change signature in any 0.x.y release.

---

## Synthesis Approach

Skein composes well-understood building blocks:

- `psycopg` + `pgvector` for storage I/O
- `numpy` for cosine arithmetic
- `httpx` for Ollama calls
- regex for mention finding (faster and more predictable than NER for our
  scale)
- a small predefined predicate vocabulary embedded once and snapped against

There is no exotic dependency. There is no novel mathematics. The novelty
is the **composition** and the **discipline** of where each component is
used.

The hardest design choice was vocabulary discovery: per-chunk LLM was too
expensive, per-corpus too vague, per-cluster (semantic clusters of chunks)
too hard to explain. Per-document landed as the right balance — documents
already have natural-language titles and coherent topics, and the operator
will recognize what came from where.

---

## What This Project Is Not

- **Not an LLM.** It calls one, briefly, per document.
- **Not a vector store.** It reads from one; never embeds.
- **Not a query-time tool.** That is [`skry-kg`](https://github.com/hrabanazviking/skry-kg).
- **Not a viewer.** That is [`bifrost-viewer`](https://github.com/hrabanazviking/bifrost-viewer).
- **Not a general-purpose graph database.** The schema is opinionated; one
  row per entity, one per edge, one per build.
- **Not competing with academic state-of-the-art KG extractors.** It is the
  artifact that makes *some* knowledge graph available on a laptop, where
  none was available before.

---

## Ultimate Aim

That a person with a corpus of text and a 6 GB GPU can build a usable
knowledge graph in fifteen minutes — and that the graph, once built, will
serve them well enough that they stop reaching for the expensive
alternative.

If a future contributor finds themselves wanting to add a per-chunk LLM
call "just this once" to improve quality: stop. That change belongs in a
different repository. Skein's identity is "the KG library that doesn't
generate per chunk." If we abandon that, we are no longer Skein.
