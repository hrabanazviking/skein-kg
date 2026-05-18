# PROJECT_LAWS.md — Skein
## *Immutable Rules*

> These rules are non-negotiable. A change that breaks one is a different
> project, not an evolution of this one.

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

## Law of Idempotent Builds

`skein build` is idempotent at the row level: it deletes all existing
`skein_entities`, `skein_entity_chunks`, `skein_relations` rows in a single
transaction before writing fresh ones. There is no "incremental" mode. If
the source changed, rebuild the whole graph — it is cheap enough.

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
