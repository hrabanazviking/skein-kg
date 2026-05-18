# Bug 0006: Malformed entity records dropped silently in vocab discovery

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

In `discover_vocabulary`, entities returned by the LLM that fail validation (missing name, name too long, etc.) are silently skipped. The log reports the count *returned by the LLM*, not the count *accepted*. A 50%-malformed response would look fine in the logs.

## Fix plan (additive)

Track accepted vs dropped count per document:
```python
n_accepted = 0; n_dropped = 0
for e in ents:
    if not <valid>:
        n_dropped += 1
        continue
    ...
    n_accepted += 1
if log:
    log(f"  doc {doc_id} '{title}': +{n_accepted} (dropped {n_dropped} malformed)")
```

## Lessons

Silent skips erase information. Always report what was skipped and why.
