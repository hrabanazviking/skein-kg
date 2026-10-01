# Skein technical manual

Source and CLI verified on 2026-10-01. Skein builds a derived entity/relation graph
over existing documents and chunk embeddings. It creates/updates `skein_*` tables;
it does not ingest or overwrite the source `documents`/`chunks` corpus.
For the connected stack, see [the system manual](../ingest-viewer/SECOND_BRAIN_MANUAL.md).

## 1. What a build does

1. Infer/validate the embedding dimension and create missing derived tables/indexes.
2. Discover names, kinds and aliases using a representative document sample and
   a chat-model vocabulary call per document, with bounded retries.
3. Find entity mentions across chunks using Unicode-aware name/alias matching.
4. Average stored chunk vectors into entity embeddings; build top-K similarity edges.
5. Embed nearby mention spans and choose predicates from the configured vocabulary.
6. Check the source fingerprint and transactionally replace the derived entity/
   relation rows, then append build metadata.

This avoids an autoregressive extraction call for every chunk. It still uses a
chat model for vocabulary and an embedding model for relation-span snapping.
Typed edges are model-assisted interpretations, not guaranteed factual triples.
Use their source chunk IDs as evidence.

## 2. Installation and private settings

Requires Python 3.13+, uv, PostgreSQL/pgvector and existing compatible nonempty
chunk vectors, plus an embedding and chat model on Ollama. Keep the checkout
alongside Bifröst if using its **BUILD SKEIN** integration.

```bash
cd "$HOME/ai/skein-kg"
cp .env.example .env
chmod 600 .env
uv sync --frozen
```

Copy only on a new installation; preserve an existing configured dotenv.
The CLI loads this root `.env`; the process environment takes precedence.

| Variable | Default/example | Effect |
|---|---|---|
| `SKEIN_DB_URL` | `postgresql:///knowledge` | Source reads and derived-table writes/schema creation |
| `SKEIN_OLLAMA_URL` | `http://localhost:11434` | Intended embedding/chat server |
| `SKEIN_EMBED_MODEL` | `nomic-embed-text` | Same vector space as stored chunks |
| `SKEIN_CHAT_MODEL` | `llama3.2:3b` | Entity vocabulary discovery |
| `SKEIN_EDGE_TOP_K` | `6` | Nearest neighbor edges per entity |
| `SKEIN_EDGE_MIN_SIM` | `0.55` | Similarity threshold |
| `SKEIN_PREDICATE_WINDOW` | `120` | Mention span window for predicate selection |
| `SKEIN_EDGE_BLOCK_SIZE` | `256` | Row-block size for memory-bounded cosine calculation |
| `SKEIN_DB_CONNECT_TIMEOUT` | `5` | Connection setup timeout in seconds |
| `SKEIN_PREDICATES` | unset | Comma-separated custom predicate vocabulary |

This is an owner/operator build role. The restricted API-ingest DB account cannot
create/replace derived graphs and must not be used here. Do not expose direct DB
access through the legacy tailnet setup script merely to authorize outside AIs;
give those AIs scoped Bifröst read/append keys instead.

## 3. Run and inspect a build

Back up first when operating an important corpus. Pause or finish ingestion before
starting to keep the source fingerprint stable, and run one build at a time:

```bash
uv run --frozen skein --help
uv run --frozen skein build
uv run --frozen skein stats
uv run --frozen skein neighbors "Odin" --limit 20
```

Explicit tuning example:

```bash
uv run --frozen skein build --top-k 6 --min-sim 0.55 --window 120
```

`stats` reports entity/relation counts, kind/predicate distributions and frequently
mentioned names. `neighbors` gives direction, predicate, related entity, similarity
and sample evidence chunk IDs. A missing normalized name returns a no-match message
and nonzero exit status. Name matching is normalized/case-insensitive, not a fuzzy
spelling or arbitrary alias-resolution endpoint.

More neighbors or a lower threshold can create a denser, noisier graph. Increasing
row-block size may increase peak memory without improving semantic quality.
Choose conservative settings and compare evidence, not just edge counts.

## 4. Tables and persistence guarantees

| Table | Stored derived knowledge |
|---|---|
| `skein_entities` | Name/normalized name, kind, mentions and entity vector |
| `skein_entity_chunks` | Entity-to-source-chunk evidence links |
| `skein_relations` | Subject, predicate, object, similarity and evidence chunk IDs |
| `skein_build` | Build fingerprint, completion time and statistics |

The previous entity/relation rows are replaced in one transaction only after
usable computation completes. Empty usable discovery or a detected source-count/
max-ID change aborts before replacement. Persistence failure rolls back that
transaction. Source tables are not deleted or modified by the build.

The fingerprint is count/max-ID based; it is not a full source-content hash and
does not detect every in-place edit. Avoid concurrent in-place source edits. Skein 0.1.1 holds a PostgreSQL session
advisory lock across the full build, shared by CLI and Bifröst-launched builds.
A second builder on the same database refuses to run. The lock releases when its
session ends, including a crashed process. This cooperative lock does not constrain
older versions or unrelated SQL tools.

Entity/relation IDs can change after a rebuild. Keep durable citations as source
chunk/document IDs rather than bookmarking a derived entity ID as permanent.
Per-document vocabulary failures are counted, including malformed response JSON,
wrong entity-list shape and entirely invalid entity records. A valid empty list is
accepted. By default more than 10% failed documents aborts before graph publication.
Set `SKEIN_MAX_FAILED_DOCUMENTS_PERCENT` to a finite value from 0 to 100 to change
that ceiling; reducing it strengthens completeness requirements. A threshold of
100 intentionally permits severe missing coverage and should not be used to hide
an outage. Coverage counts/percentage are stored in `skein_build.stats.discovery`.
Inspect warnings and coverage before treating a completed build as full coverage. Old `skein_build` records remain history, not independent snapshots of
each prior graph's entity rows.

