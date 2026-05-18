# Bug 0008: No retry on transient Ollama failures during vocab discovery

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`_ollama_chat` and `_ollama_embed` make one request and raise on any HTTP failure. A single network blip during a 17-minute build causes the affected per-document vocab call (or per-edge predicate snap) to fail. The outer `try/except` in `discover_vocabulary` catches it and skips the document — but a more recoverable transient (e.g. brief Ollama load spike) should retry.

## Fix plan (additive)

Add a small retry wrapper with exponential backoff:
```python
def _retry(fn, *, attempts=3, base_delay=2.0):
    for i in range(attempts):
        try:
            return fn()
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            if i == attempts - 1:
                raise
            time.sleep(base_delay * (2 ** i))
```
Apply it around the inner POST in `_ollama_chat` and `_ollama_embed`.

## Lessons

The library's contract is "per-document failures don't kill the build." Retry-with-backoff is the cheap layer that makes that contract more often true.
