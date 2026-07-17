from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from topologia.server.routers import observacion, aprendizaje, memoria, dashboard

app = FastAPI(title="Topología Social", version="0.2.0")

base = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(base / "frontend" / "templates"))
static = base / "frontend" / "static"

if static.exists():
    app.mount("/static", StaticFiles(directory=str(static)), name="static")

app.include_router(observacion.router, prefix="/api", tags=["observacion"])
app.include_router(aprendizaje.router, prefix="/api", tags=["aprendizaje"])
app.include_router(memoria.router, prefix="/api", tags=["memoria"])
app.include_router(dashboard.router, tags=["dashboard"])


@app.get("/")
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")
