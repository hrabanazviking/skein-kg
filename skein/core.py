"""Skein core algorithm: weave entities + typed relations from embeddings.

Pipeline
--------
1. For each document, ask the LLM once for the named entities (with optional
   aliases + kinds). Total LLM calls = number of documents, not chunks.
2. String-match those entities across all chunks (regex with word boundaries,
   case-insensitive, alias-aware). Build entity → chunk_ids map.
3. Entity embedding = mean of embeddings of chunks it appears in (L2-normalized).
4. Top-K cosine similarity between entity embeddings = candidate edges.
5. For each edge, embed the text between mentions in co-occurrence chunks
   (windowed). Snap the mean of those window-embeddings to the nearest predicate
   from a fixed vocabulary.

The only LLM autoregressive work is step 1 — and only one call per document.
"""
from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict
from typing import Callable, TypedDict

import httpx
import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from skein.build_guard import Vocabulary, build_lock, coverage, ensure_lock


def _connect(db_url: str) -> psycopg.Connection:
    return psycopg.connect(db_url, connect_timeout=int(os.getenv("SKEIN_DB_CONNECT_TIMEOUT", "5")))


def _validated_embeddings(payload: object, expected: int) -> np.ndarray:
    """Refuse partial, ragged, zero or nonfinite vectors before graph work."""
    try:
        vectors = np.asarray(payload, dtype=np.float32)
    except (TypeError, ValueError) as exc:
        raise ValueError("embedding service returned malformed vectors") from exc
    if (vectors.ndim != 2 or vectors.shape[0] != expected or not vectors.shape[1]
            or not np.isfinite(vectors).all() or not np.all(np.any(vectors, axis=1))):
        raise ValueError("embedding service returned invalid or incomplete vectors")
    return vectors


def _unit_rows(vectors: np.ndarray) -> np.ndarray:
    values = np.asarray(vectors, dtype=np.float64)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or not np.all(norms > 0):
        raise ValueError("Cannot normalize invalid embedding vectors")
    return (values / norms).astype(np.float32)


# docs/bugs/0004: stable shape of build_skein's return value.
class SkeinBuildStats(TypedDict):
    n_entities: int
    n_mentions: int
    n_edges: int
    build_seconds: float


# ─── default predicate vocabulary (generic narrative; override via env) ───
DEFAULT_PREDICATES = [
    "associated_with", "part_of", "located_in", "born_in", "lived_in",
    "ruled", "member_of", "leader_of", "married_to", "parent_of", "child_of",
    "sibling_of", "ally_of", "enemy_of", "killed", "defeated", "served",
    "wields", "created", "destroyed", "gave_to", "received_from",
    "traveled_to", "fought_at", "named_after", "depicted_as", "worshipped_as",
    "synonym_of", "described_as",
]


SYSTEM_VOCAB = (
    "You are an entity vocabulary extractor. Given excerpts from ONE document, "
    "list the distinct named entities that recur or that the document is clearly about. "
    "Skip pronouns, generic nouns, and one-off mentions. Use Title Case. "
    "Return STRICT JSON only (no preamble, no code fences) with this schema:\n"
    '{"entities":[{"name": str, "kind": str, "aliases": [str]}]}\n'
    "Kinds: person, place, deity, artifact, group, work, concept, event, other.\n"
    "Aliases: alternative spellings/titles for the same entity. Include them when known.\n"
    "Cap the list at 60 entities."
)


# docs/bugs/0008: retry transient HTTP/JSON failures with exponential backoff.
def _retry(fn: Callable, *, attempts: int = 3, base_delay: float = 2.0):
    """Call fn() with up to `attempts` retries on transient failures."""
    for i in range(attempts):
        try:
            return fn()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                if exc.response.status_code not in (408, 429):
                    raise
            if i == attempts - 1:
                raise
            time.sleep(base_delay * (2 ** i))


def _ollama_chat(client: httpx.Client, url: str, model: str, system: str,
                 user: str, *, max_tokens: int = 1200) -> str:
    def _call():
        r = client.post(f"{url}/api/chat", json={
            "model": model, "stream": False, "format": "json",
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "options": {"num_predict": max_tokens, "temperature": 0.1},
        }, timeout=300)
        r.raise_for_status()
        return r.json()["message"]["content"]
    return _retry(_call)


