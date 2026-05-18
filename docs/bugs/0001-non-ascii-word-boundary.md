# Bug 0001: Non-ASCII entity names silently fail to match (`\b` is ASCII-only)

**Discovered:** 2026-05-18 by Auditor (Sólrún Hvítmynd)
**Status:** RESOLVED 2026-05-18

---

## Symptom

`_entity_regex(name)` builds a pattern wrapped in `\b...\b`. Python's `\b` word boundary is ASCII-by-default. For non-ASCII proper nouns — Mímir, Þórr, 龙王, القرآن — the boundary characters around the name (often non-ASCII letters or whitespace) don't always satisfy `\b`'s definition. The discovered entity is silently never matched, fragmenting the entity graph.

For Norse content this is *especially* bad: names with þ, ð, æ, ö, ó are common and central.

## Expected

Entity names containing or surrounded by non-ASCII letters match correctly. Word boundaries should respect Unicode.

## Invariant violated

PROJECT_LAWS — *Law of Sourced Truth.* The vocab is built from these names; if mentions don't link back, the truth is unrooted.

## Suspected domain

`_entity_regex` in `skein/core.py`.

## Reproduction

```python
import re
name = "Mímir"
pat = re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)
# In some surrounding contexts ("…of Mímir's…") this matches; in others ("Mímir,") works;
# but with non-ASCII boundary chars ("Mímirinn") it falsely matches partial because Python
# treats the boundary between two non-ASCII letters inconsistently with ASCII conventions.
```
For full Unicode-aware behavior we want explicit lookarounds.

## Local or structural

**Structural** — affects the regex compile site and behavior across the whole pipeline.

## Fix plan (additive)

Replace `\b{body}\b` with explicit Unicode-aware lookarounds:
```python
body = r"\s+".join(parts)
return re.compile(rf"(?<![\w]){body}(?![\w])", re.IGNORECASE | re.UNICODE)
```
where `re.UNICODE` is on by default in Python 3 but stated for clarity, and the `\w` in the lookarounds is Unicode-aware. This treats "any letter, digit, or underscore" as a word char on both sides, which works for ASCII and non-ASCII consistently.

## Lessons

`\b` is one of the oldest "looks portable, isn't" features in regex. For any vocabulary library that may see non-ASCII input, use explicit Unicode lookarounds.
