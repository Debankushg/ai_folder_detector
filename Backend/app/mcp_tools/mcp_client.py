"""MCP client: starts the project MCP server and lets an LLM provider call its tools."""
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..config import BACKEND_DIR


async def run_with_mcp(root: Path, first_message: str, provider_loop):
    """Start the MCP server for `root`, then run `provider_loop(session, tools, first_message)`."""
    params = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp_tools.mcp_server"],
                                   cwd=str(BACKEND_DIR),
                                   env={**os.environ, "PROJECT_ROOT": str(root)})
    async with stdio_client(params) as (r, w), ClientSession(r, w) as session:
        await session.initialize()
        tools = (await session.list_tools()).tools
        return await provider_loop(session, tools, first_message)


async def call_tool(session, name: str, args: dict) -> tuple[str, bool]:
    """Call one MCP tool. Returns (text result, is_error)."""
    out = await session.call_tool(name, args)
    return "".join(getattr(p, "text", "") for p in out.content)[:8000], bool(out.isError)
