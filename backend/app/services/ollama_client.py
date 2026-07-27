import httpx
from app.config import settings

OLLAMA_MODEL = "llama3.2:3b"


async def _ensure_model(client: httpx.AsyncClient) -> None:
    """Pull the model if it hasn't been downloaded yet."""
    r = await client.get(f"{settings.ollama_host}/api/tags", timeout=5)
    if r.status_code != 200:
        return
    existing = {m["name"].split(":")[0] for m in r.json().get("models", [])}
    if OLLAMA_MODEL.split(":")[0] not in existing:
        await client.post(
            f"{settings.ollama_host}/api/pull",
            json={"name": OLLAMA_MODEL, "stream": False, "insecure": True},
            timeout=300,
        )


async def invoke(prompt: str, model: str = OLLAMA_MODEL) -> str:
    async with httpx.AsyncClient() as client:
        await _ensure_model(client)
        r = await client.post(
            f"{settings.ollama_host}/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
            timeout=300,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def status() -> dict:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{settings.ollama_host}/api/tags", timeout=5)
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            return {"available": True, "models": models, "host": settings.ollama_host}
    except Exception as e:
        return {"available": False, "models": [], "error": str(e)}
