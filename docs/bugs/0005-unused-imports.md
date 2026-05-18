# Bug 0005: Unused imports in `skein/core.py`

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`from typing import Iterable` and `from pathlib import Path` are imported at the top but neither is used.

## Fix plan (additive)

Remove both. (The `Callable` import added in bug 0003 takes their slot.)

## Lessons

Dead imports are dead documentation: a reader infers "these types must be used somewhere" and wastes time looking.
