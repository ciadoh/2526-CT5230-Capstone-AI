from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import dashboard, sonarqube, github, bedrock, mlflow_router, langfuse_router, config, scan, ollama_router, ml_router

app = FastAPI(
    title="TechDebt AI",
    description="AI-driven technical debt management dashboard",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config.router)
app.include_router(scan.router)
app.include_router(dashboard.router)
app.include_router(sonarqube.router)
app.include_router(github.router)
app.include_router(bedrock.router)
app.include_router(mlflow_router.router)
app.include_router(langfuse_router.router)
app.include_router(ollama_router.router)
app.include_router(ml_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"message": "TechDebt AI API", "docs": "/docs"}
