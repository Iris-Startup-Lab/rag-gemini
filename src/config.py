from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Clave de Gemini
    GEMINI_API_KEY: str = Field(..., description="API key de Gemini")

    # IDs de stores (opcional, útiles para mapear 'leyes', 'tramites', 'general')
    GEMINI_STORE_LEYES: str | None = None
    GEMINI_STORE_TRAMITES: str | None = None
    GEMINI_STORE_GENERAL: str | None = None

    # Límite de tamaño de archivos para la capa de filtro (MB)
    MAX_FREE_TIER_FILE_SIZE_MB: int = Field(
        20,
        description="Tamaño máximo en MB antes de subir a File Search (control costos).",
    )

    # Modelo por defecto para RAG
    GEMINI_MODEL: str = Field(
        "gemini-2.5-flash",
        description="Modelo por defecto para consultas RAG con File Search.",
    )

    APP_ENV: str = Field(
        "dev",
        description="Entorno de ejecución: dev | staging | prod",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instancia global de settings
settings = Settings()
