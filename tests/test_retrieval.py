"""Retrieval tests that need no embedding model: pure functions, BM25, and mocked dense scores."""
import pytest

from src import retrieval


def chunks():
    import json
    return retrieval.build_chunks(json.loads(retrieval.DICT_PATH.read_text(encoding="utf-8")))


def test_tokens_split_camel_case_and_plurals():
    assert retrieval._tokens("InvoiceLine items") == ["invoice", "line", "item"]
    assert retrieval._tokens("Customers, orders!") == ["customer", "order"]


def test_every_table_gets_an_overview_and_column_chunks():
    cs = chunks()
    tables = {c["table"] for c in cs}
    assert {c["table"] for c in cs if c["kind"] == "overview"} == tables
    assert all(any(c["table"] == t and c["kind"] == "columns" for c in cs) for t in tables)


def test_chunk_ids_are_unique_and_text_starts_with_the_table_name():
    cs = chunks()
    assert len({c["id"] for c in cs}) == len(cs)
    assert all(c["text"].startswith(f"Table {c['table']}:") for c in cs)


def test_overview_chunk_lists_foreign_keys():
    overview = next(c for c in chunks() if c["id"] == "Invoice::overview")
    assert "CustomerId -> Customer.CustomerId" in overview["text"]


def test_foreign_key_neighbours_are_symmetric_and_correct():
    nb = retrieval._fk_neighbors()
    assert {"Album", "Genre", "MediaType", "InvoiceLine", "PlaylistTrack"} <= nb["Track"]
    assert all(a in nb[b] for a in nb for b in nb[a])


def test_rrf_rewards_agreement_between_rankings():
    a = {"X": {"score": 9, "chunk": "x"}, "Y": {"score": 5, "chunk": "y"}}
    b = {"X": {"score": 1, "chunk": "x"}, "Z": {"score": 0.5, "chunk": "z"}}
    fused = retrieval._rrf(a, b)
    assert fused["X"]["score"] == pytest.approx(2 / 61)
    assert fused["X"]["score"] > fused["Y"]["score"]
    assert fused["Y"]["score"] == pytest.approx(1 / 62) == pytest.approx(fused["Z"]["score"])


def test_fk_expand_adds_neighbours_but_never_lowers_a_score():
    scores = {"Customer": {"score": 0.9, "chunk": "c"}, "Genre": {"score": 0.1, "chunk": "g"}}
    out = retrieval._fk_expand(scores, boost=0.5)
    assert out["Invoice"]["score"] == pytest.approx(0.45)
    assert "foreign key" in out["Invoice"]["chunk"]
    assert out["Customer"]["score"] == 0.9 and out["Genre"]["score"] == 0.1


def test_bm25_finds_the_table_named_in_the_question():
    tables = [r["table"] for r in retrieval.retrieve("playlist", k=3, mode="bm25")]
    assert "Playlist" in tables


def test_retrieve_ranks_and_truncates(monkeypatch):
    fake = {t: {"score": s, "chunk": t} for t, s in [("Customer", .8), ("Invoice", .5), ("Track", .2)]}
    monkeypatch.setattr(retrieval, "_dense_scores", lambda q, n: fake)
    assert [r["table"] for r in retrieval.retrieve("q", k=2)] == ["Customer", "Invoice"]
    assert len(retrieval.retrieve("q", k=10)) == 3


def test_hybrid_combines_dense_and_keyword_rankings(monkeypatch):
    monkeypatch.setattr(retrieval, "_dense_scores", lambda q, n: {"Track": {"score": .9, "chunk": "t"}})
    monkeypatch.setattr(retrieval, "_bm25_scores", lambda q: {"Track": {"score": 3, "chunk": "t"},
                                                             "Genre": {"score": 2, "chunk": "g"}})
    out = retrieval.retrieve("q", k=2, mode="hybrid")
    assert [r["table"] for r in out] == ["Track", "Genre"]


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError):
        retrieval.retrieve("q", mode="nope")