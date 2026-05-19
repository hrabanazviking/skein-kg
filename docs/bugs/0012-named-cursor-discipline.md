# Bug 0012: Named cursors `chunkscan` and `embscan` rely on context-manager close

**Discovered:** 2026-05-18 by Auditor
**Status:** RESOLVED 2026-05-18 (no code change required — current behavior is correct)

---

## Symptom

`core.py` uses `conn.cursor(name="chunkscan")` and `conn.cursor(name="embscan")`
inside `with` blocks. Audit flag suggested explicit `.close()` might be
needed for named cursors (server-side state).

## Resolution

Verified the existing pattern is correct:

```python
with psycopg.connect(db_url) as conn, conn.cursor(name="chunkscan") as cur:
    ...
```

The `with` statement on the cursor calls `__exit__` which closes the
cursor cleanly, including releasing server-side state. The `with` on the
connection ensures the connection is closed even if the cursor close
raises.

Explicit `.close()` would be redundant. Modern psycopg (3.x) handles
named-cursor cleanup correctly via context managers.

## Lessons

Not every Auditor flag is a real defect. The role of Closing as RESOLVED-
no-action — rather than silently ignoring — preserves the audit trail so
a future contributor doesn't re-flag the same line and wonder if it was
ever investigated.
