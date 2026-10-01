# Task: durable Skein build boundaries

Date: 2026-10-01. Part of Volmarr's authorized ingestion/build recovery work.

Observed risks: independent CLI builds can compute/replace derived tables
concurrently; extensive vocabulary-call failures can still publish a greatly
reduced graph; Bifröst uses a source-only fingerprint for layouts even when a
new build produces different entity IDs for the same corpus.

Plan: acquire a database session advisory lock for a complete build; keep source
tables read-only; track successful/failed document discovery and refuse publication
above a configurable failure threshold; record coverage in build metadata while
preserving the public build signature. Bifröst will use the build generation ID
and read entity/edge rows in one repeatable-read snapshot. Preserve the previous
derived graph on failure and test concurrency/coverage boundaries without an
expensive rebuild of the live knowledge base.

No source schema migration, source deletion, per-chunk LLM extraction or new
remote AI administrative permission is authorized by this implementation.
