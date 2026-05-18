# Bug 0004: `build_skein` returns `dict`; INTERFACE.md promises a specific shape

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`def build_skein(...) -> dict:` — the type is vague. INTERFACE.md documents the keys (`n_entities`, `n_mentions`, `n_edges`, `build_seconds`) but a caller has to look that up.

## Fix plan (additive)

Define a `TypedDict`:
```python
from typing import TypedDict
class SkeinBuildStats(TypedDict):
    n_entities: int
    n_mentions: int
    n_edges: int
    build_seconds: float
```
Return type becomes `-> SkeinBuildStats`.

## Lessons

`-> dict` is rarely the right return annotation for a function whose shape is part of the public contract.
