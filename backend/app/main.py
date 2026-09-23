from fastapi import FastAPI

from backend.app.models.apartment import Apartment
from backend.app.routers import apartments
from backend.app.routers import users

app = FastAPI(
    title="Smart Apartment API",
    description="Backend API for the Smart Apartment Management System",
    version="0.1.0",
)

app.include_router(apartments.router)
app.include_router(users.router)

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
