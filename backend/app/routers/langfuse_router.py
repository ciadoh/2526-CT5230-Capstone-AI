import httpx
from fastapi import APIRouter
from app.config import settings

router = APIRouter(prefix="/api/langfuse", tags=["langfuse"])


def _auth():
    return (settings.langfuse_public_key, settings.langfuse_secret_key)


@router.get("/traces")
async def list_traces(limit: int = 10, page: int = 1):
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return {"data": [], "meta": {"totalItems": 0, "totalPages": 0, "page": 1}}
    async with httpx.AsyncClient(verify=False) as client:
        r = await client.get(
            f"{settings.langfuse_host}/api/public/traces",
            params={"limit": limit, "page": page, "orderBy": "timestamp.desc"},
            auth=_auth(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
