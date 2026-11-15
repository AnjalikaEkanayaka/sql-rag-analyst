"""Tests for the MCP server, using the SDK's in-process client (no subprocess, no LLM)."""
import asyncio

import pytest
from mcp import Client

from src import mcp_server


def call(name, args):
    async def go():
        async with Client(mcp_server.mcp) as c:
            return await c.call_tool(name, args)
    return asyncio.run(go())


def text(result):
    return " ".join(getattr(c, "text", "") for c in result.content)


def test_exposes_three_tools_and_the_resource():
    async def go():
        async with Client(mcp_server.mcp) as c:
            tools = {t.name: t for t in (await c.list_tools()).tools}
            resources = [str(r.uri) for r in (await c.list_resources()).resources]
            return tools, resources
    tools, resources = asyncio.run(go())
    assert set(tools) == {"get_schema", "run_query", "ask_database"}
    assert resources == ["dictionary://chinook"]
    assert all(t.annotations.read_only_hint for t in tools.values())
    assert not any(t.annotations.destructive_hint for t in tools.values())


def test_schema_advertises_input_limits():
    async def go():
        async with Client(mcp_server.mcp) as c:
            return {t.name: t for t in (await c.list_tools()).tools}
    tools = asyncio.run(go())
    k = tools["get_schema"].input_schema["properties"]["k"]
    assert k["minimum"] == 1 and k["maximum"] == mcp_server.MAX_K
    assert tools["get_schema"].input_schema["properties"]["question"]["minLength"] == 3


@pytest.mark.parametrize("name,args", [
    ("get_schema", {"question": ""}),
    ("get_schema", {"question": "   "}),
    ("get_schema", {"question": "x" * 600}),
    ("get_schema", {"question": "customers per country", "k": 0}),
    ("get_schema", {"question": "customers per country", "k": 99}),
    ("ask_database", {"question": "hi"}),
    ("run_query", {"sql": ""}),
    ("run_query", {"sql": "SELECT 1 " + "+ 1 " * 600}),
])
def test_invalid_input_is_rejected(name, args):
    result = call(name, args)
    assert result.is_error
    assert "validation error" in text(result)


@pytest.mark.parametrize("sql,reason", [
    ("DROP TABLE Customer", "only SELECT is allowed"),
    ("SELECT 1; SELECT 2", "exactly one statement"),
    ("SELECT * FROM sqlite_master", "unknown table"),
    ("SELECT load_extension('x')", "function not allowed"),
])
def test_run_query_attacks_give_clear_errors(sql, reason):
    result = call("run_query", {"sql": sql})
    assert result.is_error
    assert "Blocked by the safety guard" in text(result)
    assert reason in text(result)


def test_run_query_execution_error_is_explained():
    result = call("run_query", {"sql": "SELECT nope FROM Customer"})
    assert result.is_error and "get_schema" in text(result)


def test_run_query_works_and_trims_whitespace():
    result = call("run_query", {"sql": "  SELECT COUNT(*) AS n FROM Customer  "})
    assert not result.is_error
    assert result.structured_content["rows"] == [[59]]


@pytest.mark.parametrize("error,expected", [
    ("GuardError: only SELECT is allowed, got Drop", "blocked by the safety guard"),
    ("QueryError: OperationalError: no such column: x", "failed to run"),
    ("LLMError: HTTP 429", "unavailable or rate-limited"),
    ("KeyError: boom", "Unexpected error"),
])
def test_ask_database_failures_become_tool_errors(monkeypatch, error, expected):
    import src.pipeline as pipeline
    monkeypatch.setattr(pipeline, "ask", lambda *a, **k: {"error": error, "sql": "SELECT 1"})
    result = call("ask_database", {"question": "anything at all"})
    assert result.is_error
    assert expected in text(result)
    assert "SQL attempted: SELECT 1" in text(result)


def test_ask_database_internal_crash_is_reported(monkeypatch):
    import src.pipeline as pipeline

    def boom(*a, **k):
        raise RuntimeError("index missing")
    monkeypatch.setattr(pipeline, "ask", boom)
    result = call("ask_database", {"question": "anything at all"})
    assert result.is_error and "pipeline failed" in text(result)


def test_ask_database_success_shape(monkeypatch):
    import src.pipeline as pipeline
    fake = {"question": "q", "tables": ["Customer"], "sql": "SELECT 1", "columns": ["n"],
            "rows": [[1]], "explanation": "One.", "error": None}
    monkeypatch.setattr(pipeline, "ask", lambda *a, **k: fake)
    result = call("ask_database", {"question": "anything at all"})
    assert not result.is_error
    assert set(result.structured_content) == {"question", "tables", "sql", "columns", "rows", "explanation"}