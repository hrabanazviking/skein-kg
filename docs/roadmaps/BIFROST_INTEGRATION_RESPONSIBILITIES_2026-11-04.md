# Skein: Incremental Graph and Resumable Inference

**Date:** 2026-11-04  
**Repository:** `hrabanazviking/skein-kg`  
**Implementation status:** Roadmap only; no application code modified.

## Relationship to the master roadmap

- **Canonical roadmap:** https://github.com/hrabanazviking/bifrost-viewer/blob/main/docs/roadmaps/BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md
- **Local full copy:** [BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md](BIFROST_SECOND_BRAIN_MASTER_EXPANSION_ROADMAP_2026-11-04.md)
- **Status:** Proposed work, not existing functionality. Confirm actual current installed state and protect existing data before writing code.
- **Ownership:** Bifröst Viewer coordinates the Second Brain. Skein and Skry own their APIs. Integrations must use documented, authenticated contracts and cannot assume direct PostgreSQL access.
- **Security:** Public Markdown only. No actual keys, OAuth client secrets, vault values, database passwords, user documents, personal account identifiers, logs, private state paths or private URLs.
- **Compatibility:** Preserve existing code behavior, published interfaces, licenses and attribution. Changes should be opt-in, reversible and regression-tested.

## Goal

Turn the existing efficient full-build algorithm into a versioned, checkpointed, resource-aware incremental pipeline while preserving the original algorithm for repeatable validation.

## Repository-specific engineering responsibilities

1. Preserve `build_skein()` and its verified full-build semantics. Introduce new public APIs rather than invasive calls from Bifröst.
2. Separate vocabulary extraction, mention discovery, embedding aggregation, candidate edges, predicate snapping, validation, staging and publication into independently resumable units.
3. Persist per-document extraction caches keyed by content, sampling, model/prompt and schema versions; invalidate only affected dependencies.
4. Stage immutable graph generations and publish atomically; preserve prior known-good graphs and a rollback pointer.
5. Support cooperative pause/resume, quiet-time resource release and crash-safe checkpoints at document/batch boundaries.
6. Offer local/optional cloud provider interfaces that preserve current embedding-vector-space identity; validate structured extraction and track billed usage.
7. Introduce evidence-aware entity identity, relation polarity and confidence/status, with optional deeper claim extraction.

## Engineering and security gates

- [ ] Adding one new document does not rerun model vocabulary discovery on unchanged documents.
- [ ] SIGKILL during build and an actual restart preserve finished checkpoints and the previous published graph.
- [ ] Local extraction remains compatible with 6 GiB VRAM; in-flight work respects cost and rate caps.
- [ ] Incremental and full-build graphs agree within a documented quality tolerance on a gold fixture.
- [ ] No new mandatory dependency on OpenRouter, Kista, or another cloud service.

## Delivery sequence

1. Read this repository's own architectural rules, domain boundaries and current source before editing.
2. Audit installed and unpublished development work; never assume a feature is absent simply because it is missing from the current public default branch.
3. Design a versioned optional integration through published API contracts; preserve baseline behavior.
4. Implement synthetic fixtures, unit tests, integration tests, timeouts and permission checks.
5. Test disconnection, false/stale results, recovery and security canaries.
6. Document capability level and deployment directions without secrets; require owner approval before live rollout.

**Canonical authority:** The primary Bifröst Viewer roadmap above resolves conflicts; individual source code and verified deployed evidence establish what is actually implemented.

