"""Evaluation harness: table recall@k, hit-all@k, MRR and execution accuracy.

Usage (from project root):
    python -m eval.run_eval --name baseline --k 4
    python -m eval.run_eval --name retrieval-k3 --k 3 --retrieval-only
    python -m eval.run_eval --name smoke --limit 5          # not recorded in results.md
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

import sqlglot
from sqlglot import exp

from src import sql_guard
from src.pipeline import ask
from src.retrieval import retrieve
from src.sql_guard import run_query

QUESTIONS = Path("data/eval/questions.json")
RUNS_DIR = Path("eval/runs")
RESULTS_MD = Path("eval/results.md")
HEADER = ("| Experiment | k | n | Recall@k | Hit-all@k | MRR | Exec acc | Easy | Medium | Hard | Notes |\n"
          "|---|---|---|---|---|---|---|---|---|---|---|\n")
NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


def gold_tables(sql):
    """Tables a gold query needs, read straight from the SQL (no hand labelling)."""
    tree = sqlglot.parse_one(sql, read="sqlite")
    ctes = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
    return {t.name for t in tree.find_all(exp.Table) if t.name.lower() not in ctes}


def _norm_cell(v):
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    if isinstance(v, str):
        s = v.strip()
        return round(float(s), 2) if NUMBER.match(s) else s
    return v


def norm_rows(rows):
    """Order-insensitive, rounding-tolerant form of a result set."""
    return sorted((tuple(_norm_cell(c) for c in r) for r in rows), key=repr)


def retrieval_metrics(gold, got):
    gold_l = {t.lower() for t in gold}
    got_l = [t.lower() for t in got]
    recall = len(gold_l & set(got_l)) / len(gold_l)
    rr = next((1 / rank for rank, t in enumerate(got_l, 1) if t in gold_l), 0.0)
    return recall, rr


def classify(out, gold_norm):
    err = out["error"]
    if err:
        if err.startswith("GuardError"):
            return "blocked"
        if err.startswith("QueryError"):
            return "exec_error"
        return "llm_error"
    if norm_rows(out["rows"]) == gold_norm:
        return "correct"
    return "empty_result" if not out["rows"] else "wrong_result"


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def summarize(records, k, retrieval_only):
    s = {"n": len(records), "k": k,
         "recall": mean(r["recall"] for r in records),
         "hit_all": mean(r["recall"] == 1.0 for r in records),
         "mrr": mean(r["rr"] for r in records)}
    if not retrieval_only:
        s["exec_acc"] = mean(r["status"] == "correct" for r in records)
        for d in ("easy", "medium", "hard"):
            s[d] = mean(r["status"] == "correct" for r in records if r["difficulty"] == d)
        s["status_counts"] = dict(Counter(r["status"] for r in records))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="experiment label")
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--retrieval-only", action="store_true", help="no LLM calls")
    ap.add_argument("--limit", type=int, help="only the first N questions (not recorded)")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    sql_guard.LOG_PATH = Path("logs/eval_queries.jsonl")  # keep eval out of the main audit log
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    if args.limit:
        questions = questions[:args.limit]

    records = []
    for q in questions:
        gold = run_query(q["gold_sql"])
        assert not gold["truncated"], f"gold for #{q['id']} hit the row cap"
        gold_norm = norm_rows(gold["rows"])
        rec = {"id": q["id"], "difficulty": q["difficulty"], "question": q["question"],
               "gold_tables": sorted(gold_tables(q["gold_sql"])), "sql": None, "status": None,
               "error": None}
        if args.retrieval_only:
            got = [r["table"] for r in retrieve(q["question"], k=args.k)]
        else:
            out = ask(q["question"], k=args.k, explain=False)
            got = out["tables"]
            rec.update(sql=out["sql"], error=out["error"], status=classify(out, gold_norm))
            if rec["status"] == "llm_error":
                raise SystemExit(f"\nLLM failure on #{q['id']}: {out['error']}\n"
                                 "Stopping so the numbers are not polluted. Answers so far are cached, "
                                 "so rerun the same command later (maybe after the quota resets).")
        rec["got_tables"] = got
        rec["recall"], rec["rr"] = retrieval_metrics(rec["gold_tables"], got)
        records.append(rec)
        print(f"#{q['id']:>2} {q['difficulty']:<6} recall={rec['recall']:.2f} {rec['status'] or ''}")

    s = summarize(records, args.k, args.retrieval_only)
    print("\n" + json.dumps(s, indent=1))

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / f"{args.name}.json").write_text(
        json.dumps({"summary": s, "records": records}, indent=1, ensure_ascii=False), encoding="utf-8")

    if args.limit:
        print("\n--limit used: not recorded in results.md")
        return
    pct = lambda x: f"{100 * x:.1f}%"
    acc = ["-"] * 4 if args.retrieval_only else [pct(s[x]) for x in ("exec_acc", "easy", "medium", "hard")]
    row = (f"| {args.name} | {args.k} | {s['n']} | {s['recall']:.3f} | {s['hit_all']:.3f} | "
           f"{s['mrr']:.3f} | {' | '.join(acc)} | {args.notes} |\n")
    new_file = not RESULTS_MD.exists() or RESULTS_MD.stat().st_size == 0
    with RESULTS_MD.open("a", encoding="utf-8") as f:
        if new_file:
            f.write("# Evaluation results\n\n" + HEADER)
        f.write(row)
    print(f"\nrecorded in {RESULTS_MD}")


if __name__ == "__main__":
    main()