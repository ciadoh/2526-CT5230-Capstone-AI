import json
import os
import boto3
from botocore.config import Config
from app.config import settings

SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() != "false"

# Models available via Bedrock for comparison
MODELS = {
    "nova-micro": "eu.amazon.nova-micro-v1:0",
    "nova-lite": "eu.amazon.nova-lite-v1:0",
    "nova-pro": "eu.amazon.nova-pro-v1:0",
    "mistral": "mistral.mixtral-8x7b-instruct-v0:1",
}


def _client():
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_default_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        verify=SSL_VERIFY,
    )


def _extract_usage(response: dict) -> dict:
    """Bedrock reports token counts as response headers for every provider
    (x-amzn-bedrock-input/output-token-count), so this works uniformly across
    Anthropic/Nova/Mistral without parsing provider-specific body shapes."""
    headers = response.get("ResponseMetadata", {}).get("HTTPHeaders", {})

    def _int(key):
        try:
            return int(headers.get(key))
        except (TypeError, ValueError):
            return None

    input_tokens = _int("x-amzn-bedrock-input-token-count")
    output_tokens = _int("x-amzn-bedrock-output-token-count")
    total = None
    if input_tokens is not None or output_tokens is not None:
        total = (input_tokens or 0) + (output_tokens or 0)
    return {"input": input_tokens, "output": output_tokens, "total": total, "unit": "TOKENS"}


def invoke_model(model_id: str, prompt: str, max_tokens: int = 1024) -> tuple[str, dict]:
    client = _client()

    # Strip regional prefix (eu., us., ap.) for provider detection
    base_id = model_id.split(".", 1)[-1] if model_id[:3] in ("eu.", "us.", "ap.") else model_id

    if "anthropic" in base_id:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
    elif "amazon.nova" in base_id:
        body = {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.3},
        }
    elif "mistral" in base_id:
        body = {
            "prompt": f"<s>[INST] {prompt} [/INST]",
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
    else:
        raise ValueError(f"Unsupported model: {model_id}")

    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    usage = _extract_usage(response)

    if "anthropic" in base_id:
        text = result["content"][0]["text"]
    elif "amazon.nova" in base_id:
        text = result["output"]["message"]["content"][0]["text"]
    elif "mistral" in base_id:
        text = result["outputs"][0]["text"]
    else:
        text = str(result)
    return text, usage


def build_debt_prompt(issues: list[dict], metrics: dict) -> str:
    top_issues = issues[:5]
    issue_summary = "\n".join(
        f"- [{i.get('severity', 'UNKNOWN')}] {i.get('message', '')} in {i.get('component', '')}"
        for i in top_issues
    )
    return f"""You are a senior software engineer reviewing technical debt in a codebase.

Key metrics:
- Code smells: {metrics.get('code_smells', 'N/A')}
- Bugs: {metrics.get('bugs', 'N/A')}
- Vulnerabilities: {metrics.get('vulnerabilities', 'N/A')}
- Technical debt: {metrics.get('technical_debt', 'N/A')} minutes
- Duplication: {metrics.get('duplicated_lines_density', 'N/A')}%
- Maintainability rating: {metrics.get('maintainability_rating', 'N/A')}

Top issues:
{issue_summary}

Provide a concise analysis (3-5 bullet points) covering:
1. The most critical areas of concern
2. Specific refactoring recommendations
3. Estimated effort to address the highest-risk items
Keep your response practical and actionable."""
