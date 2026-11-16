import pytest
from fastapi.testclient import TestClient

from src import api, pipeline, retrieval

client = TestClient(api.app)

GOOD = {"question": "How many customers are there?", "tables": ["Customer"],
        "sql": "SELECT COUNT(*) FROM Customer LIMIT 50", "columns": ["n"], "rows": [[59]],
        "explanation": "There are 59 customers.", "error": None}


def failing(error, sql="SELECT 1"):
    return lambda *a, **k: {**GOOD, "error": error, "sql": sql}


def test_health_ok_when_everything_is_present(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "INDEX_DIR", tmp_path)  # exists
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok" and r.json()["tables"] == 11


def test_health_reports_a_missing_index(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "INDEX_DIR", tmp_path / "missing")
    r = client.get("/health")
    assert r.status_code == 503 and r.json()["status"] == "degraded" and r.json()["index"] is False


def test_ask_success(monkeypatch):
    monkeypatch.setattr(pipeline, "ask", lambda *a, **k: GOOD)
    r = client.post("/ask", json={"question": "  How many customers are there?  "})
    assert r.status_code == 200
    assert r.json()["rows"] == [[59]] and r.json()["sql"].startswith("SELECT")
    assert "error" not in r.json()


@pytest.mark.parametrize("payload", [{}, {"question": ""}, {"question": "hi"}, {"question": "   "},
                                     {"question": "x" * 501}, {"question": 123}, {"q": "How many customers?"}])
def test_ask_rejects_invalid_input(payload, monkeypatch):
    monkeypatch.setattr(pipeline, "ask", lambda *a, **k: pytest.fail("pipeline must not run"))
    assert client.post("/ask", json=payload).status_code == 422


@pytest.mark.parametrize("error,status,code", [
    ("GuardError: only SELECT is allowed, got Drop", 422, "blocked_by_guard"),
    ("QueryError: OperationalError: no such column: x", 422, "query_failed"),
    ("LLMError: HTTP 429", 503, "llm_unavailable"),
])
def test_ask_failures_have_clear_status_and_body(monkeypatch, error, status, code):
    monkeypatch.setattr(pipeline, "ask", failing(error, sql="DROP TABLE Customer"))
    r = client.post("/ask", json={"question": "anything at all"})
    assert r.status_code == status
    detail = r.json()["detail"]
    assert detail["error"] == code and detail["sql"] == "DROP TABLE Customer"


def test_unexpected_errors_do_not_leak_internals(monkeypatch):
    monkeypatch.setattr(pipeline, "ask", failing("KeyError: secret_internal_detail"))
    r = client.post("/ask", json={"question": "anything at all"})
    assert r.status_code == 500 and "secret_internal_detail" not in r.text

    def boom(*a, **k):
        raise RuntimeError("secret path /etc/shadow")
    monkeypatch.setattr(pipeline, "ask", boom)
    r = client.post("/ask", json={"question": "anything at all"})
    assert r.status_code == 500 and "shadow" not in r.text


def test_schema_success(monkeypatch):
    monkeypatch.setattr(retrieval, "retrieve", lambda q, k=4, **kw: [{"table": "Customer"}, {"table": "Invoice"}][:k])
    r = client.get("/schema", params={"question": "customers per country", "k": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["tables"] == ["Customer", "Invoice"] and "TABLE Customer (" in body["schema_text"]


@pytest.mark.parametrize("params", [{}, {"question": "hi"}, {"question": "   "}, {"question": "x" * 501},
                                    {"question": "customers", "k": 0}, {"question": "customers", "k": 99},
                                    {"question": "customers", "k": "many"}])
def test_schema_rejects_invalid_input(params):
    assert client.get("/schema", params=params).status_code == 422


def test_schema_failure_is_a_clean_500(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("collection does not exist at /secret/path")
    monkeypatch.setattr(retrieval, "retrieve", boom)
    r = client.get("/schema", params={"question": "customers per country"})
    assert r.status_code == 500 and "/secret/path" not in r.text


def test_unknown_route_and_wrong_method():
    assert client.get("/nope").status_code == 404
    assert client.get("/ask").status_code == 405


def test_openapi_documents_the_three_endpoints():
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths) == {"/health", "/schema", "/ask"}


def test_llm_errors_do_not_leak_provider_details(monkeypatch):
    monkeypatch.setattr(pipeline, "ask", failing("LLMError: HTTP 429: Rate limit reached in organization org_SECRET123"))
    r = client.post("/ask", json={"question": "anything at all"})
    assert r.status_code == 503 and "org_SECRET123" not in r.text and "429" not in r.text
    assert "try again later" in r.json()["detail"]["message"].lower()