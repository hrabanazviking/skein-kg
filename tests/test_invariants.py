"""Invariant tests for Skein — the Prophecy Rite, layer 5.

These tests verify the IMMUTABLE truths from PROJECT_LAWS.md. They are
pure-Python and do NOT require Postgres or Ollama.

Run with:    uv run pytest tests/
"""
from __future__ import annotations

import inspect
import re
from typing import get_type_hints

import pytest

from skein import build_skein, neighbors_of, schema_apply
from skein.core import (
    DEFAULT_PREDICATES, SkeinBuildStats, SYSTEM_VOCAB,
    _entity_regex, _normalize_name, _parse_vocab_response,
    build_edges,
)


# ─── Iron Law 1: public surface stable ──────────────────────────────────────

def test_public_surface():
    """`build_skein`, `neighbors_of`, `schema_apply` are the only public API."""
    import skein
    expected = {"build_skein", "neighbors_of", "schema_apply"}
    actual = set(skein.__all__)
    assert actual == expected, f"public surface drift: {actual - expected} added, {expected - actual} removed"


def test_build_skein_signature_stable():
    """Required arguments to build_skein never change without a major version.

    Per INTERFACE.md: db_url is positional; ollama_url, embed_model, chat_model
    are keyword-only and required. Anything else added later must have a default.
    """
    sig = inspect.signature(build_skein)
    required = [p.name for p in sig.parameters.values() if p.default is inspect.Parameter.empty]
    expected = ["db_url", "ollama_url", "embed_model", "chat_model"]
    assert required == expected, f"build_skein required args changed: {required}"


def test_skein_build_stats_shape():
    """SkeinBuildStats TypedDict matches what INTERFACE.md promises."""
    expected_keys = {"n_entities", "n_mentions", "n_edges", "build_seconds"}
    actual_keys = set(SkeinBuildStats.__annotations__.keys())
    assert actual_keys == expected_keys


# ─── Iron Law 2: per-document LLM budget ────────────────────────────────────

def test_no_per_chunk_chat_in_source():
    """Skein's defining law: no autoregressive LLM call per chunk.

    Verify the source code does not contain a per-chunk chat invocation
    pattern. We grep for `for ... in chunks: ... ollama_chat`.
    """
    import skein.core as core
    src = inspect.getsource(core)
    # rough grep for the anti-pattern
    forbidden_patterns = [
        r"for\s+\w+\s+in\s+chunks[^:]*:\s*[^\n]*ollama_chat",
        r"for\s+\w+\s+in\s+rows[^:]*:\s*[^\n]*ollama_chat",
    ]
    for pat in forbidden_patterns:
        assert not re.search(pat, src, re.S), f"per-chunk ollama_chat detected: {pat}"


# ─── Iron Law 5: idempotency markers ───────────────────────────────────────

def test_schema_sql_is_idempotent():
    """All CREATE statements use IF NOT EXISTS."""
    from skein.schema import SCHEMA_SQL
    statements = [s.strip() for s in SCHEMA_SQL.split(";") if s.strip()]
    creates = [s for s in statements if s.upper().startswith(("CREATE TABLE", "CREATE INDEX", "CREATE EXTENSION"))]
    for s in creates:
        assert "IF NOT EXISTS" in s.upper(), f"non-idempotent CREATE: {s[:80]}"


# ─── Iron Law 4: sacred source — no writes to chunks/documents ─────────────

def test_no_writes_to_sacred_source():
    """Skein must not INSERT/UPDATE/DELETE/ALTER any non-`skein_*` table."""
    import skein.core as core
    import skein.schema as schema
    forbidden = re.compile(
        r"(INSERT\s+INTO|UPDATE|DELETE\s+FROM|ALTER\s+TABLE|DROP\s+TABLE)\s+(?!skein_)(?!IF\s+NOT)(?!IF\s+EXISTS)([a-zA-Z_]+)",
        re.IGNORECASE,
    )
    for mod in (core, schema):
        src = inspect.getsource(mod)
        # Allowlist: SELECT-only queries against documents/chunks are fine
        # We look only for write operations
        for match in forbidden.finditer(src):
            table = match.group(2)
            if table.lower().startswith("skein_"):
                continue
            pytest.fail(f"forbidden write to non-skein table '{table}' in {mod.__name__}: {match.group(0)}")


