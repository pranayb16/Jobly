from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jobly.api.routes.companies import router as companies_router
from jobly.api.routes.health import router as health_router
from jobly.api.routes.roles import router as roles_router
from jobly.api.routes.skills import router as skills_router
from jobly.api.routes.trends import router as trends_router
from jobly.config import get_settings
from jobly.db.pool import close_pool, open_pool
from jobly.logging_config import configure_logging
from jobly.products.jobs.routes import router as jobs_router


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
app.include_router(companies_router)
app.include_router(trends_router)
app.include_router(roles_router)
app.include_router(skills_router)
