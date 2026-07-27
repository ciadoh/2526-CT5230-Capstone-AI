from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://admin:changeme@postgres:5432/appdb"
    sonarqube_url: str = "http://sonarqube:9000"
    sonarqube_token: str = ""
    mlflow_tracking_uri: str = "http://mlflow:5000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://langfuse:3000"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"
    ollama_host: str = "http://localhost:11434"
    github_token: str = ""
    target_repo: str = "expressjs/express"

    class Config:
        env_file = ".env"


settings = Settings()
