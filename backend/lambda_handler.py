"""HTTP Lambda entry point for the FastAPI app."""

from runtime_bootstrap import bootstrap_runtime

bootstrap_runtime()

from mangum import Mangum

from src.api.main import app

handler = Mangum(app, lifespan="auto")
