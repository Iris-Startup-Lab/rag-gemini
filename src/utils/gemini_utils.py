from typing import List
from src.models.schemas import Source
from src.utils.logger import logger

MAX_SNIPPET_CHARS = 160  # Máximo de caracteres para el snippet


def extract_sources_from_grounding(raw_response) -> List[Source]:
    """
    Extrae las fuentes desde grounding_metadata (File Search) de Gemini 2.5.
    Devuelve una lista de Source(filename, page, snippet).
    """
    sources: List[Source] = []

    try:
        # 1. Obtener candidatos
        candidates = getattr(raw_response, "candidates", [])
        if not candidates:
            logger.info("🔎 No hay candidates en la respuesta de Gemini.")
            return sources

        candidate = candidates[0]

        # 2. Acceder a grounding_metadata
        grounding = getattr(candidate, "grounding_metadata", None)
        if not grounding:
            logger.info("🔎 Respuesta sin grounding_metadata.")
            return sources

        chunks = getattr(grounding, "grounding_chunks", None)
        if not chunks:
            logger.info("🔎 grounding_metadata sin grounding_chunks.")
            return sources

        # 3. Extraer retrieved_context por chunk
        for chunk in chunks:
            rc = getattr(chunk, "retrieved_context", None)
            if not rc:
                continue

            title = getattr(rc, "title", None)
            uri = getattr(rc, "uri", None)

            filename = title or uri or "desconocido"

            # Cambiar snippet a vacío
            sources.append(
                Source(
                    filename=filename,
                    page=None,      # FileSearch todavía no expone página
                    snippet="",   # <--- vacío para no saturar el front
                )
            )

        # 4. Limpiar duplicados por filename
        unique = {}
        for s in sources:
            if s.filename not in unique:
                unique[s.filename] = s

        cleaned = list(unique.values())
        logger.info(f"📚 Fuentes extraídas (sin snippet): {cleaned}")

        return cleaned

    except Exception as exc:
        logger.warning(f"⚠️ Error al parsear grounding_metadata: {exc}")
        return []
