"""Smoke test: talk to our MCP server like a real client would (over stdio)."""
import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent


async def main():
    params = StdioServerParameters(command=sys.executable, args=["src/mcp_server.py"],
                                   env={**os.environ}, cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            print("tools:", [t.name for t in (await s.list_tools()).tools])

            r = await s.call_tool("get_schema", {"question": "How many customers per country?"})
            print("\nget_schema ->", r.is_error, r.structured_content["tables"])

            r = await s.call_tool("run_query", {"sql": "SELECT COUNT(*) AS n FROM Customer"})
            print("\nrun_query ->", r.is_error, r.structured_content)

            r = await s.call_tool("run_query", {"sql": "DROP TABLE Customer"})
            print("\nattack ->", r.is_error, [c.text for c in r.content])

            r = await s.call_tool("ask_database", {"question": "How many customers are there?"})
            print("\nask_database ->", r.is_error, r.structured_content)

            print("\nresources:", [(x.name, str(x.uri)) for x in (await s.list_resources()).resources])
            rr = await s.read_resource("dictionary://chinook")
            print("resource starts:", rr.contents[0].text[:60].replace("\n", " | "))


asyncio.run(main())