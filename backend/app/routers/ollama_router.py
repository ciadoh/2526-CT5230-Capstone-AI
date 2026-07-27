from fastapi import APIRouter
from app.services import ollama_client

router = APIRouter(prefix="/api/ollama", tags=["ollama"])


@router.get("/status")
async def get_status():
    return await ollama_client.status()


@router.post("/generate")
async def generate(body: dict):
    prompt = body.get("prompt", "")
    model = body.get("model", ollama_client.OLLAMA_MODEL)
    try:
        response = await ollama_client.invoke(prompt, model)
        return {"model": model, "response": response}
    except Exception as e:
        return {"model": model, "response": f"ERROR: {e}", "error": True}
