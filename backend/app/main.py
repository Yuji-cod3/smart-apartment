from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from backend.app.database.dependencies import get_db
from backend.app.database.connection import Base
from backend.app.routers import dashboard

from backend.app.routers import apartments
from backend.app.routers import devices
from backend.app.routers import rooms
from backend.app.routers import users
from backend.app.routers import automations
from backend.app.routers import rent

app = FastAPI(
    title="Smart Apartment API",
    description="Backend API for the Smart Apartment Management System",
    version="0.1.0",
)

app.include_router(apartments.router)
app.include_router(rooms.router)
app.include_router(devices.router)
app.include_router(users.router)
app.include_router(automations.router)
app.include_router(rent.router)
app.include_router(dashboard.router)

frontend = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/dashboard/assets", StaticFiles(directory=frontend / "assets"), name="dashboard-assets")


@app.get("/dashboard", include_in_schema=False)
@app.get("/dashboard/", include_in_schema=False)
def dashboard_page():
    return FileResponse(frontend / "index.html", headers={"Cache-Control": "no-store"})

@app.get("/")
def root():
    return {
        "system": "Smart Apartment Management System",
        "status": "online",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@app.get("/health/ready", tags=["Health"])
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        # Read every application table so missing migrations fail readiness.
        for table in Base.metadata.sorted_tables:
            db.execute(table.select().limit(0))
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, "Database is not ready.")
    return {"status": "ready"}
