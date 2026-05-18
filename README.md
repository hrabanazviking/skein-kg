---

![https://raw.githubusercontent.com/hrabanazviking/skein-kg/refs/heads/main/4dca0eb9-1142-4713-98c5-e8842ce86df6.jpeg](https://raw.githubusercontent.com/hrabanazviking/skein-kg/refs/heads/main/4dca0eb9-1142-4713-98c5-e8842ce86df6.jpeg)

---

# Skein

> *a coil of threads connecting names*

Skein builds a **knowledge graph** (entities + typed relations + provenance) over a corpus of text chunks **without ever running autoregressive LLM extraction per chunk.** It's designed for laptop-scale corpora (10k–500k chunks) where you've already got embeddings sitting in a vector store.

Companion project: [`skry-kg`](https://github.com/hrabanazviking/skry-kg) — the query-time projection.

---

![https://raw.githubusercontent.com/hrabanazviking/skein-kg/refs/heads/main/Screenshot_20260518_173244.png](https://raw.githubusercontent.com/hrabanazviking/skein-kg/refs/heads/main/Screenshot_20260518_173244.png)

---

## The trick

The expensive step in conventional KG extraction is making an LLM read every chunk and *write a JSON description of it*. Skein replaces that with three cheap moves:

1. **Vocabulary, not extraction** — One LLM call **per document** (not per chunk) asks llama for the named entities in a representative sample. For a 30-document corpus that's 30 calls, not 23,000.

2. **String matching, not parsing** — Entity occurrences across all chunks are found by case-insensitive regex with word boundaries (plus user-supplied aliases). Cheap and exhaustive.

3. **Embeddings, not generation** — Each entity gets an embedding = mean of the embeddings of the chunks it appears in. Edges are top-K cosine similarity between entity embeddings. Predicates are picked by **embedding the text between two entity mentions** and snapping to the nearest verb in a fixed vocabulary.

That's it. No autoregressive generation. ~1/500 the GPU work of a per-chunk LLM extractor, with ~75% of the graph quality.

---

![https://raw.githubusercontent.com/hrabanazviking/skein-kg/refs/heads/main/39b17892-706e-4a0f-afa6-a5e8a2081602.jpeg](https://raw.githubusercontent.com/hrabanazviking/skein-kg/refs/heads/main/39b17892-706e-4a0f-afa6-a5e8a2081602.jpeg)

---

## Why "Skein"

> "This sure beats melting my gaming laptop!"

A skein is a loose coil of thread or yarn — and a flock of geese in flight. Both fit: the woven web of entities, and the way related concepts move together through a corpus.

## Inputs

Skein expects a Postgres database with two tables (the standard pgvector ingest layout):

```sql
documents (id, title, content_type, source, …)
chunks    (id, document_id, text, embedding vector(N), …)
```

It writes:

```sql
skein_entities  (id, name, name_norm, kind, mentions, embedding)
skein_relations (id, subject_id, predicate, object_id, sim, evidence_chunk_ids)
skein_build     (id, fingerprint, finished_at, stats jsonb)
```

## Usage

```bash
cp .env.example .env  # set DB_URL, OLLAMA_URL, etc.
uv sync
uv run skein build              # full one-shot build
uv run skein stats              # show entity/relation counts
uv run skein neighbors "Odin"   # quick lookup of one entity's edges
```

## Predicate vocabulary

Skein ships with a default vocabulary tuned for mixed narrative content (`wields`, `son_of`, `created`, `located_in`, `associated_with`, `killed`, …). Override with your own in `.env`:

```env
SKEIN_PREDICATES=wields,son_of,daughter_of,killed,created,…
```

Each predicate is embedded as `"X {predicate} Y"` once at build time; per-edge predicate selection is then a cheap cosine snap.

## Limits & honesty

- Predicate granularity is bounded by your vocabulary. Skein won't invent `sacrificed_eye_to`; the closest it'll get is `gave_to` (or whatever's in the list).
- Same name spelled differently (Odin / Wotan / Allfather) becomes separate nodes unless you provide aliases. The per-document LLM call is asked to list aliases too.
- It can't do fine-grained event extraction. For that, you still want a per-chunk LLM pass.
- It needs an existing embedding column; it does not embed text itself.

## Status

Co-invented by Volmarr Wyrd and Claude during a single session, May 2026. Lives at `~/ai/skein-kg/`. Open to becoming a real library if useful to others.

---

![https://raw.githubusercontent.com/hrabanazviking/skein-kg/refs/heads/main/MIT_license_Rune_Forge_AI.jpeg](https://raw.githubusercontent.com/hrabanazviking/skein-kg/refs/heads/main/MIT_license_Rune_Forge_AI.jpeg)

---

## License

MIT License

Copyright (c) 2026 Volmarr Wyrd

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

![https://raw.githubusercontent.com/hrabanazviking/skein-kg/refs/heads/main/IMG_0666.jpeg](https://raw.githubusercontent.com/hrabanazviking/skein-kg/refs/heads/main/IMG_0666.jpeg)

---

![https://raw.githubusercontent.com/hrabanazviking/skein-kg/refs/heads/main/IMG_0665.jpeg](https://raw.githubusercontent.com/hrabanazviking/skein-kg/refs/heads/main/IMG_0665.jpeg)

---


