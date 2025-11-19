import math
from typing import Tuple, Optional
from fastapi import UploadFile

from src.config import settings
from src.utils.exceptions import FileTooLargeError, UnsupportedFileTypeError

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


def _get_extension(filename: str) -> str:
    dot_idx = filename.rfind(".")
    if dot_idx == -1:
        return ""
    return filename[dot_idx:].lower()


def _get_file_size_mb(file: UploadFile) -> float:
    """
    Intenta obtener el tamaño del archivo en MB usando el objeto subyacente.
    Nota: esto lee el stream para medir tamaño y regresa el puntero al inicio.
    """
    file.file.seek(0, 2)        # Ir al final
    size_bytes = file.file.tell()
    file.file.seek(0)           # Volver al inicio
    size_mb = size_bytes / (1024 * 1024)
    # Redondeo a 2 decimales más por estética de respuesta
    return math.ceil(size_mb * 100) / 100.0


def validate_file(file: UploadFile) -> Tuple[bool, Optional[str], Optional[float]]:
    """
    Valida un archivo antes de subirlo a Gemini.

    Returns:
        (accepted, reason, size_mb)
        - accepted: True -> pasar; False -> descartar.
        - reason: motivo en texto si fue descartado.
        - size_mb: tamaño estimado del archivo.
    """
    filename = file.filename or "unknown"
    ext = _get_extension(filename)
    size_mb = _get_file_size_mb(file)

    max_mb = settings.MAX_FREE_TIER_FILE_SIZE_MB

    # 1) Tamaño
    if size_mb > max_mb:
        return (
            False,
            f"FILE_TOO_LARGE: {size_mb} MB > {max_mb} MB",
            size_mb,
        )

    # 2) Extensión
    if ext not in SUPPORTED_EXTENSIONS:
        return (
            False,
            f"UNSUPPORTED_EXTENSION: {ext or 'NO_EXT'}",
            size_mb,
        )

    return True, None, size_mb
