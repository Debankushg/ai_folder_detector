"""Google Gemini provider: tool-calling loop over the MCP tools (with overload retry)."""
import os

from ..config import MAX_LLM_TURNS
from ..diagram.graph_cleaner import clean_graph
from ..mcp_tools.mcp_client import call_tool
from .prompts import SYSTEM
from .response_parser import extract_json

async def _gemini_generate(client, models: list[str], contents, config):
    """Retry on overload (429/500/503), then try the next model in the list."""
    import asyncio
    from google.genai import errors

    last: Exception | None = None
    for model in models:
        for delay in (0, 3, 8, 15):
            await asyncio.sleep(delay)
            try:
                return await client.aio.models.generate_content(model=model, contents=contents, config=config)
            except (errors.ServerError, errors.ClientError) as e:
                if getattr(e, "code", 0) not in (429, 500, 502, 503, 504):
                    raise
                last = e
    raise last


async def run_gemini(session, mcp_tools, first: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    models = [os.getenv("GEMINI_MODEL", "gemini-3.8-flash")] + [
        m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "").split(",") if m.strip()]
    tools = [types.Tool(function_declarations=[
        types.FunctionDeclaration(name=t.name, description=t.description or "",
                                  parameters_json_schema=t.inputSchema) for t in mcp_tools])]
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM, tools=tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
    contents = [types.Content(role="user", parts=[types.Part(text=first)])]
    for _ in range(MAX_LLM_TURNS):
        resp = await _gemini_generate(client, models, contents, config)
        if not resp.candidates or not resp.candidates[0].content:
            raise RuntimeError("Gemini returned an empty response")
        msg = resp.candidates[0].content
        contents.append(msg)
        calls = [p.function_call for p in (msg.parts or []) if p.function_call]
        if not calls:
            return clean_graph(extract_json("".join(p.text or "" for p in (msg.parts or []))))
        parts = []
        for c in calls:
            txt, err = await call_tool(session, c.name, dict(c.args or {}))
            parts.append(types.Part.from_function_response(
                name=c.name, response={"error": txt} if err else {"result": txt}))
        contents.append(types.Content(role="user", parts=parts))
    raise RuntimeError("LLM did not finish within the turn limit")