def _ollama_embed(client: httpx.Client, url: str, model: str,
                  texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 1), dtype=np.float32)
    out: list[list[float]] = []
    # Batch — nomic-embed has no hard cap but keep groups small for memory
    for i in range(0, len(texts), 32):
        batch = texts[i:i + 32]
        def _call():
            r = client.post(f"{url}/api/embed",
                            json={"model": model, "input": batch},
                            timeout=300)
            r.raise_for_status()
            return r.json()["embeddings"]
        vectors = _validated_embeddings(_retry(_call), len(batch))
        if out and len(out[0]) != vectors.shape[1]:
            raise ValueError("embedding dimensions changed between batches")
        out.extend(vectors.tolist())
    return np.asarray(out, dtype=np.float32)


def _normalize_name(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()).lower()


def _entity_regex(name: str) -> re.Pattern:
    r"""Compile a Unicode-aware regex for an entity name (and its aliases).

    docs/bugs/0001: Python's ``\b`` word boundary is ASCII-only. For Norse
    content (Mímir, Þórr, Þrúðr, Ðagr) and any non-Latin alphabet the
    boundary fails to match consistently. We use explicit Unicode-aware
    lookarounds with ``\w`` (which IS Unicode-aware under ``re.UNICODE``,
    on by default in Python 3) so the boundary treats letters of any
    script identically.
    """
    parts = [re.escape(p) for p in name.split() if p]
    if not parts:
        return re.compile(r"$^")  # never matches
    body = r"\s+".join(parts)
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE | re.UNICODE)


def _parse_vocab_response(raw: str, *, strict: bool = False) -> list[dict]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        if strict:
            raise ValueError("Missing vocabulary JSON")
        return []
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        if strict:
            raise ValueError("Malformed vocabulary JSON") from None
        return []
    ents = d.get("entities") if isinstance(d, dict) else None
    if strict and not isinstance(ents, list):
        raise ValueError("Vocabulary entities must be a list")
    if strict and ents and not any(_sanitize_entity(entity) for entity in ents):
        raise ValueError("Vocabulary response contains no valid entity records")
    return ents if isinstance(ents, list) else []


def _sanitize_entity(entity: object) -> dict | None:
    """Model JSON can be syntactically valid while its field types are wrong."""
    if not isinstance(entity, dict) or not isinstance(entity.get("name"), str):
        return None
    name = entity["name"].strip()
    if not name or len(name) > 100:
        return None
    kind = entity.get("kind")
    kind = kind.strip().lower()[:32] if isinstance(kind, str) else "other"
    aliases = entity.get("aliases")
    aliases = aliases if isinstance(aliases, list) else []
    aliases = sorted({a.strip() for a in aliases if isinstance(a, str) and a.strip() and len(a) <= 100})
    return {"name": name, "kind": kind or "other", "aliases": aliases}


def _merge_vocabulary(vocab: dict, entities: list[dict]) -> tuple[int, int]:
    accepted, dropped = 0, 0
    for entity in entities:
        entity = _sanitize_entity(entity)
        if entity is None:
            dropped += 1
            continue
        key = _normalize_name(entity["name"])
        if key in vocab:
            vocab[key]["aliases"] = sorted({*vocab[key]["aliases"], *entity["aliases"]})
        else:
            vocab[key] = entity
        accepted += 1
    return accepted, dropped


def discover_vocabulary(
    db_url: str, *, ollama_url: str, chat_model: str,
    samples_per_doc: int = 6, sample_chars: int = 1800,
    log: Callable[[str], None] | None = None,
) -> list[dict]:
    """One LLM call per document → list of {name, kind, aliases}.

    docs/bugs/0003: `log` is typed as `Callable[[str], None] | None`.
    docs/bugs/0006: per-doc accepted/dropped counts are reported via `log`.
    """
    with _connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("SELECT id, title FROM documents ORDER BY id")
        docs = cur.fetchall()

    vocab: dict[str, dict] = {}
    failed = 0
    with httpx.Client() as client, _connect(db_url) as conn:
        for doc_id, title in docs:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT text FROM chunks WHERE document_id = %s "
                    "ORDER BY (chunk_index %% 7), chunk_index LIMIT %s",
                    (doc_id, samples_per_doc),
                )
                samples = [r[0][:sample_chars] for r in cur.fetchall()]
            if not samples:
                failed += 1
                continue
            user = (f"Document title: {title}\n\nExcerpts:\n\n" +
                    "\n\n---\n\n".join(samples) + "\n\nJSON:")
            try:
                raw = _ollama_chat(client, ollama_url, chat_model, SYSTEM_VOCAB, user)
                ents = _parse_vocab_response(raw, strict=True)
            except Exception as e:
                failed += 1
                if log:
                    log(f"  doc {doc_id} '{title}': vocab call failed — {e}")
                continue
            accepted, dropped = _merge_vocabulary(vocab, ents)
            if log:
                log(f"  doc {doc_id} {title!r}: +{accepted} (dropped {dropped} malformed)")
    return Vocabulary(vocab.values(), len(docs), failed)


