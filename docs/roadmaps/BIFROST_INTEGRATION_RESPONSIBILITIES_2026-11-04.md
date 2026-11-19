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


## 2026-11-19 superseding implementation guidance

The owner expressly confirms that the November 4 incremental design supersedes the older prohibition. The updated [PROJECT_LAWS](../../PROJECT_LAWS.md) and [PHILOSOPHY](../../PHILOSOPHY.md) now make incremental updates the **target normal path**. Do not rewrite source documents or require `skein build` after every source/connection update. Keep the existing full-build `build_skein()` API functioning while new `incremental_v2` stages are implemented and tested.

Priority tests: ten additions change only delta-dependent extraction/relations; edit/retraction removes stale evidence but preserves unrelated facts; an unchanged source yields zero inference calls; no DB rebuild on a new API client connection; interrupts preserve published graph and resume checkpoints. Vision-derived captions should arrive via Ingest as sourced derived evidence; visual embeddings and raw image assets belong to Bifröst's multimodal adapters, not forced into Skein's original text vector space. Use separate graph derivatives only when lineage and model identity are proved.

**Canonical new requirements:** [Bifröst 2026-11-19 additive multimodal and visual lore roadmap](https://github.com/hrabanazviking/bifrost-viewer/blob/docs/second-brain-incremental-multimodal-gateway-2026-11-19/docs/roadmaps/SECOND_BRAIN_ADDITIVE_INCREMENTAL_MULTIMODAL_GATEWAY_2026-11-19.md). After its canonical merger, update the link to the main-branch document. No deployment is implied by this roadmap change.

## Managed raw folder categories and copy/move reconciliation (2026-11-19)

The user-approved [managed raw library design](https://github.com/hrabanazviking/bifrost-viewer/blob/docs/second-brain-incremental-multimodal-gateway-2026-11-19/docs/roadmaps/SECOND_BRAIN_MANAGED_RAW_LIBRARY_FOLDERS_2026-11-19.md) makes physical folder ancestry part of provenance, while content hashes permit reuse of compatible derived computation.

- Ingest owns source instance IDs, physical path history, category ancestry and canonical document versions; **Skein does not crawl folders or alter raw files**.
- Treat a path-only move or folder reclassification as a cheap category-edge delta, not an LLM/embedding/whole-graph operation.
- If the same bytes are copied to another folder, represent a second source/location and its category evidence without duplicating content-level extraction or embeddings.
- If an existing source is edited, retract obsolete per-source evidence, reuse compatible unchanged chunks and rerun only changed material and affected entities/neighbors.
- Preserve multiple surviving locations when the original copy remains. Do not infer a move from identical bytes alone. Root unavailability must never trigger an automatic data deletion.
- Preserve provenance, source revision and content/model-version identities in staged graph generations. The prior published generation remains usable until the delta passes validation.
- Tests must cover duplicate across folders, relocation without re-embedding, independent change to a copied file, verified deletion, disconnected root and graph rollback.

**No running implementation is claimed by updating this task document.**
