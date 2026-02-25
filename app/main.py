"""Trolley Problem Arena - FastAPI application."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import router

app = FastAPI(
    title="Trolley Problem Arena",
    description="Multi-agent turn-based trolley problem mini-game API",
    version="1.0.0",
)

app.include_router(router)

# Serve static frontend
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def index():
    """Serve spectator UI."""
    ui = Path(__file__).parent / "static" / "index.html"
    if ui.exists():
        return FileResponse(ui)
    return {"message": "Trolley Problem Arena API", "docs": "/docs", "static": "Place index.html in app/static/"}


@app.get("/health")
def health():
    return {"status": "ok"}
