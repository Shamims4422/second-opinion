from fastapi import FastAPI

app = FastAPI(
    title="CriticLoop",
    description="Experience-based risk scoring for AI-agent actions.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}
