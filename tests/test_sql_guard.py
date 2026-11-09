import json
import sqlite3

import pytest

from src import sql_guard
from src.sql_guard import GuardError, QueryError, run_query, validate_sql


@pytest.fixture(autouse=True)
def tmp_log(tmp_path, monkeypatch):
    """Send logs to a temp file so tests never touch the real log."""
    path = tmp_path / "queries.jsonl"
    monkeypatch.setattr(sql_guard, "LOG_PATH", path)
    return path


ATTACKS = {
    "multiple_statements": "SELECT 1; DROP TABLE Customer",
    "multiple_statements_comment": "SELECT * FROM Customer; DROP TABLE Customer --",
    "insert": "INSERT INTO Customer (CustomerId) VALUES (999)",
    "update": "UPDATE Customer SET Country = 'X'",
    "delete": "DELETE FROM Customer",
    "drop": "DROP TABLE Customer",
    "alter": "ALTER TABLE Customer ADD COLUMN hacked INT",
    "create": "CREATE TABLE evil (a INT)",
    "replace_into": "REPLACE INTO Customer (CustomerId) VALUES (1)",
    "pragma": "PRAGMA table_info(Customer)",
    "attach": "ATTACH DATABASE 'other.db' AS other",
    "detach": "DETACH DATABASE other",
    "vacuum_into": "VACUUM INTO 'copy.db'",
    "explain": "EXPLAIN SELECT 1",
    "transaction": "BEGIN",
    "load_extension": "SELECT load_extension('evil.dll')",
    "readfile": "SELECT readfile('/etc/passwd')",
    "memory_bomb_zeroblob": "SELECT zeroblob(1000000000)",
    "memory_bomb_randomblob": "SELECT randomblob(100000000)",
    "unknown_table": "SELECT * FROM users",
    "unknown_table_join": "SELECT * FROM Customer, secret_table",
    "unknown_table_in_subquery": "SELECT * FROM Customer WHERE CustomerId IN (SELECT id FROM secrets)",
    "sqlite_master": "SELECT * FROM sqlite_master",
    "sqlite_schema_join": "SELECT * FROM Customer c JOIN sqlite_schema s ON 1=1",
    "schema_qualified": "SELECT * FROM main.sqlite_master",
    "table_valued_function": "SELECT * FROM pragma_table_info('Customer')",
    "delete_inside_cte": "WITH x AS (DELETE FROM Customer RETURNING *) SELECT * FROM x",
    "empty": "",
    "whitespace": "   ",
    "too_long": "SELECT 1 " + "+ 1 " * 1000,
}


@pytest.mark.parametrize("sql", ATTACKS.values(), ids=ATTACKS.keys())
def test_attack_is_blocked(sql):
    with pytest.raises(GuardError):
        validate_sql(sql)


def test_non_string_is_blocked():
    with pytest.raises(GuardError):
        validate_sql(None)


def test_blocked_attack_never_touches_database():
    with pytest.raises(GuardError):
        run_query("DELETE FROM Customer")
    assert run_query("SELECT COUNT(*) FROM Customer")["rows"][0][0] == 59


def test_database_is_read_only_even_without_guard():
    """Defense in depth: bypass the guard and the DB itself still refuses writes."""
    con = sqlite3.connect(sql_guard.DB_URI, uri=True)
    with pytest.raises(sqlite3.OperationalError):
        con.execute("DELETE FROM Customer")
    con.close()


NORMAL = {
    "simple": "SELECT * FROM Customer",
    "trailing_semicolon": "SELECT FirstName FROM Customer;",
    "where": "SELECT FirstName FROM Customer WHERE Country = 'USA'",
    "group_by": "SELECT Country, COUNT(*) AS n FROM Customer GROUP BY Country ORDER BY n DESC",
    "join": "SELECT t.Name FROM Track t JOIN Album a ON t.AlbumId = a.AlbumId",
    "subquery": "SELECT Name FROM Track WHERE TrackId IN (SELECT TrackId FROM InvoiceLine)",
    "cte": "WITH c AS (SELECT * FROM Customer) SELECT COUNT(*) FROM c",
    "union": "SELECT Name FROM Artist UNION SELECT Name FROM Genre",
    "lowercase_table": "select count(*) from customer",
    "strftime": "SELECT strftime('%Y', InvoiceDate) AS y, SUM(Total) FROM Invoice GROUP BY y",
    "comment_is_harmless": "SELECT * FROM Customer -- ; DROP TABLE Customer",
}


@pytest.mark.parametrize("sql", NORMAL.values(), ids=NORMAL.keys())
def test_normal_query_passes(sql):
    out = validate_sql(sql)
    assert out.upper().startswith(("SELECT", "WITH"))


def test_normal_query_runs():
    out = run_query("SELECT COUNT(*) AS n FROM Customer")
    assert out["columns"] == ["n"]
    assert out["rows"][0][0] == 59


def test_comment_is_removed_from_executed_sql():
    assert "--" not in validate_sql("SELECT * FROM Customer -- ; DROP TABLE Customer")


def test_limit_added_when_missing():
    assert "LIMIT 50" in validate_sql("SELECT * FROM Track")


def test_huge_limit_is_lowered():
    out = validate_sql("SELECT * FROM Track LIMIT 1000000")
    assert "LIMIT 50" in out and "1000000" not in out


def test_small_limit_is_kept():
    assert "LIMIT 5" in validate_sql("SELECT * FROM Track LIMIT 5")


def test_union_gets_limit_too():
    assert "LIMIT 50" in validate_sql("SELECT Name FROM Artist UNION SELECT Name FROM Genre")


def test_row_cap_and_truncated_flag():
    out = run_query("SELECT * FROM Track")
    assert len(out["rows"]) == 50
    assert out["truncated"] is True


def test_timeout_stops_runaway_query(monkeypatch):
    monkeypatch.setattr(sql_guard, "TIMEOUT_S", 0.3)
    infinite = ("WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r) "
                "SELECT COUNT(*) FROM r")
    with pytest.raises(QueryError, match="timed out"):
        run_query(infinite)


def test_execution_error_is_reported():
    with pytest.raises(QueryError):
        run_query("SELECT no_such_column FROM Customer")


def test_every_query_is_logged(tmp_log):
    run_query("SELECT 1")
    with pytest.raises(GuardError):
        run_query("DROP TABLE Customer")
    entries = [json.loads(line) for line in tmp_log.read_text().splitlines()]
    assert [e["status"] for e in entries] == ["ok", "blocked"]
    assert "DROP TABLE" in entries[1]["sql"]

def test_strict_mode_allows_only_listed_tables():
    with pytest.raises(GuardError):
        run_query("SELECT * FROM Invoice", tables=["Customer"])
    assert run_query("SELECT COUNT(*) FROM Customer", tables=["Customer"])["rows"][0][0] == 59