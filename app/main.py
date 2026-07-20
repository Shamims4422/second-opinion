from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.evaluations import router as evaluations_router
from app.api.experiences import router as experiences_router
from app.database import Base, engine
from app.exceptions import CriticLoopError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="CriticLoop",
    description="Experience-based risk scoring for AI-agent actions.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(experiences_router)
app.include_router(evaluations_router)


@app.exception_handler(CriticLoopError)
async def criticloop_error_handler(request: Request, exc: CriticLoopError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}
