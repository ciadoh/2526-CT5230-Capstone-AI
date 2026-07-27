import os
import httpx
from app.config import settings

SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() != "false"


def _auth() -> tuple[str, str]:
    return (settings.sonarqube_token, "")


async def get_issues(project_key: str, page_size: int = 100) -> dict:
    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        r = await client.get(
            f"{settings.sonarqube_url}/api/issues/search",
            params={
                "componentKeys": project_key,
                "ps": page_size,
                "facets": "types,severities,tags",
                "resolved": "false",
            },
            auth=_auth(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()


async def get_metrics(project_key: str) -> dict:
    metrics = [
        "complexity", "cognitive_complexity", "duplicated_lines_density",
        "sqale_rating", "reliability_rating", "security_rating",
        "bugs", "vulnerabilities", "code_smells",
        "sqale_index", "coverage", "lines", "ncloc",
    ]
    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        r = await client.get(
            f"{settings.sonarqube_url}/api/measures/component",
            params={
                "component": project_key,
                "metricKeys": ",".join(metrics),
            },
            auth=_auth(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()


async def get_hotspots(project_key: str) -> dict:
    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        r = await client.get(
            f"{settings.sonarqube_url}/api/hotspots/search",
            params={"projectKey": project_key, "ps": 50},
            auth=_auth(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()


FILE_METRICS = [
    "bugs", "vulnerabilities", "code_smells",
    "cognitive_complexity", "duplicated_lines_density", "sqale_rating",
    "sqale_index", "lines", "ncloc",
    "blocker_violations", "critical_violations", "major_violations",
    "minor_violations", "info_violations",
]


async def get_component_tree(project_key: str) -> list[dict]:
    """Return per-file metrics for ALL files in the project, paginating through results."""
    page_size = 500  # SonarQube max
    result = []
    page = 1

    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        while True:
            r = await client.get(
                f"{settings.sonarqube_url}/api/measures/component_tree",
                params={
                    "component": project_key,
                    "metricKeys": ",".join(FILE_METRICS),
                    "qualifiers": "FIL",
                    "ps": page_size,
                    "p": page,
                    "strategy": "leaves",
                },
                auth=_auth(),
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            components = data.get("components", [])
            for c in components:
                flat = {m["metric"]: m.get("value", "0") for m in c.get("measures", [])}
                result.append({"key": c["key"], "name": c.get("name", c["key"]), "metrics": flat})

            paging = data.get("paging", {})
            total = paging.get("total", 0)
            if page * page_size >= total:
                break
            page += 1

    return result


async def get_history(project_key: str, metric: str = "sqale_index") -> dict:
    async with httpx.AsyncClient(verify=SSL_VERIFY) as client:
        r = await client.get(
            f"{settings.sonarqube_url}/api/measures/search_history",
            params={"component": project_key, "metrics": metric, "ps": 30},
            auth=_auth(),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
