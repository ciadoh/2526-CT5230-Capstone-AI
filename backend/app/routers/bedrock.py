from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings
from app.services import sonar_client, github_client, ollama_client
from app.services.bedrock_client import invoke_model, build_debt_prompt, MODELS
from app.state import get_active_repo
from langfuse import Langfuse

OLLAMA_ALIAS = "ollama"

router = APIRouter(prefix="/api/bedrock", tags=["bedrock"])

async def _invoke_alias(model_alias: str, prompt: str) -> tuple[str, str, dict]:
    if model_alias == OLLAMA_ALIAS:
        text, usage = await ollama_client.invoke(prompt)
        return text, f"ollama/{ollama_client.OLLAMA_MODEL}", usage

    model_id = MODELS.get(model_alias)
    if not model_id:
        raise HTTPException(status_code=400, detail=f"Unknown model alias: {model_alias}")
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        text, usage = await loop.run_in_executor(pool, invoke_model, model_id, prompt)
    return text, model_id, usage

def _langfuse():
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        return Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    return None

async def _get_sonar_data(project_key: str) -> tuple[list, dict]:
    try:
        sonar_data = await sonar_client.get_metrics(project_key)
        measures = sonar_data.get("component", {}).get("measures", [])
        metrics_flat = {m["metric"]: m.get("value") for m in measures}
        issues_data = await sonar_client.get_issues(project_key, page_size=20)
        issues = issues_data.get("issues", [])
        return issues, metrics_flat
    except Exception:
        return [], {}

def _build_github_fallback_prompt(repo: dict, commits: list) -> str:
    recent = "\n".join(
        f"- {c['sha'][:7]} {c['commit']['message'].split(chr(10))[0][:80]}"
        for c in commits[:5]
    )
    return f"""You are a senior software engineer reviewing the GitHub repository '{repo.get("full_name")}' for technical debt indicators.

Repository context:
- Description: {repo.get("description", "N/A")}
- Language: {repo.get("language", "N/A")}
- Open issues: {repo.get("open_issues_count", "N/A")}
- Forks: {repo.get("forks_count", "N/A")}
- Stars: {repo.get("stargazers_count", "N/A")}
- Last pushed: {repo.get("pushed_at", "N/A")}

Recent commits:
{recent}

Note: Static analysis (SonarQube) is not yet configured. Based on the repository metadata and commit history above, provide a concise analysis (3-5 bullet points) covering:
1. Likely technical debt risks based on the project type and age
2. Signs of good or poor maintenance from commit patterns
3. Recommended next steps for a technical debt assessment
Keep your response practical and actionable."""

class AnalyseRequest(BaseModel):
    model_alias: str = "nova-lite"

class IssueAnalyseRequest(BaseModel):
    model_alias: str = "nova-lite"
    issue_key: str
    message: str
    component: str
    severity: str = ""
    issue_type: str = ""
    rule: str = ""

def _build_issue_prompt(req: IssueAnalyseRequest) -> str:
    file_path = req.component.split(":")[-1] if ":" in req.component else req.component
    return f"""You are a senior software engineer performing a code review.

A static analysis tool (SonarQube) flagged the following issue:

  Severity : {req.severity}
  Type     : {req.issue_type}
  Rule     : {req.rule}
  File     : {file_path}
  Message  : {req.message}

Please provide:
1. A clear explanation of what this issue means and why it matters.
2. A concrete fix with a short code example (use the likely language based on the file extension).
3. Any caveats or edge cases to watch for when applying the fix.

Be concise and practical."""

@router.get("/models")
async def list_models():
    return {"models": list(MODELS.keys())}

@router.post("/analyse")
async def analyse(req: AnalyseRequest):
    if req.model_alias!= OLLAMA_ALIAS and req.model_alias not in MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown model alias: {req.model_alias}")

    project_key = get_active_repo().replace("/", "-")
    owner, repo_name = get_active_repo().split("/", 1)

    issues, metrics_flat = await _get_sonar_data(project_key)

    if metrics_flat:
        prompt = build_debt_prompt(issues, metrics_flat)
        data_source = "sonarqube"
    else:
        try:
            repo = await github_client.get_repo(owner, repo_name)
            commits = await github_client.get_commits(owner, repo_name, per_page=10)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"GitHub unavailable: {e}")
        prompt = _build_github_fallback_prompt(repo, commits)
        data_source = "github-fallback"

    provider = "ollama" if req.model_alias == OLLAMA_ALIAS else "bedrock"
    lf = _langfuse()
    trace = generation = None
    model_id = f"ollama/{ollama_client.OLLAMA_MODEL}" if provider == "ollama" else MODELS.get(req.model_alias)
    if lf:
        trace = lf.trace(name="debt-analysis", input={"model": req.model_alias, "project": project_key, "source": data_source})
        generation = trace.generation(name=f"{provider}-invoke", model=model_id, input=prompt)

    try:
        response_text, model_id, usage = await _invoke_alias(req.model_alias, prompt)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{provider.capitalize()} error: {e}")

    if generation:
        generation.end(output=response_text, usage=usage)
    if trace:
        trace.update(output=response_text)
    if lf:
        lf.flush()

    return {
        "model_alias": req.model_alias,
        "response": response_text,
        "data_source": data_source
    }