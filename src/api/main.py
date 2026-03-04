"""FastAPI application."""

import uvicorn
from fastapi import FastAPI
from sqlalchemy import text

from src.api.routes import parking, signs, snow
from src.api.schemas import HealthOut
from src.config import settings
from src.database import async_engine

app = FastAPI(title="ParkWise MTL", version="0.1.0")

app.include_router(parking.router)
app.include_router(signs.router)
app.include_router(snow.router)


@app.get("/health", response_model=HealthOut)
async def health():
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return HealthOut(status="ok", db_connected=True)
    except Exception:
        return HealthOut(status="degraded", db_connected=False)


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
