"""OpenRouter-operated tools. These execute server-side and need no local handler."""

from src.core.config import settings


def openrouter_server_tools() -> list[dict]:
    tools: list[dict] = []
    if settings.web_search_enabled:
        tools.append(
            {
                "type": "openrouter:web_search",
                "parameters": {
                    "max_total_results": settings.web_search_max_total_results,
                    "search_context_size": settings.web_search_context_size,
                },
            }
        )
    if settings.web_fetch_enabled:
        tools.append(
            {
                "type": "openrouter:web_fetch",
                "parameters": {
                    "max_content_tokens": settings.web_fetch_max_content_tokens,
                },
            }
        )
    if settings.datetime_tool_enabled:
        tools.append(
            {
                "type": "openrouter:datetime",
                "parameters": {"timezone": settings.morrow_timezone},
            }
        )
    return tools
