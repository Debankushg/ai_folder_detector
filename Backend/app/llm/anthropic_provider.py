"""Anthropic Claude provider: tool-calling loop over the MCP tools."""
import os

from ..config import MAX_LLM_TURNS
from ..diagram.graph_cleaner import clean_graph
from ..mcp_tools.mcp_client import call_tool
from .prompts import SYSTEM
from .response_parser import extract_json

async def run_anthropic(session, mcp_tools, first: str) -> dict:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    tools = [{"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
             for t in mcp_tools]
    messages = [{"role": "user", "content": first}]
    for _ in range(MAX_LLM_TURNS):
        resp = await client.messages.create(model=model, max_tokens=4000, system=SYSTEM,
                                            tools=tools, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        calls = [b for b in resp.content if b.type == "tool_use"]
        if not calls:
            return clean_graph(extract_json("".join(b.text for b in resp.content if b.type == "text")))
        results = []
        for c in calls:
            txt, err = await call_tool(session, c.name, c.input)
            results.append({"type": "tool_result", "tool_use_id": c.id, "content": txt, "is_error": err})
        messages.append({"role": "user", "content": results})
    raise RuntimeError("LLM did not finish within the turn limit")
