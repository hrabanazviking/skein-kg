# Bug 0003: `log` callable parameters lack `Callable[[str], None]` type hints

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`build_skein`, `discover_vocabulary`, `snap_predicates` all take a `log=` parameter with a default of `print` or `None` — but no type hint. The INTERFACE.md promises a `Callable`-shaped contract.

## Fix plan (additive)

Add `Callable[[str], None]` to each `log` parameter. Import `Callable` from `typing`.

## Lessons

Public API surface is documented in INTERFACE.md but enforced in the signature. Both should align.
