import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services import github_client, ollama_client
from app.services.bedrock_client import invoke_model, MODELS
from app.state import get_active_repo
from app.config import settings
from langfuse import Langfuse

OLLAMA_ALIAS = "ollama"


def _langfuse():
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        return Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    return None

router = APIRouter(prefix="/api/github", tags=["github"])


def _parts():
    return get_active_repo().split("/", 1)


@router.get("/repo")
async def get_repo():
    owner, repo = _parts()
    return await github_client.get_repo(owner, repo)


@router.get("/commits")
async def get_commits(per_page: int = 20):
    owner, repo = _parts()
    return await github_client.get_commits(owner, repo, per_page)


@router.get("/languages")
async def get_languages():
    owner, repo = _parts()
    return await github_client.get_languages(owner, repo)


@router.get("/contributors")
async def get_contributors():
    owner, repo = _parts()
    return await github_client.get_contributors(owner, repo)


class FixPrRequest(BaseModel):
    issue_key: str
    issue_message: str
    component: str
    analysis: str
    model_alias: str = "nova-lite"


def _strip_fences(text: str) -> str:
    """Remove markdown code fences that models sometimes wrap output in."""
    text = re.sub(r"^```[^\n]*\n", "", text.strip())
    text = re.sub(r"\n```$", "", text.strip())
    return text


@router.post("/create-fix-pr")
async def create_fix_pr(req: FixPrRequest):
    owner, repo = _parts()
    active_project_key = get_active_repo().replace("/", "-")

    # Validate the issue belongs to the active repo
    if ":" in req.component:
        issue_project_key = req.component.split(":", 1)[0]
        if issue_project_key != active_project_key:
            raise HTTPException(
                status_code=400,
                detail=f"This issue is from '{issue_project_key}' but the active repo is '{active_project_key}'. Switch to the correct repo or select an issue from the current repo."
            )

    # Derive file path from SonarQube component string ("project-key:path/to/file.js")
    file_path = req.component.split(":", 1)[-1] if ":" in req.component else req.component

    # Fetch the real file content from GitHub
    try:
        original, file_sha = await github_client.get_file_content(owner, repo, file_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not fetch {file_path}: {e}")

    # Ask the model to produce the fixed file
    if req.model_alias != OLLAMA_ALIAS and req.model_alias not in MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown model: {req.model_alias}")

    prompt = (
        f"You are a senior software engineer. Fix the following SonarQube issue in the file below.\n\n"
        f"Issue   : {req.issue_message}\n"
        f"File    : {file_path}\n\n"
        f"Current file content:\n{original[:6000]}\n\n"
        f"Return ONLY the complete corrected file content. "
        f"No explanation, no markdown fences, no commentary — just the raw fixed code."
    )
    provider = OLLAMA_ALIAS if req.model_alias == OLLAMA_ALIAS else "bedrock"
    model_id = f"ollama/{ollama_client.OLLAMA_MODEL}" if provider == OLLAMA_ALIAS else MODELS[req.model_alias]

    lf = _langfuse()
    trace = generation = None
    if lf:
        trace = lf.trace(
            name="create-fix-pr",
            input={"issue": req.issue_message, "file": file_path, "model": req.model_alias},
        )
        generation = trace.generation(name=f"{provider}-fix", model=model_id, input=prompt)

    try:
        if provider == OLLAMA_ALIAS:
            text, usage = await ollama_client.invoke(prompt)
        else:
            text, usage = invoke_model(model_id, prompt, max_tokens=4096)
        fixed = _strip_fences(text)
    except Exception as e:
        if generation:
            generation.end(output=f"ERROR: {e}", level="ERROR")
        if trace:
            trace.update(output=f"ERROR: {e}")
        if lf:
            lf.flush()
        raise HTTPException(status_code=502, detail=f"Model error: {e}")

    if generation:
        generation.end(output=fixed, usage=usage)
    if trace:
        trace.update(output={"fixed_file": fixed[:500] + "..." if len(fixed) > 500 else fixed})
    if lf:
        lf.flush()

    # Create branch + commit + PR
    try:
        pr = await github_client.create_fix_pr(
            owner, repo, req.issue_key, req.issue_message,
            file_path, fixed, file_sha, req.analysis,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "pr_url": pr.get("html_url"),
        "pr_number": pr.get("number"),
        "branch": pr.get("head", {}).get("ref"),
        "usage": usage,
    }
