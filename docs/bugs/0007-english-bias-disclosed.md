# Bug 0007: Default predicate vocabulary is English-biased; not disclosed

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`DEFAULT_PREDICATES` is tuned for English narrative content (`son_of`, `ruled`, `defeated`, etc.) and the `SYSTEM_VOCAB` prompt is in English. README and INTERFACE.md don't disclose this — a user with an Arabic / Mandarin / Russian corpus would not realize predicate quality will be poor without modifying the vocabulary.

## Fix plan (additive)

Add a clear disclosure block to both README.md and INTERFACE.md:

> **Language scope.** Skein's default predicate vocabulary and entity-discovery prompt are tuned for English-language narrative content. For non-English corpora, supply your own `SKEIN_PREDICATES` and consider running the entity discovery prompt in the target language (see `SYSTEM_VOCAB` in `skein/core.py`).

## Lessons

A tool that "just works" on Norse-English text but not on Mandarin is a useful tool. A tool that *quietly* works less well on Mandarin is a lie. The fix is honesty, not feature work.
