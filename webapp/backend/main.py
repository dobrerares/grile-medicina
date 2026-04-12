from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routes import router
import quiz as quiz_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and load data
    Base.metadata.create_all(bind=engine)
    quiz_service.load_data()
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
