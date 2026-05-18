# MYTHIC_ENGINEERING.md — Skein

> *How to work in this repository under the [Mythic Engineering](https://github.com/hrabanazviking/Mythic-Engineering)
> convention.*

---

## The Scrolls

| Scroll | What it tells you |
|---|---|
| [`SYSTEM_VISION.md`](SYSTEM_VISION.md) | The soul — what Skein exists to do |
| [`PHILOSOPHY.md`](PHILOSOPHY.md) | The deeper why — the wound it salves, the iron laws |
| [`DOMAIN_MAP.md`](DOMAIN_MAP.md) | Realm boundaries — what belongs where |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Bones — major structure |
| [`DATA_FLOW.md`](DATA_FLOW.md) | Rivers of flow — every data path |
| [`PROJECT_LAWS.md`](PROJECT_LAWS.md) | Immutable rules |
| [`INTERFACE.md`](INTERFACE.md) | Public Python API contract |
| [`README.md`](README.md) | Outward-facing intro |
| [`DEVLOG.md`](DEVLOG.md) | What changed, why, what was learned |
| [`skein/README_AI.md`](skein/README_AI.md) | Notes for editing the code in `skein/` |
| [`docs/bugs/`](docs/bugs/) | Open bug notes from Auditor passes |

## How to Start a Session

1. Read [`DEVLOG.md`](DEVLOG.md) — newest entry to oldest, scanning for what changed.
2. Read [`SYSTEM_VISION.md`](SYSTEM_VISION.md) and [`PHILOSOPHY.md`](PHILOSOPHY.md) — short, foundational.
3. Scan [`docs/bugs/`](docs/bugs/) for open notes.
4. State your role (see below).

## How to End a Session

1. Append to [`DEVLOG.md`](DEVLOG.md).
2. Run the Prophecy Rite (tests).
3. Rite of Preservation (git commit with multi-line message + Co-Authored-By).
4. Update any scroll that drifted from reality.

---

## The Six Roles

| Role | Owns |
|---|---|
| **Skald** | Naming, framing, philosophy → `PHILOSOPHY.md`, `SYSTEM_VISION.md`, vocabulary choices |
| **Cartographer** | Maps, orientation → `DATA_FLOW.md`, `DOMAIN_MAP.md` |
| **Architect** | Boundaries, refactor planning, interface design → `ARCHITECTURE.md`, `INTERFACE.md` |
| **Forge Worker** | Code, tests, implementation → `skein/core.py`, `skein/schema.py`, `skein/cli.py` |
| **Auditor** (Sólrún Hvítmynd) | Bug hunting, invariant verification → `docs/bugs/`, code review |
| **Scribe** | Documentation, changelogs → `DEVLOG.md` |

State the role at the start of any nontrivial task. Wrong role = wasted
effort.

---

## The Iron Laws

Drawn from canonical RULES.AI.md and applied specifically to Skein:

1. **Document before code.** Markdown first; implementation second.
2. **No pseudocode.** Markdown describes future behavior, never pseudo-Python.
3. **Never delete without asking.** Files, functions, modules, data — ask first.
4. **Full files only.** When showing edits in a planning doc, show the
   entire updated file.
5. **Additive bug fixing only.** Wrap, redirect, add a correct path
   alongside. Never delete to fix.
6. **No `print()` in library code.** Progress goes through the caller's
   `log=` callable. The CLI's Rich renderers are the only place `print`-
   adjacent output is appropriate.
7. **No absolute paths.** Use `pathlib.Path.parent.resolve()` patterns.
8. **No hardcoded config.** All knobs in `.env` (see `.env.example`).
9. **All Ollama/Postgres calls wrap in try/except.** Per-document failures
   in vocabulary discovery are logged and skipped, not raised.
10. **One LLM call per document, not per chunk.** The defining iron law of
    Skein.
11. **Type hints on all public signatures.**
12. **Methods under 50 lines.** Phase functions in `core.py` are the
    natural decomposition.
13. **The persist step is one transaction.** All-or-nothing.

---

## The Bug Hunt Rite

When you find something wrong:

1. **Create a Bug Note** in `docs/bugs/NNNN-slug.md`:
   ```markdown
   # Bug: <name>

   **Discovered:** YYYY-MM-DD by <role>

   ## Symptom
   ## Expected
   ## Suspected domains
   ## Invariant violated
   ## Reproduction
   ## Hypothesis
   ## Fix plan
   ```
2. **Invoke the Auditor** — Sólrún Hvítmynd. Ask: what invariant failed?
   what domain owns this? local or structural? what changed near this
   boundary? hidden coupling?
3. **Additive fix.** Never delete structure to fix.
4. **Verify against invariants** in [`PROJECT_LAWS.md`](PROJECT_LAWS.md).
5. **Update the Bug Note** with the resolution and lessons. Mark
   `STATUS: resolved`; do not delete.

---

## The Robustness Rite

- Every external call (Ollama, Postgres) in try/except with `log` warning
  on failure
- Per-document failures are skipped, not fatal — the build continues
- Type hints on every function signature
- No `print()` — `log=` callable in library, Rich in CLI
- Methods ≤ 50 lines; phase decomposition in `core.py` enforces this
- Cross-platform: regex `re.IGNORECASE` works the same everywhere;
  pathlib for any file I/O
- `.env.example` includes every env var the code reads
- The persist step is a single transaction — no partial state ever

---

## The Prophecy Rite (Testing)

Five layers — start at the **invariant** layer:

1. **Invariant** — `tests/test_invariants.py`: fingerprint determinism;
   schema idempotency; `evidence_chunk_ids` always non-empty; no writes to
   `chunks` or `documents`.
2. **Unit** — `tests/test_core.py`: `_parse_vocab_response` on malformed
   input; `_entity_regex` matching; `_normalize_name`; `build_edges` shape
   guarantees.
3. **Boundary** — `tests/test_schema.py`: `schema_apply` idempotent;
   dimension inference correct.
4. **Integration** — `tests/test_build.py`: full mini-build on a tiny
   in-memory or test-database corpus (when a test DB is available).
5. **Regression** — `tests/test_regression.py`: any specific bug from
   `docs/bugs/` reproduces and stays fixed.

---

## The Rite of Preservation (Commits)

```
<short subject under 70 chars>

<blank line>

<paragraph on the WHY — what changed and why it changed>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## The Rite of Return (Reverts)

`git revert <sha>` for anything pushed. Never `git reset --hard` on shared
history.

---

## Plundering Workflow

Skein has plundered no upstream code. If a future feature does, follow the
[canonical Plundering Workflow](https://github.com/hrabanazviking/Mythic-Engineering/blob/main/MYTHIC_ENGINEERING_PLUNDERING_WORKFLOW.md):
attribution in `LICENSE`/`NOTICE`/`THIRD_PARTY_NOTICES.md`; create
`docs/plunder/<UPSTREAM>_PLUNDER_MAP.md`; pass license, architecture,
security, integration review before merging.