def find_mentions(db_url: str, vocab: list[dict]) -> dict[str, set[int]]:
    """For each canonical entity name, set of chunk_ids it appears in (incl. aliases)."""
    patterns: dict[str, list[re.Pattern]] = {}
    for ent in vocab:
        names = [ent["name"], *ent["aliases"]]
        patterns[_normalize_name(ent["name"])] = [_entity_regex(n) for n in names]

    mentions: dict[str, set[int]] = defaultdict(set)
    with _connect(db_url) as conn, conn.cursor(name="chunkscan") as cur:
        cur.itersize = 2000
        cur.execute("SELECT id, text FROM chunks")
        for cid, text in cur:
            for key, pats in patterns.items():
                if any(p.search(text) for p in pats):
                    mentions[key].add(cid)
    return mentions


def compute_entity_embeddings(
    db_url: str, mentions: dict[str, set[int]],
) -> dict[str, np.ndarray]:
    """Entity embedding = mean of L2-normalized chunk embeddings, then re-normalized."""
    all_chunk_ids = sorted({c for cs in mentions.values() for c in cs})
    if not all_chunk_ids:
        return {}
    chunk_embs: dict[int, np.ndarray] = {}
    with _connect(db_url) as conn:
        register_vector(conn)
        with conn.cursor(name="embscan") as cur:
            cur.itersize = 1000
            cur.execute("SELECT id, embedding FROM chunks WHERE id = ANY(%s) AND embedding IS NOT NULL",
                        (all_chunk_ids,))
            for cid, emb in cur:
                v = np.array(emb, dtype=np.float32)
                if v.ndim != 1 or not v.size or not np.isfinite(v).all() or not np.any(v):
                    continue
                n = np.linalg.norm(v.astype(np.float64))
                if n > 0:
                    v = v / n
                chunk_embs[cid] = v
    out: dict[str, np.ndarray] = {}
    for key, chunk_ids in mentions.items():
        vs = [chunk_embs[c] for c in chunk_ids if c in chunk_embs]
        if not vs:
            continue
        m = np.mean(vs, axis=0)
        n = np.linalg.norm(m.astype(np.float64))
        if np.isfinite(n) and n > 0:
            out[key] = (m / n).astype(np.float32)
    return out


def build_edges(
    keys: list[str], embeddings: np.ndarray, *,
    top_k: int, min_sim: float,
) -> list[tuple[int, int, float]]:
    n = len(keys)
    if top_k < 1 or not np.isfinite(min_sim):
        raise ValueError("top_k must be positive and min_sim must be finite")
    if n < 2:
        return []
    k = min(top_k, n - 1)
    block_size = max(1, int(os.getenv("SKEIN_EDGE_BLOCK_SIZE", "256")))
    out: dict[tuple[int, int], float] = {}
    for start in range(0, n, block_size):
        stop = min(n, start + block_size)
        sim = embeddings[start:stop] @ embeddings.T
        sim[np.arange(stop - start), np.arange(start, stop)] = -1.0
        top_idx = np.argpartition(-sim, kth=k - 1, axis=1)[:, :k]
        for local, neighbors in enumerate(top_idx):
            i = start + local
            for j in neighbors:
                j = int(j)
                score = float(sim[local, j])
                if score < min_sim or i == j:
                    continue
                a, b = sorted((i, j))
                out[(a, b)] = max(score, out.get((a, b), -1.0))
    return [(a, b, score) for (a, b), score in out.items()]


# ─── snap_predicates: phase helpers (docs/bugs/0009) ────────────────────────

