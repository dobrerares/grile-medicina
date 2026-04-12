import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routes import router
from admin_routes import router as admin_router
from report_routes import router as report_router
import quiz as quiz_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and load data
    Base.metadata.create_all(bind=engine)
    quiz_service.load_data()
    screenshots_dir = os.environ.get("SCREENSHOT_PATH", "/app/data/screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)
    yield
    # Shutdown: nothing to clean up


app = FastAPI(
    title="Grile Medicina API",
    description="Quiz API for Romanian medical biology exam questions",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(admin_router)
app.include_router(report_router)
