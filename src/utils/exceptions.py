class GeminiServiceError(Exception):
    """Errores genéricos al interactuar con Gemini."""


class FileTooLargeError(Exception):
    """Archivo excede el límite permitido de tamaño."""


class UnsupportedFileTypeError(Exception):
    """Extensión de archivo no soportada para el pipeline."""
