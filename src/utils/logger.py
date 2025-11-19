from loguru import logger
import sys


def setup_logging() -> None:
    """
    Configura loguru para toda la app.
    """
    logger.remove()  # Quita handlers por defecto
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    # Ejemplo de logging de arranque
    logger.info("Logging inicializado")