def _embed_predicate_vocabulary(
    predicates: list[str], *, ollama_url: str, embed_model: str,
) -> np.ndarray:
    """Embed each predicate via a fixed template and return L2-normalized."""
    with httpx.Client() as client:
        pred_emb = _ollama_embed(
            client, ollama_url, embed_model,
            [f"is {p.replace('_', ' ')}" for p in predicates],
        )
    return _unit_rows(pred_emb)


def _cooccurrence_chunks_per_edge(
    edges: list[tuple[int, int, float]],
    keys: list[str], mentions: dict[str, set[int]],
    cap: int = 8,
) -> dict[tuple[int, int], list[int]]:
    """For each edge, return the (capped, sorted) list of chunks where both
    endpoints are mentioned."""
    out: dict[tuple[int, int], list[int]] = {}
    for a, b, _ in edges:
        common = sorted(mentions[keys[a]] & mentions[keys[b]])[:cap]
        if common:
            out[(a, b)] = common
    return out


def _fetch_chunk_texts(db_url: str, chunk_ids: list[int]) -> dict[int, str]:
    """One DB round-trip for all the chunk texts needed by predicate snap."""
    if not chunk_ids:
        return {}
    needed = sorted(set(chunk_ids))
    with _connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("SELECT id, text FROM chunks WHERE id = ANY(%s)", (needed,))
        return {cid: t for cid, t in cur.fetchall()}


