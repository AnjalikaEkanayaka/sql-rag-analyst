"""Tests for the evaluation harness and for the integrity of the 40-question benchmark."""
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from eval import run_eval
from src import pipeline, sql_guard

QUESTIONS = json.loads((Path(__file__).resolve().parent.parent / "data" / "eval" / "questions.json")
                       .read_text(encoding="utf-8"))


def test_norm_rows_ignores_order_rounding_and_numeric_strings():
    assert run_eval.norm_rows([[2, "b"], [1, "a"]]) == run_eval.norm_rows([[1.0, "a"], [2.004, " b "]])
    assert run_eval.norm_rows([["2021", 5]]) == run_eval.norm_rows([[2021, 5.0]])
    assert run_eval.norm_rows([[1, "a"]]) != run_eval.norm_rows([[1, "b"]])
    assert run_eval.norm_rows([[None, "x"]]) == run_eval.norm_rows([[None, "x"]])


def test_extra_columns_make_a_result_wrong():
    assert run_eval.norm_rows([[1, "a"]]) != run_eval.norm_rows([[1]])


def test_retrieval_metrics():
    assert run_eval.retrieval_metrics({"A", "B"}, ["C", "A"]) == (0.5, 0.5)
    assert run_eval.retrieval_metrics({"A"}, ["a"]) == (1.0, 1.0)
    assert run_eval.retrieval_metrics({"A"}, []) == (0.0, 0.0)


def test_classify_statuses():
    gold = run_eval.norm_rows([[1]])
    mk = lambda error=None, rows=(): {"error": error, "rows": list(rows)}
    assert run_eval.classify(mk(rows=[[1.0]]), gold) == "correct"
    assert run_eval.classify(mk(rows=[[2]]), gold) == "wrong_result"
    assert run_eval.classify(mk(), gold) == "empty_result"
    assert run_eval.classify(mk("GuardError: x"), gold) == "blocked"
    assert run_eval.classify(mk("QueryError: x"), gold) == "exec_error"
    assert run_eval.classify(mk("LLMError: x"), gold) == "llm_error"


def test_gold_tables_from_sql():
    assert run_eval.gold_tables("SELECT 1 FROM Album a JOIN Artist r ON a.ArtistId = r.ArtistId") == {"Album", "Artist"}
    assert run_eval.gold_tables("WITH x AS (SELECT * FROM Track) SELECT * FROM x") == {"Track"}
    assert run_eval.gold_tables("SELECT * FROM Customer WHERE CustomerId IN (SELECT CustomerId FROM Invoice)") == {"Customer", "Invoice"}


def test_summarize_counts_correctly():
    recs = [{"recall": 1.0, "rr": 1.0, "status": "correct", "difficulty": "easy"},
            {"recall": 0.5, "rr": 0.5, "status": "wrong_result", "difficulty": "hard"}]
    s = run_eval.summarize(recs, 4, False)
    assert s["hit_all"] == 0.5 and s["exec_acc"] == 0.5 and s["easy"] == 1.0 and s["hard"] == 0.0


# ---- benchmark integrity -------------------------------------------------------------------
def test_benchmark_shape():
    assert [q["id"] for q in QUESTIONS] == list(range(1, 41))
    assert Counter(q["difficulty"] for q in QUESTIONS) == {"easy": 15, "medium": 15, "hard": 10}
    assert len({q["question"].lower() for q in QUESTIONS}) == 40


@pytest.mark.parametrize("q", QUESTIONS, ids=[f"q{q['id']}" for q in QUESTIONS])
def test_gold_sql_is_valid_safe_and_answerable(q, tmp_path, monkeypatch):
    monkeypatch.setattr(sql_guard, "LOG_PATH", tmp_path / "log.jsonl")
    result = sql_guard.run_query(q["gold_sql"])  # passes the guard and executes
    assert result["rows"] and not result["truncated"]
    assert {t.lower() for t in run_eval.gold_tables(q["gold_sql"])} <= sql_guard.known_tables()


def test_fewshot_examples_never_overlap_the_benchmark():
    shown = {s.lower() for s in re.findall(r"^Q: (.*)$", pipeline.FEWSHOT, re.M)}
    assert shown and not shown & {q["question"].lower() for q in QUESTIONS}
    gold = {re.sub(r"\s+", " ", q["gold_sql"]).lower() for q in QUESTIONS}
    for sql in re.findall(r"^SQL: (.*)$", pipeline.FEWSHOT, re.M):
        assert re.sub(r"\s+", " ", sql).lower() not in gold