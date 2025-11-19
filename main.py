from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router as api_router
from src.utils.logger import setup_logging


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title="RAG-Gemini Backend",
        version="0.1.0",
        description="Backend FastAPI para RAG con Gemini File Search.",
    )

    # CORS básico (ajusta orígenes cuando tengas frontend)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # ⚠️ para dev; en prod restringir
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    return app


app = create_app()
