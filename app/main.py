from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="API para consulta do Portal da Transparência com automação Playwright.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router)


@app.get("/")
async def index() -> dict[str, str]:
    return {"app": settings.APP_NAME, "status": "online"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=False)
