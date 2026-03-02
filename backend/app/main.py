from fastapi import FastAPI

from app.api.routes import router as api_router

app = FastAPI(title="AutoOps AI Backend", version="0.1.0")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix="/api")
