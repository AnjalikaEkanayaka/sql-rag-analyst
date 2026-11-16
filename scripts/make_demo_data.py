"""Build docs/data.js for the static demo page.

Runs the real pipeline on a few benchmark questions, marks each answer correct or not against the
verified gold SQL (same comparison as the evaluation), and adds the evaluation results table.
Needs your Groq key and search index (answers and SQL come from the cache when already asked).

    python -m scripts.make_demo_data
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from eval import run_eval  # noqa: E402
from src import pipeline, sql_guard  # noqa: E402

EXAMPLE_IDS = [17, 18, 19, 25, 31, 36, 37, 39]  # mixed difficulty; #39 is a known failure
MAX_ROWS_SHOWN = 12
OUT = ROOT / "docs" / "data.js"


def parse_results(text):
    """eval/results.md table -> list of dicts."""
    rows = []
    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("|---") or line.startswith("| Experiment"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 11:
            continue
        keys = ["name", "k", "n", "recall", "hit_all", "mrr", "exec_acc", "easy", "medium", "hard"]
        row = dict(zip(keys, cells[:10]))
        row["notes"] = " | ".join(cells[10:])
        rows.append(row)
    return rows


def main():
    questions = {q["id"]: q for q in json.loads(
        (ROOT / "data" / "eval" / "questions.json").read_text(encoding="utf-8"))}
    examples = []
    for qid in EXAMPLE_IDS:
        q = questions[qid]
        gold = sql_guard.run_query(q["gold_sql"])
        out = pipeline.ask(q["question"], k=4, explain=True)
        status = run_eval.classify(out, run_eval.norm_rows(gold["rows"]))
        if status == "llm_error":
            sys.exit(f"LLM failure on #{qid}: {out['error']}\nRerun later; finished answers are cached.")
        print(f"#{qid:>2} {q['difficulty']:<6} {status}")
        examples.append({
            "id": qid, "difficulty": q["difficulty"], "question": q["question"],
            "status": status, "tables": out["tables"], "sql": out["sql"], "error": out["error"],
            "columns": out["columns"], "rows": out["rows"][:MAX_ROWS_SHOWN],
            "row_count": len(out["rows"]), "explanation": out["explanation"],
            "gold_sql": q["gold_sql"], "gold_tables": run_eval.gold_tables(q["gold_sql"]),
        })
    results = parse_results((ROOT / "eval" / "results.md").read_text(encoding="utf-8"))
    data = {"examples": examples, "results": results,
            "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            "settings": "k=4 retrieved tables, foreign-key hints on, all known tables allowed"}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("window.DEMO = " + json.dumps(data, ensure_ascii=False, indent=1, default=sorted) + ";\n",
                   encoding="utf-8")
    print(f"wrote {OUT} ({len(examples)} examples, {len(results)} result rows)")


if __name__ == "__main__":
    main()