"""Internal API - LLM for apps."""
from typing import Dict, Any, List

from user_container.agent.llm_client import LLMClient
from user_container.db.db import DB

MAX_TOKENS = 4096


def chat(
    messages: List[Dict[str, Any]],
    model: str,
    app_id: str,
    db: DB
) -> Dict[str, Any]:
    """Wywołaj LLM i trackuj usage."""
    # Wybierz model
    if model == "cheap":
        client = LLMClient.cheap()
    else:
        client = LLMClient.default()

    # 3. Wywołaj LLM
    try:
        response = client.chat(
            messages=messages,
            tools=None,
            component=f"app:{app_id}"
        )
    except Exception as e:
        return {"status": "error", "error": str(e)}

    return {
        "status": "success",
        "content": response.content,
        "usage": response.usage,
        "cost_usd": response.cost_usd
    }
