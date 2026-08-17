from app.config import settings

AVAILABLE_REPOS = [
    "expressjs/express",
    "ciadoh/NodeGoat",
    "ciadoh/juice-shop",
    "ciadoh/WebGoat",
    "ciadoh/2526-CT5230-Capstone-AI",
]

# Repos where the authenticated GitHub token has write access (PRs allowed)
PR_ENABLED_REPOS = {"ciadoh/NodeGoat", "ciadoh/juice-shop", "ciadoh/WebGoat", "ciadoh/2526-CT5230-Capstone-AI"}

_active_repo: str | None = None


def get_active_repo() -> str:
    return _active_repo or settings.target_repo


def set_active_repo(repo: str) -> None:
    global _active_repo
    _active_repo = repo
