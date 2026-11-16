"""Tests for the static-demo data generator (no LLM needed)."""
from scripts import make_demo_data as demo

TABLE = """# Evaluation results

| Experiment | k | n | Recall@k | Hit-all@k | MRR | Exec acc | Easy | Medium | Hard | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 4 | 40 | 0.962 | 0.900 | 0.988 | 97.5% | 100.0% | 100.0% | 90.0% | dense k=4, explain off |
| ret-bm25-k4 | 4 | 40 | 0.884 | 0.750 | 0.821 | - | - | - | - | bm25, n_chunks=10|
| gen-noschema | 4 | 40 | - | - | - | 55.0% | 20.0% | 86.7% | 60.0% | NO schema, ~470 prompt chars |
"""


def test_parse_results_reads_every_row_and_column():
    rows = demo.parse_results(TABLE)
    assert [r["name"] for r in rows] == ["baseline", "ret-bm25-k4", "gen-noschema"]
    assert rows[0]["exec_acc"] == "97.5%" and rows[0]["hit_all"] == "0.900"
    assert rows[1]["exec_acc"] == "-" and rows[1]["notes"] == "bm25, n_chunks=10"
    assert rows[2]["recall"] == "-" and rows[2]["hard"] == "60.0%"


def test_parse_results_ignores_headers_and_junk():
    assert demo.parse_results("# title\n\nnot a table\n|---|---|\n| a | b |") == []


def test_example_ids_exist_in_the_benchmark():
    import json
    from pathlib import Path
    ids = {q["id"] for q in json.loads(
        (Path(__file__).resolve().parent.parent / "data" / "eval" / "questions.json").read_text(encoding="utf-8"))}
    assert set(demo.EXAMPLE_IDS) <= ids