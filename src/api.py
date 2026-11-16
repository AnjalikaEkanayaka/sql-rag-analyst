"""FastAPI service: GET /health, GET /schema, POST /ask.

Run:  uvicorn src.api:app --port 8000      then open http://localhost:8000/docs
"""
import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)  # our code uses relative paths like data/chinook.db

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.concurrency import run_in_threadpool  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel, Field, StringConstraints  # noqa: E402

from src import pipeline, retrieval, sql_guard  # noqa: E402

log = logging.getLogger("api")

DB_PATH = ROOT / "data" / "chinook.db"
DICT_PATH = ROOT / "data" / "data_dictionary.json"
INDEX_DIR = ROOT / "chroma_db"
STRICT = os.getenv("STRICT_TABLES", "0") == "1"
MAX_K = len(sql_guard.known_tables())

# One request at a time through the model and the vector store: simple, safe, and enough for a
# demo on a small machine. (/health does not take the lock.)
_lock = threading.Lock()

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class AskRequest(BaseModel):
    question: Question = Field(examples=["Who are the top 3 customers by total spending?"])


class AskResponse(BaseModel):
    question: str
    tables: list[str] = Field(description="The tables whose definitions the LLM was given.")
    sql: str = Field(description="The validated SQL that actually ran (machine-generated: check it).")
    columns: list[str]
    rows: list[list[Any]] = Field(description="At most 50 rows.")
    explanation: str | None


class SchemaResponse(BaseModel):
    tables: list[str]
    schema_text: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("WARMUP") == "1":  # load the embedding model before the first request
        await run_in_threadpool(lambda: retrieval.retrieve("warm up", k=1))
    yield


app = FastAPI(
    title="SQL + RAG Analyst",
    version="0.1.0",
    description="Ask plain-English questions about the Chinook music-store database. "
                "Retrieval picks relevant tables, an LLM writes read-only SQL, and a guard "
                "validates it before it runs.",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    """Liveness and readiness: 200 when the database, dictionary and search index are present."""
    checks = {"database": DB_PATH.exists(), "dictionary": DICT_PATH.exists(),
              "index": INDEX_DIR.exists()}
    ok = all(checks.values())
    body = {"status": "ok" if ok else "degraded", **checks,
            "strict_tables": STRICT, "tables": MAX_K}
    return JSONResponse(body, status_code=200 if ok else 503)


@app.get("/schema", response_model=SchemaResponse)
def schema(
    question: Annotated[str, Query(min_length=3, max_length=500,
                                   description="What you want to know; used to pick tables.")],
    k: Annotated[int, Query(ge=1, le=MAX_K, description="How many tables to return.")] = 4,
):
    """The tables most relevant to a question, with their column definitions."""
    question = question.strip()
    if len(question) < 3:
        raise HTTPException(422, detail={"error": "invalid_input",
                                         "message": "question must have at least 3 characters"})
    try:
        with _lock:
            tables = [r["table"] for r in retrieval.retrieve(question, k=k)]
            text = pipeline.schema_text(tables)
    except Exception:
        log.exception("schema lookup failed")
        raise HTTPException(500, detail={"error": "internal_error",
                                         "message": "Schema lookup failed. Is the search index built?"})
    return {"tables": tables, "schema_text": text}


# How each pipeline failure maps to an HTTP status: (status, code, message, show_detail).
# LLM errors can contain provider details (organisation ids, quotas), so they stay in the log.
_FAILURES = {
    "GuardError": (422, "blocked_by_guard", "The generated SQL was blocked by the safety guard", True),
    "QueryError": (422, "query_failed", "The generated SQL failed to run", True),
    "LLMError": (503, "llm_unavailable",
                 "The language-model service is unavailable or rate-limited. Try again later.", False),
}


@app.post("/ask", response_model=AskResponse,
          responses={422: {"description": "Invalid input, or no safe query could be produced"},
                     503: {"description": "LLM service unavailable"}})
def ask(req: AskRequest):
    """Answer a question: retrieve tables, generate SQL, validate, run, explain."""
    try:
        with _lock:
            out = pipeline.ask(req.question, k=4, explain=True, strict=STRICT)
    except Exception:
        log.exception("ask failed")
        raise HTTPException(500, detail={"error": "internal_error", "message": "Internal error."})
    if out["error"]:
        kind, _, detail = out["error"].partition(": ")
        status, code, label, show = _FAILURES.get(kind, (500, "internal_error", "Internal error.", False))
        if not show:
            log.error("pipeline error: %s", out["error"])
        message = f"{label}: {detail}" if show else label
        raise HTTPException(status, detail={"error": code, "message": message, "sql": out["sql"]})
    return out