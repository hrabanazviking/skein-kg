# Bug 0002: Embedding dim from DB used in SQL format string without validation

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18

---

## Symptom

`infer_embedding_dim(conn)` returns an integer that is then plugged into `SCHEMA_SQL.format(dim=dim)`. The query path uses `pg_attribute.atttypmod` (a numeric column) which makes injection unlikely in well-formed databases — but the fallback path reads `embedding` from a row and uses `len(...)`, where the underlying type could be anything that supports `len()`. If a malicious actor or schema corruption produced a non-numeric value here, the format-string substitution could inject SQL.

## Expected

The dimension is validated as a positive integer in a reasonable range (16-65536) before being embedded in SQL.

## Invariant violated

Law of Fault Tolerance (defensively prevent unexpected data from reaching dangerous code paths) + general SQL-injection-by-format-string smell.

## Fix plan (additive)

```python
def infer_embedding_dim(conn: psycopg.Connection) -> int:
    ...
    dim = ...  # existing logic
    if not isinstance(dim, int) or dim < 16 or dim > 65536:
        raise RuntimeError(
            f"refusing to construct schema with implausible embedding dimension {dim!r}"
        )
    return dim
```

The same range check should run on the fallback `len(r[0])` path before returning.

## Lessons

Even when the format-substituted value "comes from the database," validate it. The cost of an `int()` + range check is negligible; the cost of a missed SQL injection is large.
