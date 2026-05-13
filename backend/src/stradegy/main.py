from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from stradegy.config import settings
from stradegy.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init database
    await init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": settings.app_version}


@app.get("/api/account/summary")
async def account_summary():
    return {
        "equity": 0.0,
        "buying_power": 0.0,
        "tax_reserve": 0.0,
        "day_pnl": 0.0,
        "open_positions": 0,
        "mode": "paper" if settings.paper_trading else "live",
        "autonomy": settings.autonomy_mode,
        "tier": "micro",
    }


# Serve PWA static files in production
static_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


def main():
    import uvicorn
    uvicorn.run(
        "stradegy.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
