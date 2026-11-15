"""MCP server: the SQL + RAG analyst as three tools and one resource.

Run directly (stdio transport):  python src/mcp_server.py
Inspect with MCP Inspector:      npx @modelcontextprotocol/inspector .venv/Scripts/python.exe src/mcp_server.py
"""
import os
import sys
from pathlib import Path
from typing import Annotated, Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # `from src...` works however the client launches us
os.chdir(ROOT)                 # our code uses relative paths like data/chinook.db

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402
from pydantic import Field, StringConstraints  # noqa: E402

from src import sql_guard  # noqa: E402  (light: sqlglot only)
# NOTE: src.pipeline / src.retrieval pull in chromadb + fastembed (slow to import), so they are
# imported inside the tools. The server then answers the client's handshake immediately.

# STRICT_TABLES=1 makes the guard accept only the tables retrieved for the question
# (least privilege; costs some accuracy, see eval/results.md).
STRICT = os.getenv("STRICT_TABLES", "0") == "1"
MAX_K = len(sql_guard.known_tables())

# Parameter types: the SDK turns these into the JSON schema the client's AI reads, and enforces them.
Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500),
                     Field(description="A plain-English question about the music-store data.",
                           examples=["Who are the top 3 customers by total spending?"])]
TopK = Annotated[int, Field(ge=1, le=MAX_K, description="How many tables to return (default 4).")]
Sql = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1,
                                       max_length=sql_guard.MAX_SQL_CHARS),
                Field(description="Exactly one SQLite SELECT statement.",
                      examples=["SELECT Name FROM Genre ORDER BY Name"])]

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                            openWorldHint=False)
# ask_database sends the question and schema text to a third-party LLM API.
READ_ONLY_EXTERNAL = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True,
                                     openWorldHint=True)

mcp = MCPServer(
    "sql-rag-analyst",
    instructions=(
        "Read-only access to the Chinook music-store database (SQLite): artists, albums, tracks, "
        "genres, customers, employees, invoices and playlists. For a simple question call "
        "ask_database. To control the SQL yourself, call get_schema first, then run_query. "
        "Read the data-dictionary resource for a full description of every table and column."
    ),
)


def _guard_error(e: Exception) -> ToolError:
    if isinstance(e, sql_guard.GuardError):
        return ToolError(f"Blocked by the safety guard: {e}. Only one read-only SELECT on "
                         "known tables is allowed.")
    return ToolError(f"The query failed to run: {e}. Check table and column names with get_schema.")


@mcp.tool(annotations=READ_ONLY)
def get_schema(question: Question, k: TopK = 4) -> dict[str, Any]:
    """Find the database tables most relevant to a question, with their columns.

    Call this before writing SQL for run_query. Returns 'tables' (best match first) and
    'schema' (column names, types, primary and foreign keys for those tables). Phrase the
    question naturally; mention the things you want to count, list or compare.
    """
    try:
        from src.pipeline import schema_text
        from src.retrieval import retrieve

        tables = [r["table"] for r in retrieve(question, k=k)]
        return {"tables": tables, "schema": schema_text(tables)}
    except Exception as e:
        raise ToolError(f"Schema lookup failed ({type(e).__name__}: {str(e)[:150]}). "
                        "If the search index is missing, run: python -m src.retrieval build") from e


@mcp.tool(name="run_query", annotations=READ_ONLY)
def run_sql(sql: Sql) -> dict[str, Any]:
    """Run ONE read-only SQLite SELECT statement and return the rows.

    Use this after get_schema when you want to write the SQL yourself. SQLite dialect (for
    dates use strftime). Only SELECT on the known tables is allowed, so no INSERT, UPDATE,
    DELETE, DROP, PRAGMA or multiple statements. System tables such as sqlite_master are not
    accessible: use get_schema to see table structure. At most 50 rows are returned (a LIMIT is
    added if missing) and a query is stopped after 5 seconds. Returns 'sql' (what actually ran),
    'columns', 'rows' and 'truncated' (true if the 50-row cap was reached).
    """
    try:
        return sql_guard.run_query(sql)
    except (sql_guard.GuardError, sql_guard.QueryError) as e:
        raise _guard_error(e) from e


@mcp.tool(annotations=READ_ONLY_EXTERNAL)
def ask_database(question: Question) -> dict[str, Any]:
    """Answer a plain-English question about the database in one step.

    Finds the relevant tables, has a language model write a read-only SQL query, validates and
    runs it, and explains the result. Returns 'sql', 'tables' (the schema the model was given),
    'columns', 'rows' (at most 50) and 'explanation'. The SQL is machine-generated and can be
    wrong, so check 'sql' before relying on the answer. If 'tables' lacks a table the question
    clearly needs (for example sales data without InvoiceLine), or the result looks wrong, use
    get_schema and run_query instead. The question and table definitions are sent to an
    external LLM service.
    """
    try:
        from src.pipeline import ask

        out = ask(question, k=4, explain=True, strict=STRICT)
    except Exception as e:
        raise ToolError(f"The pipeline failed ({type(e).__name__}: {str(e)[:150]}). "
                        "If the search index is missing, run: python -m src.retrieval build") from e
    if out["error"]:
        kind, _, detail = out["error"].partition(": ")
        reason = {
            "GuardError": "The generated SQL was blocked by the safety guard",
            "QueryError": "The generated SQL failed to run",
            "LLMError": "The language-model service is unavailable or rate-limited",
        }.get(kind, "Unexpected error")
        sql_note = f"\nSQL attempted: {out['sql']}\n" if out["sql"] else " "
        raise ToolError(f"{reason}: {detail}.{sql_note}You can inspect tables with get_schema "
                        "and run your own SELECT with run_query.")
    return {key: out[key] for key in ("question", "tables", "sql", "columns", "rows", "explanation")}


@mcp.resource("dictionary://chinook", name="data-dictionary", mime_type="text/markdown",
              description="Plain-language description of every table and column, with row counts "
                          "and example values.")
def data_dictionary() -> str:
    return (ROOT / "data" / "data_dictionary.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run()  # stdio transport