## 5. Use from Bifröst

Open the owner viewer, choose **BUILD SKEIN**, wait for completion and inspect its
status/counts. Switch to **ENTITIES** to see the 3D graph. Building the `skein_*`
tables and constructing their browser layout are separate stages; the layout can
still return `202` pending after the database graph has finished.

Bifröst launches the CLI from this sibling checkout, so its `.env` must remain
configured. A reader can call `/api/skein/status` and `/api/skein/graph`; initiating
`/api/skein/build` requires owner `admin`. Outside AI append keys do not authorize
expensive global rebuilds.

Ingestion does not automatically rebuild Skein on every append. Schedule a manual
owner build after a batch of new sources or when you need refreshed vocabulary.
Skry can retrieve new chunks immediately, but its vocabulary-filtered names may
still reflect the last Skein build.

## 6. Python API

The main exports are `schema_apply`, `build_skein` and `neighbors_of`. A complete
configured example, run from this project root:

```python
import json
import logging
import os
import sys
from dotenv import dotenv_values
from skein import build_skein, neighbors_of

logging.basicConfig(level=logging.INFO)
config = {**dotenv_values(".env"), **os.environ}
raw_predicates = config.get("SKEIN_PREDICATES", "")
predicates = [p.strip() for p in raw_predicates.split(",") if p.strip()] or None
stats = build_skein(
    config["SKEIN_DB_URL"],
    ollama_url=config["SKEIN_OLLAMA_URL"],
    embed_model=config["SKEIN_EMBED_MODEL"],
    chat_model=config["SKEIN_CHAT_MODEL"],
    predicates=predicates,
    top_k=6,
    min_sim=0.55,
    window=120,
    log=logging.getLogger("skein.operator").info,
)
result = neighbors_of(config["SKEIN_DB_URL"], "Odin", limit=20)
json.dump({"stats": stats, "neighbors": result}, sys.stdout, ensure_ascii=False, indent=2)
```

This example intentionally performs a build; use only `neighbors_of` for a
read-only lookup. The library receives DB/model arguments explicitly and does not
load `.env` itself. `schema_apply` creates derived schema but requires existing
usable vectors to infer dimension. It is not source-schema initialization.

## 7. Vocabulary, language and interpretation

The default vocabulary/prompt is tuned for English narrative sources. Norse
Unicode names can match correctly, but this is not general semantic entity
resolution. Similar names can become separate nodes; discovered aliases help
mention matching but do not guarantee a complete identity merge.

Use comma-separated `SKEIN_PREDICATES` values suitable for your domain/language.
Skein chooses among that vocabulary; it does not invent an unlimited precise
event predicate. Non-English discovery may need a deliberately adapted prompt
and new evaluation; changing a setting alone does not guarantee equivalent
coverage. Representative document samples can miss entities deep in a large file.
Preserve originals and read evidence for high-stakes interpretations.

## 8. Troubleshooting, backups and tests

| Failure | Action |
|---|---|
| Cannot infer vector dimension | Ingest compatible chunks first; inspect nonnull vectors/schema |
| Model missing or unreachable | Check configured Ollama server and both model names |
| Bad/incomplete embeddings | Inspect model response and matching source model; validation refuses invalid vectors |
| No usable entities | Read discovery/mention warnings; previous graph is preserved |
| Corpus changed during build | Finish/pause source writes, then rerun once |
| Very slow vocabulary phase | Number/size of documents, chat model, GPU load and per-document retry logs |
| Unexpectedly few entities | Partial discovery failures, sampling, vocabulary/language or name matching |
| Empty Bifröst entity view | Derived DB build and separate layout status; verify sibling config |

Use the [stack backup/restore](../ingest-viewer/SECOND_BRAIN_MANUAL.md#back-up-and-verify).
A full database dump includes derived tables. Rebuilding can replace them but
requires functioning models and can produce different vocabulary/predicates.

```bash
uv run --frozen pytest -q
git status --short
```

See [INTERFACE.md](INTERFACE.md), [skein/README_AI.md](skein/README_AI.md),
[ARCHITECTURE.md](ARCHITECTURE.md) and [DEVLOG.md](DEVLOG.md) for contracts/history.

## 10. Build recovery boundaries (0.1.1)

- `SKEIN_DB_CONNECT_TIMEOUT` defaults to 5 seconds for the build-lock session.
- `SKEIN_MAX_FAILED_DOCUMENTS_PERCENT` defaults to 10; settings are validated.
- The advisory lock namespace is configured in `skein/build.defaults.json`.
  All cooperating installations must use the same namespace.
- Lost locking sessions refuse publication. Empty usable entities, changed source
  fingerprints, failed embeddings or excessive discovery failures preserve the
  previous graph. Correct the cause and start a deliberate new build.
- Replacement of derived rows and addition of build history remain one atomic
  transaction. No source schema/row is repaired or deleted by a failed build.
- Bifröst uses the build ID plus source fingerprint for its v2 entity cache and
  reads entity/relation rows in one repeatable-read snapshot. Old cached layouts
  are kept while a replacement build is in progress.

Run `uv run --frozen pytest -q` from the Skein root for fault and invariant tests.
Bifröst also provides opt-in isolated-database tests for concurrent build locks.
Do not run a full production rebuild just to check that locking works.
