from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jobly.api.routes.health import router as health_router
from jobly.api.routes.jobs import router as jobs_router
from jobly.config import get_settings
from jobly.db.pool import close_pool, open_pool
from jobly.logging_config import configure_logging


configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    open_pool()
    yield
    close_pool()


app = FastAPI(title="Jobly API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(jobs_router)
