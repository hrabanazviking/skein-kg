# Bug 0011: Default predicate vocabulary small + English-biased

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18 (no code change required — disclosed in [0007](0007-english-bias-disclosed.md); vocabulary remains configurable via `SKEIN_PREDICATES`)

---

## Symptom

`DEFAULT_PREDICATES` has 29 entries, all English narrative verbs/phrases.
Corpora about niches the default doesn't cover (e.g. chemistry, music
theory, sports) will see lots of edges snap to `associated_with` because
the right predicate isn't in the list.

## Resolution

This is a **deliberate design choice**, not a bug:

1. The predicate vocabulary is **explicitly configurable** via the
   `SKEIN_PREDICATES` env var (documented in `.env.example`, README, and
   `INTERFACE.md`).
2. The English-bias of the *default* is disclosed in
   [`0007-english-bias-disclosed.md`](0007-english-bias-disclosed.md) —
   that bug fixed the documentation gap. There is no remaining hidden bias.
3. Skein's `Law of the Honest Vocabulary` (PROJECT_LAWS) explicitly states
   the library will only ever return predicates from the vocabulary. The
   solution to a domain-specific need is to **provide the domain's
   vocabulary**, not for Skein to silently invent terms.

A future "predicate-pack" registry (one per domain) could ship in a later
version. For now: configure your own; we tell you why and where.

## Lessons

Some "bugs" are missing-features in disguise, and some missing-features
are intentional design choices. The Auditor's role is to surface them so
the architect can decide. The architect has decided this one is by design.
