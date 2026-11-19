# PROJECT_LAWS.md — Skein
## *Current Project Laws (revised 2026-11-19)*

> Owner-approved newer decisions supersede conflicting older project rules. The 2026-11-04 Bifröst Second Brain master expansion roadmap requires incremental processing as the preferred future normal mode. Maintain backward-compatible full-build behavior and data preservation until an incremental replacement has passed tests; do not mistake the legacy code's current limitations for the system's governing requirements. These laws may evolve through documented, owner-authorized revisions.

---

## Law of the Bounded LLM Budget

The number of autoregressive LLM calls per build is bounded by the number of
*documents*, not chunks. If a contribution requires per-chunk generation, it
is not Skein — it is a different tool living in a different repository.

## Law of the Honest Vocabulary

Predicates come from `DEFAULT_PREDICATES` (or whatever the user provides via
`SKEIN_PREDICATES`). The library will never silently invent a predicate not
in the list. If the snapping has no good match, it returns the *nearest* one
by cosine and reports the similarity in the relation row — but it does not
hallucinate new vocabulary.

## Law of Sourced Truth

Every triple in `skein_relations` carries `evidence_chunk_ids`. No row is
ever written without at least one evidence chunk. A future consumer must
always be able to follow the citation back to the text that justified the
claim.

## Law of the Sacred Source

Skein **reads** from `documents` and `chunks`. Skein **never writes to or
schema-modifies** them. Skein owns the `skein_*` namespace and nothing more.

## Law of Incremental-First, Versioned, Atomic Graph Updates

**Design authority (2026-11-19):** Newer owner-approved incremental architecture supersedes the former "no incremental" rule. The desired normal update path is `incremental_v2`: inspect durable source ID/revision/hash deltas, reuse compatible extraction caches, retract obsolete per-source evidence, update affected graph neighborhoods and publish a validated generation atomically. No global rebuild merely because a document was added, changed, or removed, and no graph rebuild when an API connection changes.

**Backward compatibility:** The existing `skein build` / `build_skein()` full-build implementation continues to have its currently tested, atomic, reproducible behavior until an independently versioned incremental path is implemented, benchmarked, verified on a cloned database and approved for production. The original full build remains an explicitly selectable recovery/reconciliation operation thereafter. This law changes the project requirement; it does **not** claim that incremental code is already deployed.

**Preservation:** A failed or partial incremental run must never replace the last known-good published graph or modify canonical `documents`/`chunks` source records. Persist per-document cache and stage checkpoints; preserve attributable evidence, versioned embedding/model identities, quality checks, safe rollback, pause/resume, and owner-approved full reconciliation. New public APIs extend rather than silently change existing signatures.

## Law of Determinism

The build must be reproducible given identical inputs. Seeds are set
explicitly. Sampling is order-stable. LLM temperature is low and
`format=json` is enforced. The fingerprint scheme in `skein_build` is
content-addressed (chunk count + max id + doc count + max id) so that any
change in the source produces a different fingerprint.

## Law of Fault Tolerance

The build is best-effort. If a single document's LLM vocabulary call fails,
log a warning and continue. If a single edge's predicate-snapping fails,
that edge gets dropped, not the build. The transaction at persist time
ensures partial state never leaks.

## Law of No Generative Edge Inference

Edges are derived from embedding cosine + text-span embedding + nearest-vocab
cosine. They are **not** asked of an LLM. Adding "what predicate is between
these two entities, llama?" calls is forbidden — that would re-create the
exact cost we built Skein to avoid.

## Law of the Public Surface

The functions reexported from `skein/__init__.py` (`build_skein`,
`neighbors_of`, `schema_apply`) form the public API. They are version-stable.
Adding new public functions is fine; changing the signature of an existing
one requires bumping the major version.

## Law of Honest Logs

Use `print()` only inside the CLI's Rich renderers. Library code that needs
to report progress accepts a `log=` callable (default: `print`) and the
caller decides what to do with it. Library code does not establish global
logger handlers.

## Law of Single-Purpose

Skein builds graphs. Skein does not query them at scale — for that there is
`neighbors_of` (small, one-entity convenience) and the consumer database.
Skein does not visualize them — for that there is Bifröst. Skein does not
extract them at query time — for that there is `skry-kg`. Refuse the urge
to absorb adjacent concerns.

## Rite of Preservation

Commit messages: short subject (under 70 chars), blank line, paragraph on
the *why*. Add `Co-Authored-By: …` for pair work.

## Rite of Return

`git revert` over `git reset --hard` for anything pushed.

## Rite of Vocabulary Edit

To change the default predicate vocabulary, edit `DEFAULT_PREDICATES` in
`skein/core.py`, bump the version in `pyproject.toml`, and note the change
prominently in the README's "Status" section. Existing consumers may rely on
specific predicate names.
