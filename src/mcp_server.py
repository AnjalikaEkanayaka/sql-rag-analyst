"""MCP server: the SQL + RAG analyst as three tools and one resource.

Run directly (stdio transport):  python src/mcp_server.py
Inspect with MCP Inspector:      npx @modelcontextprotocol/inspector <python> src/mcp_server.py
"""
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # `from src...` works however the client launches us
os.chdir(ROOT)                 # our code uses relative paths like data/chinook.db

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

from src import sql_guard  # noqa: E402
from src.pipeline import ask, schema_text  # noqa: E402
from src.retrieval import retrieve  # noqa: E402

# STRICT_TABLES=1 makes the guard accept only the tables retrieved for the question
# (least privilege; costs some accuracy, see eval/results.md).
STRICT = os.getenv("STRICT_TABLES", "0") == "1"

mcp = MCPServer(
    "sql-rag-analyst",
    instructions=(
        "Answers plain-English questions about the Chinook music-store SQLite database. "
        "Use get_schema to see relevant tables, run_query to run your own read-only SELECT, "
        "or ask_database to go from question to answer in one step."
    ),
)


@mcp.tool()
def get_schema(question: str, k: int = 4) -> dict[str, Any]:
    """Find the database tables most relevant to a question.

    Returns the table names and their column definitions (types, primary and foreign keys).
    Use this before writing SQL with run_query.
    """
    tables = [r["table"] for r in retrieve(question, k=k)]
    return {"tables": tables, "schema": schema_text(tables)}


@mcp.tool(name="run_query")
def run_sql(sql: str) -> dict[str, Any]:
    """Validate and run ONE read-only SELECT statement on the Chinook database.

    Only SELECT on known tables is allowed. A LIMIT of 50 rows is enforced, with a 5 second
    timeout. Returns the SQL that actually ran, column names and rows.
    """
    try:
        return sql_guard.run_query(sql)
    except (sql_guard.GuardError, sql_guard.QueryError) as e:
        # ToolError text is shown to the client; any other exception is hidden from it
        raise ToolError(str(e)) from e


@mcp.tool()
def ask_database(question: str) -> dict[str, Any]:
    """Answer a plain-English question about the database.

    Finds relevant tables, writes a read-only SQL query with an LLM, validates and runs it,
    and returns the SQL, result rows and a short explanation. Check the 'sql' and 'tables'
    fields before trusting the answer.
    """
    out = ask(question, k=4, explain=True, strict=STRICT)
    return {key: out[key] for key in
            ("question", "tables", "sql", "columns", "rows", "explanation", "error")}


@mcp.resource("dictionary://chinook", name="data-dictionary", mime_type="text/markdown",
              description="Plain-language description of every table and column.")
def data_dictionary() -> str:
    return (ROOT / "data" / "data_dictionary.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run()  # stdio transport