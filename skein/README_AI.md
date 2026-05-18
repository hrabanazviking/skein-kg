# skein/ — README_AI.md

This directory is **The Algorithm** (see `../DOMAIN_MAP.md`). It is the
load-bearing center of the project.

## What's here

- `__init__.py` — reexports the three public functions. **Do not add to this
  list without updating `../INTERFACE.md` in the same commit.** The exported
  surface is a contract.
- `core.py` — the four-step pipeline + persistence + lookup helper. The
  expensive functions are split out so each can be tested or replaced
  independently.
- `schema.py` — table DDL + embedding-dimension inference. Idempotent.
- `cli.py` — Typer-based command line. Strictly a presentation layer over
  `core.py`; should never re-implement algorithmic logic.

## Where the LLM calls live

Two functions touch a generative LLM (autoregressive chat):

- `discover_vocabulary(...)` — issues exactly one `/api/chat` request per
  document. The system prompt is the module-level constant `SYSTEM_VOCAB`
  in `core.py`. Output is parsed as JSON via `_parse_vocab_response(...)`.

That is the entire chat budget. If you find yourself wanting to add a third
LLM-chat caller, **stop**. It probably belongs in a different tool. Skein's
identity is "the KG library that doesn't generate per chunk."

Two functions use the embedding endpoint (non-generative, single forward pass):

- `snap_predicates(...)` — embeds (a) the predicate vocabulary templates once,
  and (b) the text-spans between entity mentions in co-occurrence chunks.
  Cosine-snaps each edge to its nearest predicate.

## How the pipeline composes

`build_skein(...)` is the top-level orchestrator. It runs the four phases in
order, passing immutable state (lists, dicts, numpy arrays) from one to the
next. There is no shared mutable state and no class hierarchy. This is
intentional — each phase is a function that takes inputs and returns outputs,
making each one independently testable.

## How to make changes

1. **New predicate.** Add to `DEFAULT_PREDICATES` in `core.py`. Document in
   the README's vocabulary section. Existing builds remain valid; the new
   predicate appears only after the next `skein build`.

2. **Tune sampling.** `discover_vocabulary(samples_per_doc=...)`. Currently 6.

3. **Tune edges.** `build_edges(top_k=..., min_sim=...)`. Higher top_k =
   denser graph but noisier. Higher min_sim = sparser but cleaner.

4. **New CLI command.** Add to `cli.py` only; do not add CLI concerns to
   `core.py`.

5. **Schema change.** This is a big deal. Edit `schema.py`, and update
   `fingerprint` in `core.py` to embed a new version prefix so old caches
   on the consumer side are detected as stale.

## What to never do

- Add a per-chunk LLM call. (See Law of the Bounded LLM Budget.)
- Hardcode a predicate inside the snapping logic instead of going through
  the vocab. (See Law of the Honest Vocabulary.)
- Mutate `documents` or `chunks`. (See Law of the Sacred Source.)
- Write rows without populating `evidence_chunk_ids`. (See Law of Sourced
  Truth.)
- Use `print()` in `core.py`. Pass progress through the `log=` callable so
  the caller decides.