def _closest_mention_pair_span(
    text: str, pat_a: re.Pattern, pat_b: re.Pattern, window: int,
) -> str | None:
    """Find the smallest-gap mention pair in `text`; return the surrounding
    text-between-mentions span (with a small ±window/4 cushion) or None."""
    ma = list(pat_a.finditer(text))
    mb = list(pat_b.finditer(text))
    if not ma or not mb:
        return None
    best: tuple[int, int, int] | None = None
    for x in ma:
        for y in mb:
            if x.start() == y.start():
                continue
            if x.end() <= y.start():
                lo, hi = x.end(), y.start()
            elif y.end() <= x.start():
                lo, hi = y.end(), x.start()
            else:
                continue
            gap = hi - lo
            if best is None or gap < best[0]:
                best = (gap, lo, hi)
    if best is None:
        return None
    _, lo, hi = best
    lo2 = max(0, lo - window // 4)
    hi2 = min(len(text), hi + window // 4)
    span = text[lo2:hi2].strip()
    return span[:480] if span else None


def _collect_predicate_spans(
    edge_chunks: dict[tuple[int, int], list[int]],
    chunk_text: dict[int, str],
    names_canonical: list[str], window: int,
) -> tuple[list[str], dict[tuple[int, int], list[int]]]:
    """Build the flat list of span_texts plus a per-edge index map into it."""
    span_texts: list[str] = []
    span_groups: dict[tuple[int, int], list[int]] = defaultdict(list)
    pat_cache: dict[int, re.Pattern] = {}
    for (a, b), chunk_ids in edge_chunks.items():
        pa = pat_cache.setdefault(a, _entity_regex(names_canonical[a]))
        pb = pat_cache.setdefault(b, _entity_regex(names_canonical[b]))
        for cid in chunk_ids:
            text = chunk_text.get(cid, "")
            if not text:
                continue
            span = _closest_mention_pair_span(text, pa, pb, window)
            if span is None:
                continue
            span_texts.append(span)
            span_groups[(a, b)].append(len(span_texts) - 1)
    return span_texts, span_groups


def _snap_best_predicates(
    span_texts: list[str], span_groups: dict[tuple[int, int], list[int]],
    pred_emb: np.ndarray, predicates: list[str],
    edge_chunks: dict[tuple[int, int], list[int]],
    *, ollama_url: str, embed_model: str,
) -> dict[tuple[int, int], tuple[str, list[int]]]:
    """Embed the spans, mean-pool per edge, snap to the nearest predicate."""
    with httpx.Client() as client:
        span_emb = _ollama_embed(client, ollama_url, embed_model, span_texts)
    span_emb = _unit_rows(span_emb)
    out: dict[tuple[int, int], tuple[str, list[int]]] = {}
    for (a, b), idxs in span_groups.items():
        v = np.mean(span_emb[idxs], axis=0)
        norm = np.linalg.norm(v)
        if norm > 0:
            v = v / norm
        scores = pred_emb @ v
        best = int(np.argmax(scores))
        out[(a, b)] = (predicates[best], edge_chunks[(a, b)])
    return out


def snap_predicates(
    db_url: str, *, ollama_url: str, embed_model: str,
    keys: list[str], names_canonical: list[str],
    mentions: dict[str, set[int]], edges: list[tuple[int, int, float]],
    predicates: list[str], window: int = 120,
    log: Callable[[str], None] | None = None,
) -> dict[tuple[int, int], tuple[str, list[int]]]:
    """Orchestrator — each phase is a helper above.

    For each candidate edge, find co-occurrence chunks, extract the
    text-between-mentions, embed it, and snap to the nearest predicate in
    the fixed vocabulary by cosine similarity.

    docs/bugs/0009: refactored from a 100-line single function into five
    named helpers, each under 50 lines.
    """
    if not edges:
        return {}

    pred_emb = _embed_predicate_vocabulary(
        predicates, ollama_url=ollama_url, embed_model=embed_model,
    )

    edge_chunks = _cooccurrence_chunks_per_edge(edges, keys, mentions)
    if not edge_chunks:
        return {}

    chunk_text = _fetch_chunk_texts(
        db_url, [c for cs in edge_chunks.values() for c in cs],
    )

    span_texts, span_groups = _collect_predicate_spans(
        edge_chunks, chunk_text, names_canonical, window,
    )
    if not span_texts:
        return {}

    if log:
        log(f"  embedding {len(span_texts)} predicate spans for {len(edge_chunks)} edges…")

    return _snap_best_predicates(
        span_texts, span_groups, pred_emb, predicates, edge_chunks,
        ollama_url=ollama_url, embed_model=embed_model,
    )


def fingerprint(db_url: str) -> str:
    with _connect(db_url) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*), COALESCE(MAX(id),0) FROM chunks")
        nc, mc = cur.fetchone()
        cur.execute("SELECT COUNT(*), COALESCE(MAX(id),0) FROM documents")
        nd, md = cur.fetchone()
    return f"v1_c{nc}_{mc}_d{nd}_{md}"


def build_skein(
    db_url: str, *, ollama_url: str, embed_model: str, chat_model: str,
    predicates: list[str] | None = None,
    top_k: int = 6, min_sim: float = 0.55, window: int = 120,
    log: Callable[[str], None] = print,
) -> SkeinBuildStats:
    coverage([])  # validate recovery policy before any DB or model work
    with build_lock(db_url) as lock_connection:
        return _build_locked(db_url, ollama_url=ollama_url, embed_model=embed_model,
                             chat_model=chat_model, predicates=predicates, top_k=top_k,
                             min_sim=min_sim, window=window, log=log, lock_connection=lock_connection)


def _build_locked(db_url: str, *, ollama_url: str, embed_model: str, chat_model: str,
                  predicates: list[str] | None, top_k: int, min_sim: float,
                  window: int, log: Callable[[str], None], lock_connection) -> SkeinBuildStats:
    from skein.schema import schema_apply
    schema_apply(db_url)
    predicates = predicates or DEFAULT_PREDICATES
    fp = fingerprint(db_url)
    log(f"Skein build · fingerprint={fp}")

    t0 = time.time()
    log("1/4 discovering entity vocabulary (1 LLM call per document)…")
    vocab = discover_vocabulary(db_url, ollama_url=ollama_url, chat_model=chat_model, log=log)
    discovery = coverage(vocab)
    log(f"   → {len(vocab)} unique entities")

    log("2/4 finding mentions across all chunks (regex)…")
    mentions = find_mentions(db_url, vocab)
    vocab = [v for v in vocab if mentions.get(_normalize_name(v["name"]))]
    keys = [_normalize_name(v["name"]) for v in vocab]
    names_canonical = [v["name"] for v in vocab]
    log(f"   → {sum(len(s) for s in mentions.values())} mentions across {len(vocab)} entities")

    log("3/4 computing entity embeddings (mean of chunk vectors)…")
    embs_dict = compute_entity_embeddings(db_url, mentions)
    keys = [k for k in keys if k in embs_dict]
    if not keys:
        raise RuntimeError("no usable entities discovered; previous Skein graph preserved")
    keep = set(keys)
    vocab = [v for v in vocab if _normalize_name(v["name"]) in keep]
    names_canonical = [v["name"] for v in vocab]
    embeddings = np.stack([embs_dict[k] for k in keys])

    log(f"4/4 building edges (top_k={top_k}, min_sim={min_sim}) + snapping predicates…")
    raw_edges = build_edges(keys, embeddings, top_k=top_k, min_sim=min_sim)
    log(f"   → {len(raw_edges)} candidate edges")
    pred_map = snap_predicates(
        db_url, ollama_url=ollama_url, embed_model=embed_model,
        keys=keys, names_canonical=names_canonical, mentions=mentions,
        edges=raw_edges, predicates=predicates, window=window, log=log,
    )

    if fingerprint(db_url) != fp:
        raise RuntimeError("corpus changed during build; previous Skein graph preserved; retry build")
    log("persisting…")
    ensure_lock(lock_connection)
    persist(db_url, vocab, mentions, keys, embeddings, raw_edges, pred_map, fp, discovery=discovery)

    return _build_stats(vocab, mentions, pred_map, t0, log)


def _build_stats(vocab, mentions, pred_map, started, log) -> SkeinBuildStats:
    dt = time.time() - started
    stats = {
        "n_entities": len(vocab),
        "n_mentions": sum(len(s) for s in mentions.values()),
        "n_edges": len(pred_map),
        "build_seconds": round(dt, 1),
    }
    log(f"Skein built in {dt:.1f}s · {stats}")
    return stats


def persist(
    db_url: str, vocab: list[dict], mentions: dict[str, set[int]],
    keys: list[str], embeddings: np.ndarray,
    edges: list[tuple[int, int, float]],
    pred_map: dict[tuple[int, int], tuple[str, list[int]]],
    fp: str,
    *, discovery: dict | None = None,
):
    with _connect(db_url) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM skein_relations")
            cur.execute("DELETE FROM skein_entity_chunks")
            cur.execute("DELETE FROM skein_entities")
            id_for_key: dict[str, int] = {}
            for i, v in enumerate(vocab):
                cur.execute(
                    "INSERT INTO skein_entities (name, name_norm, kind, mentions, embedding) "
                    "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (v["name"], keys[i], v["kind"], len(mentions[keys[i]]), embeddings[i]),
                )
                id_for_key[keys[i]] = cur.fetchone()[0]
            link_rows = [(id_for_key[k], c) for k, cs in mentions.items()
                         for c in cs if k in id_for_key]
            if link_rows:
                cur.executemany(
                    "INSERT INTO skein_entity_chunks (entity_id, chunk_id) VALUES (%s, %s) "
                    "ON CONFLICT DO NOTHING",
                    link_rows,
                )
            rel_rows = []
            for (a, b, s) in edges:
                if (a, b) not in pred_map:
                    continue
                pred, evidence = pred_map[(a, b)]
                rel_rows.append((id_for_key[keys[a]], pred, id_for_key[keys[b]],
                                 float(s), evidence))
            if rel_rows:
                cur.executemany(
                    "INSERT INTO skein_relations "
                    "(subject_id, predicate, object_id, sim, evidence_chunk_ids) "
                    "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    rel_rows,
                )
            cur.execute(
                "INSERT INTO skein_build (fingerprint, stats) VALUES (%s, %s)",
                (fp, json.dumps({"n_entities": len(vocab),
                                 "n_edges": len(rel_rows), "discovery": discovery or {}})),
            )
        conn.commit()


def neighbors_of(db_url: str, name: str, *, limit: int = 20) -> dict:
    with _connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, kind, mentions FROM skein_entities WHERE name_norm = %s",
            (_normalize_name(name),),
        )
        row = cur.fetchone()
        if not row:
            return {"found": False, "name": name}
        eid, ename, kind, mentions = row
        cur.execute(
            """
            SELECT r.predicate, e.name, e.kind, r.sim, r.evidence_chunk_ids,
                   CASE WHEN r.subject_id = %s THEN 'out' ELSE 'in' END AS dir
            FROM skein_relations r
            JOIN skein_entities e
              ON e.id = CASE WHEN r.subject_id = %s THEN r.object_id ELSE r.subject_id END
            WHERE r.subject_id = %s OR r.object_id = %s
            ORDER BY r.sim DESC
            LIMIT %s
            """,
            (eid, eid, eid, eid, limit),
        )
        edges = [
            {"predicate": p, "other": n, "kind": k, "sim": float(s),
             "evidence": list(ev), "direction": d}
            for p, n, k, s, ev, d in cur.fetchall()
        ]
    return {"found": True, "id": eid, "name": ename, "kind": kind,
            "mentions": mentions, "edges": edges}
