from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import List

from src.models.schemas import (
    UploadResponse,
    QueryRequest,
    QueryResponse,
    Source,
)
from src.services.gemini_service import GeminiService
from src.services.file_service import FileService
from src.services.prompt_service import PromptService
from src.utils.exceptions import GeminiServiceError
from src.utils.logger import logger

router = APIRouter()


# -------- Dependencias simples tipo singleton -------- #

_gemini_service = GeminiService()
_prompt_service = PromptService()
_file_service = FileService(_gemini_service)


def get_gemini_service() -> GeminiService:
    return _gemini_service


def get_prompt_service() -> PromptService:
    return _prompt_service


def get_file_service() -> FileService:
    return _file_service


# ------------------- ENDPOINTS ------------------- #

@router.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@router.post("/create-store", response_model=dict)
def create_store(
    payload: dict,
    gemini_service: GeminiService = Depends(get_gemini_service),
):
    display_name = payload.get("display_name")
    if not display_name:
        raise HTTPException(status_code=400, detail="display_name requerido")

    try:
        store_name = gemini_service.create_store(display_name=display_name)
    except GeminiServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"store_name": store_name}


@router.post(
    "/upload-files/{store_name}",
    response_model=UploadResponse,
)
async def upload_files(
    store_name: str,
    files: List[UploadFile] = File(...),
    file_service: FileService = Depends(get_file_service),
):
    """
    Recibe múltiples archivos, los valida con el módulo de limpieza
    y sube los que pasen el filtro.
    """
    # Nota: FileService es síncrono; FastAPI permite llamarlo así
    resp = file_service.process_and_upload(store_name=store_name, files=files)
    return resp


@router.post("/query/{store_name}", response_model=QueryResponse)
async def query_store(
    store_name: str,
    body: QueryRequest,
    gemini_service: GeminiService = Depends(get_gemini_service),
    prompt_service: PromptService = Depends(get_prompt_service),
):
    """
    Realiza una consulta RAG sobre un File Search store.
    """
    _, system_instruction = prompt_service.get_system_instruction(
        profile=body.prompt_profile
    )

    try:
        raw_response = gemini_service.query_with_rag(
            store_name=store_name,
            query=body.query,
            system_instruction=system_instruction,
        )
    except GeminiServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # ---- Parseo muy conservador del response ---- #
    # MVP: usamos response.text como answer y dejamos sources vacío
    # o intentamos extraer de citations si están presentes.
    answer_text = getattr(raw_response, "text", "")

    sources: List[Source] = []

    # Intento de extracción de citas (puede necesitar ajuste según el SDK real)
    try:
        candidates = getattr(raw_response, "candidates", [])
        for cand in candidates:
            citations = getattr(cand, "citations", []) or []
            for c in citations:
                meta = getattr(c, "metadata", {}) or {}
                sources.append(
                    Source(
                        filename=meta.get("file_name", "desconocido"),
                        page=meta.get("page", None),
                        snippet=meta.get("snippet", ""),
                    )
                )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"No se pudieron parsear citas de Gemini: {exc}")

    return QueryResponse(answer=answer_text, sources=sources)