# ─── Bug 0001: Unicode word boundaries ─────────────────────────────────────

@pytest.mark.parametrize("name,text,should_match", [
    ("Odin", "and then Odin spoke", True),
    ("Mímir", "the well of Mímir lies deep", True),
    ("Þórr", "Þórr hurled the hammer", True),
    ("Þrúðr", "Þrúðr, daughter of Þórr", True),
    ("Odin", "Odinsbeard", False),     # word boundary must respect this
    ("Mímir", "Mímirinn", False),       # ditto for non-ASCII
])
def test_entity_regex_unicode_boundaries(name, text, should_match):
    """Per docs/bugs/0001: non-ASCII names must match with proper boundaries."""
    pat = _entity_regex(name)
    found = bool(pat.search(text))
    assert found == should_match, f"{name!r} in {text!r}: expected match={should_match}, got {found}"


# ─── Vocab parsing robustness ──────────────────────────────────────────────

def test_parse_vocab_response_handles_garbage():
    """Malformed LLM JSON returns [] without raising."""
    assert _parse_vocab_response("") == []
    assert _parse_vocab_response("not json at all") == []
    assert _parse_vocab_response("{") == []
    assert _parse_vocab_response('{"entities": null}') == []
    assert _parse_vocab_response('{"entities": [{"name": "Odin"}]}') == [{"name": "Odin"}]


def test_parse_vocab_response_strips_code_fences():
    """LLMs sometimes wrap JSON in ```json — should still parse."""
    raw = '```json\n{"entities":[{"name":"Odin"}]}\n```'
    assert _parse_vocab_response(raw) == [{"name": "Odin"}]


# ─── Predicate vocabulary sanity ──────────────────────────────────────────

def test_default_predicates_are_snake_case():
    """All default predicates are lowercase snake_case (or single word)."""
    for p in DEFAULT_PREDICATES:
        assert p == p.lower(), f"{p} is not lowercase"
        assert re.match(r"^[a-z_]+$", p), f"{p} is not snake_case"


def test_default_predicates_unique():
    """No duplicates in DEFAULT_PREDICATES."""
    assert len(DEFAULT_PREDICATES) == len(set(DEFAULT_PREDICATES))


# ─── normalize_name properties ─────────────────────────────────────────────

@pytest.mark.parametrize("a,b", [
    ("Odin", "odin"),
    ("  Odin  ", "odin"),
    ("Odin Allfather", "odin allfather"),
    ("Odin\tAllfather", "odin allfather"),  # whitespace normalized
    ("Odin   Allfather", "odin allfather"),  # collapsed
])
def test_normalize_name_collapses_whitespace_and_case(a, b):
    assert _normalize_name(a) == b


# ─── build_edges shape ────────────────────────────────────────────────────

def test_build_edges_returns_canonical_pairs():
    """Edges always have (a, b) with a < b — no duplicates from symmetry."""
    import numpy as np
    keys = ["x", "y", "z"]
    # 3 unit vectors that all somewhat overlap
    embs = np.eye(3, dtype=np.float32) + 0.6
    embs = embs / np.linalg.norm(embs, axis=1, keepdims=True)
    edges = build_edges(keys, embs, top_k=2, min_sim=0.0)
    for a, b, _ in edges:
        assert a < b, f"edge {(a, b)} not in canonical (a < b) order"


def test_build_edges_handles_too_few_nodes():
    """With one or zero nodes, returns []."""
    import numpy as np
    assert build_edges([], np.zeros((0, 1), dtype=np.float32), top_k=4, min_sim=0.5) == []
    assert build_edges(["x"], np.ones((1, 1), dtype=np.float32), top_k=4, min_sim=0.5) == []
