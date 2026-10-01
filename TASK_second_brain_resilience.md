# Task: Second-brain recovery and resilience

Date: 2026-09-30
Role: Sigrun, acting as Cartographer, Architect, Forge Worker, Auditor and Scribe.

## Authorization and target

Volmarr requested discovery, restoration, robustness improvements and GitHub pushes for the installed second brain. This task records that authorized scope before implementation.

## Existing system

The knowledge store contains 1234 documents and 49003 embedded chunks. Bifrost, Skein, Skry and the private local ingest watcher share PostgreSQL and Ollama. Bifrost is running but binds only to the tailnet interface; a plain page visit requires a token and does not offer a login form. Skein has 8586 entities and 26339 relations. All existing tests pass.

## Owning domain and planned work

Skein: Reject malformed embedding batches; sanitize vocabulary field types; skip invalid source vectors; preserve the existing graph on empty/failed discovery; isolate optional schema probes; bound database connections. Files: skein/core.py, skein/schema.py, tests/, INTERFACE.md and DEVLOG.md.

## Invariants

Preserve original corpus, user configuration and private files. Keep public response contracts and source ownership. Skry remains read-only. Skein owns only its derived tables. No secrets or corpus documents enter Git commits. No destructive schema changes or history rewrites. Keep failed inputs recoverable.

## Verification

Add regression tests for observed failure paths, run existing tests, validate service units, exercise live graph/search/Skry endpoints and inbox ingestion. Verify restart and outage recovery. Inspect staged diffs for accidental data/credentials before committing and pushing.

## Sequence

1. Preserve local sources, configs and database backup.
2. Commit and push this task document.
3. Implement the scoped fixes and regression tests.
4. Deploy locally and verify behavior.
5. Update architecture/interface/devlog documentation and push verified changes.

## Completed verification

2026-09-30: 37 tests pass, including malformed vocabulary fields, incomplete and
nonfinite embedding batches, nonretryable HTTP errors, empty build preservation
and blocked cosine edges compared with the dense reference. Ruff passes for
changed core/schema/test modules. The installed Bifrost environment was rebuilt
with these sources. Its existing entity graph remains intact; no destructive
schema migration or full production rediscovery was performed.
