"""SQL guard: validate with sqlglot, then execute read-only with timeout, row cap and logging."""
import json
import sqlite3
import time
from functools import lru_cache
from pathlib import Path

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

DB_URI = "file:data/chinook.db?mode=ro"
DICT_PATH = Path("data/data_dictionary.json")
LOG_PATH = Path("logs/queries.jsonl")
MAX_ROWS = 50
MAX_SQL_CHARS = 2000
TIMEOUT_S = 5.0

# Functions that read files, load code, or can exhaust memory.
BLOCKED_FUNCTIONS = {
    "load_extension", "readfile", "writefile", "edit", "fts3_tokenizer",
    "zeroblob", "randomblob",
}
# Statements that may only appear at the top level, but we also scan inside (defense in depth).
_FORBIDDEN_NAMES = ["Insert", "Update", "Delete", "Drop", "Alter", "AlterTable", "Create",
                    "Command", "Pragma", "Attach", "Detach", "Merge", "Transaction",
                    "Commit", "Rollback", "Set", "Use"]
FORBIDDEN_NODES = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))
ALLOWED_ROOTS = (exp.Select, exp.Union, exp.Intersect, exp.Except)


class GuardError(Exception):
    """The SQL was blocked by policy."""


class QueryError(Exception):
    """The SQL passed the guard but failed or timed out when executed."""


@lru_cache(maxsize=1)
def known_tables():
    data = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    return frozenset(t["table"].lower() for t in data)


def _enforce_limit(root, max_rows):
    if isinstance(root, exp.Select):
        lim = root.args.get("limit")
        n = None
        if lim is not None:
            e = lim.expression
            if isinstance(e, exp.Literal) and e.is_int:
                n = int(e.this)
        if n is None or n > max_rows:  # missing, huge, or not a plain number
            root = root.limit(max_rows, copy=False)
        return root
    # UNION / INTERSECT / EXCEPT: wrap so the cap applies to the whole result
    return exp.select("*").from_(root.subquery("q")).limit(max_rows)


def validate_sql(sql, tables=None, max_rows=MAX_ROWS):
    """Return safe SQL (comments removed, LIMIT enforced) or raise GuardError."""
    allowed = {t.lower() for t in tables} if tables is not None else known_tables()

    if not isinstance(sql, str) or not sql.strip():
        raise GuardError("empty or non-text SQL")
    if len(sql) > MAX_SQL_CHARS:
        raise GuardError(f"SQL longer than {MAX_SQL_CHARS} characters")

    try:
        statements = [s for s in sqlglot.parse(sql, read="sqlite") if s is not None]
    except SqlglotError as e:
        raise GuardError(f"could not parse SQL: {str(e)[:120]}")
    if len(statements) != 1:
        raise GuardError(f"exactly one statement allowed, got {len(statements)}")

    root = statements[0]
    if not isinstance(root, ALLOWED_ROOTS):
        raise GuardError(f"only SELECT is allowed, got {type(root).__name__}")

    bad = next(root.find_all(*FORBIDDEN_NODES), None)
    if bad is not None:
        raise GuardError(f"forbidden operation inside query: {type(bad).__name__}")

    for fn in root.find_all(exp.Func):
        name = (fn.name if isinstance(fn, exp.Anonymous) else fn.sql_name()).lower()
        if name in BLOCKED_FUNCTIONS:
            raise GuardError(f"function not allowed: {name}")

    cte_names = {c.alias_or_name.lower() for c in root.find_all(exp.CTE)}
    for t in root.find_all(exp.Table):
        if not isinstance(t.this, exp.Identifier):
            raise GuardError("table-valued functions are not allowed")
        if t.db or t.catalog:
            raise GuardError(f"schema-qualified table not allowed: {t.sql()}")
        name = t.name.lower()
        if name not in allowed and name not in cte_names:
            raise GuardError(f"unknown table: {t.name}")

    root = _enforce_limit(root, max_rows)
    return root.sql(dialect="sqlite", comments=False)


def _log(sql, status, reason=None, rows=None, ms=None):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "status": status,
             "sql": str(sql)[:500], "reason": reason, "rows": rows, "ms": ms}
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_query(sql, max_rows=MAX_ROWS, tables=None):
    """Validate then execute. Returns dict(sql, columns, rows, truncated)."""
    start = time.time()
    try:
        safe_sql = validate_sql(sql, tables=tables, max_rows=max_rows)
    except GuardError as e:
        _log(sql, "blocked", reason=str(e))
        raise

    con = sqlite3.connect(DB_URI, uri=True)
    deadline = time.time() + TIMEOUT_S
    timed_out = {"hit": False}

    def _check_time():
        if time.time() > deadline:
            timed_out["hit"] = True
            return 1  # non-zero = abort the running query
        return 0

    con.set_progress_handler(_check_time, 10_000)
    try:
        con.execute("PRAGMA query_only = ON")  # second lock on top of mode=ro
        cur = con.execute(safe_sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = [list(r) for r in cur.fetchmany(max_rows)]
        truncated = len(rows) >= max_rows  # cap reached, so there may be more rows
    except sqlite3.Error as e:
        msg = f"query timed out after {TIMEOUT_S}s" if timed_out["hit"] else f"{type(e).__name__}: {e}"
        _log(safe_sql, "error", reason=msg, ms=int((time.time() - start) * 1000))
        raise QueryError(msg)
    finally:
        con.close()

    _log(safe_sql, "ok", rows=len(rows), ms=int((time.time() - start) * 1000))
    return {"sql": safe_sql, "columns": columns, "rows": rows, "truncated": truncated}