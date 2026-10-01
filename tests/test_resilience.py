"""Derived graphs must survive unreliable model responses and rebuilds."""
import httpx
import numpy as np
import pytest
from contextlib import nullcontext

import skein.core as core


@pytest.mark.parametrize("entity", [None, [], {"name": 4}, {"name": "  "}, {"kind": "deity"}])
def test_malformed_vocabulary_entries_are_dropped(entity):
    assert core._sanitize_entity(entity) is None


def test_wrong_optional_field_types_do_not_break_discovery():
    assert core._sanitize_entity({"name": " Odin ", "kind": 12, "aliases": "Wotan"}) == {
        "name": "Odin", "kind": "other", "aliases": []}


@pytest.mark.parametrize("payload", [[], [[1], [2]], [[0, 0]], [[float('inf'), 1]], [[1], [2, 3]]])
def test_bad_embedding_batches_fail_before_persistence(payload):
    with pytest.raises(ValueError, match="embedding"):
        core._validated_embeddings(payload, 1)


def test_empty_discovery_preserves_existing_graph(monkeypatch):
    import skein.schema
    monkeypatch.setattr(skein.schema, "schema_apply", lambda url: None)
    monkeypatch.setattr(core, "build_lock", lambda url: nullcontext(None))
    monkeypatch.setattr(core, "fingerprint", lambda url: "same")
    monkeypatch.setattr(core, "discover_vocabulary", lambda *a, **kw: [])
    monkeypatch.setattr(core, "find_mentions", lambda *a: {})
    monkeypatch.setattr(core, "compute_entity_embeddings", lambda *a: {})
    monkeypatch.setattr(core, "persist", lambda *a: pytest.fail("must preserve old graph"))
    with pytest.raises(RuntimeError, match="preserved"):
        core.build_skein("db", ollama_url="url", embed_model="embed", chat_model="chat", log=lambda m: None)


def test_permanent_http_errors_are_not_retried():
    count = 0
    def fail():
        nonlocal count
        count += 1
        response = httpx.Response(404, request=httpx.Request("POST", "http://ollama/api/embed"))
        response.raise_for_status()
    with pytest.raises(httpx.HTTPStatusError):
        core._retry(fail, base_delay=0)
    assert count == 1


def test_blocked_edges_match_dense_reference(monkeypatch):
    monkeypatch.setenv("SKEIN_EDGE_BLOCK_SIZE", "3")
    vectors = np.random.default_rng(8).normal(size=(17, 6)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    sim = vectors @ vectors.T
    np.fill_diagonal(sim, -1)
    reference = {}
    for i, neighbors in enumerate(np.argpartition(-sim, kth=3, axis=1)[:, :4]):
        for j in neighbors:
            if sim[i, j] >= .1:
                a, b = sorted((i, int(j)))
                reference[(a, b)] = float(sim[i, j])
    actual = {(a, b): score for a, b, score in core.build_edges(list(map(str, range(17))), vectors, top_k=4, min_sim=.1)}
    assert actual.keys() == reference.keys()
    for edge in actual:
        assert actual[edge] == pytest.approx(reference[edge], abs=1e-6)


@pytest.mark.parametrize("raw", ["", "not JSON", '{"entities":null}', '{"entities":[{"name":5}]}'])
def test_malformed_vocabulary_is_a_failed_document_in_strict_discovery(raw):
    with pytest.raises(ValueError):
        core._parse_vocab_response(raw, strict=True)
    assert core._parse_vocab_response(raw) == ([] if "name" not in raw else [{"name": 5}])


def test_valid_empty_vocabulary_is_not_misclassified_as_failure():
    assert core._parse_vocab_response('{"entities":[]}', strict=True) == []


def test_discovery_quality_gate_preserves_old_graph(monkeypatch):
    import skein.schema
    from skein.build_guard import Vocabulary
    monkeypatch.setattr(core, "build_lock", lambda url: nullcontext(None))
    monkeypatch.setattr(skein.schema, "schema_apply", lambda url: None)
    monkeypatch.setattr(core, "fingerprint", lambda url: "same")
    monkeypatch.setattr(core, "discover_vocabulary", lambda *a, **kw: Vocabulary([{"name":"Odin"}], 10, 2))
    monkeypatch.setattr(core, "find_mentions", lambda *a: pytest.fail("quality gate must precede graph work"))
    with pytest.raises(RuntimeError, match="previous graph preserved"):
        core.build_skein("db", ollama_url="url", embed_model="embed", chat_model="chat", log=lambda m: None)


def test_discovery_quality_threshold_is_configurable_and_validated(monkeypatch):
    from skein.build_guard import Vocabulary, coverage
    vocab = Vocabulary([], 10, 2)
    monkeypatch.setenv("SKEIN_MAX_FAILED_DOCUMENTS_PERCENT", "20")
    assert coverage(vocab)["failed_percent"] == 20
    monkeypatch.setenv("SKEIN_MAX_FAILED_DOCUMENTS_PERCENT", "NaN")
    with pytest.raises(ValueError):
        coverage(vocab)


def test_invalid_recovery_policy_fails_before_connecting(monkeypatch):
    monkeypatch.setenv("SKEIN_MAX_FAILED_DOCUMENTS_PERCENT", "NaN")
    monkeypatch.setattr(core, "build_lock", lambda url: pytest.fail("must validate before connection/model work"))
    with pytest.raises(ValueError):
        core.build_skein("unused", ollama_url="url", embed_model="embed", chat_model="chat")


def test_large_finite_embeddings_normalize_without_overflow():
    actual = core._unit_rows(np.array([[1e30, 1e30]], dtype=np.float32))
    assert np.isfinite(actual).all()
    assert np.linalg.norm(actual[0]) == pytest.approx(1)


def test_cancelling_chunk_vectors_do_not_create_zero_entity(monkeypatch):
    from unittest.mock import MagicMock
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.__iter__.return_value = iter([(1,[1,0]),(2,[-1,0])])
    monkeypatch.setattr(core, "_connect", lambda url: connection)
    monkeypatch.setattr(core, "register_vector", lambda conn: None)
    assert core.compute_entity_embeddings("unused", {"odin": {1,2}}) == {}
