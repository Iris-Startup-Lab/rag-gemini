# src/scraping/runner.py
from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

from src.scraping import DATA_ROOT
from src.scraping.playwright_scraper import BaseScraper
from src.preprocessing.cleaner import filter_valid_files
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# Configurables por env (con defaults razonables)
MIN_FILES_TO_INDEX = int(os.getenv("SCRAPER_MIN_FILES_TO_INDEX", "5"))
MAX_WAIT_DAYS = int(os.getenv("SCRAPER_MAX_WAIT_DAYS", "7"))

META_FILE = DATA_ROOT / "meta" / "scraper_meta.json"


def load_meta() -> Dict[str, str]:
    """
    Lee el archivo JSON con el último timestamp de indexado por store.
    Formato: { "store_name": "2025-01-01T12:34:56.789Z", ... }
    """
    if not META_FILE.exists():
        return {}
    try:
        return json.loads(META_FILE.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("No se pudo leer META_FILE, se reinicia metadata.")
        return {}


def update_meta_after_index(store_name: str) -> None:
    """
    Actualiza el timestamp de último indexado para un store.
    """
    meta = load_meta()
    meta[store_name] = datetime.utcnow().isoformat()
    META_FILE.parent.mkdir(parents=True, exist_ok=True)
    META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("META_FILE actualizado para store %s", store_name)


def should_index_now(store_name: str, new_files: List[Path]) -> bool:
    """
    Decide si se debe lanzar indexado para un store:
    - True si:
        * hay archivos nuevos Y
        * (len(new_files) >= MIN_FILES_TO_INDEX) O
        * ya pasó MAX_WAIT_DAYS desde el último indexado
    """
    if not new_files:
        return False

    meta = load_meta()
    last_str = meta.get(store_name)
    last_dt = datetime.fromisoformat(last_str) if last_str else None
    now = datetime.utcnow()

    enough_files = len(new_files) >= MIN_FILES_TO_INDEX
    waited_enough = last_dt is None or (now - last_dt).days >= MAX_WAIT_DAYS

    logger.info(
        "Decisión indexado para %s -> nuevos=%s, enough_files=%s, waited_enough=%s",
        store_name,
        len(new_files),
        enough_files,
        waited_enough,
    )

    return enough_files or waited_enough


async def _run_scrapers_async(scrapers: Iterable[BaseScraper]) -> Dict[str, List[Path]]:
    """
    Ejecuta todos los scrapers (secuencial por ahora) y agrupa
    los archivos nuevos por store_name.
    """
    from collections import defaultdict

    new_files_by_store: Dict[str, List[Path]] = defaultdict(list)

    for scraper in scrapers:
        try:
            new_files = await scraper.run()
        except Exception as exc:
            logger.exception("Scraper %s falló: %s", scraper.id, exc)
            continue

        if not new_files:
            continue

        store_name = scraper.store_name
        new_files_by_store[store_name].extend(new_files)

    return new_files_by_store


def run_scraper_and_maybe_index(scrapers: Iterable[BaseScraper]) -> None:
    """
    Punto de entrada de alto nivel:

    1) Ejecuta scrapers y agrupa nuevos archivos por store.
    2) Filtra archivos válidos con el cleaner existente.
    3) Decide si indexar según MIN_FILES_TO_INDEX y MAX_WAIT_DAYS.
    4) Llama a GeminiService.upload_files_to_store(...) cuando toca.
    """
    logger.info("==== Iniciando job de scraping + indexado automático ====")

    new_files_by_store = asyncio.run(_run_scrapers_async(scrapers))

    if not new_files_by_store:
        logger.info("No hubo nuevos archivos en ningún scraper. Nada que indexar.")
        return

    gemini = GeminiService()

    for store_name, paths in new_files_by_store.items():
        logger.info("Procesando store %s con %s archivos nuevos brutos", store_name, len(paths))

        # 1) Filtro de limpieza (tamaño, extensión) usando tu módulo actual
        valid_files = filter_valid_files(paths)
        if not should_index_now(store_name, valid_files):
            logger.info(
                "Se pospone indexado para %s (archivos válidos=%s)",
                store_name,
                len(valid_files),
            )
            continue

        logger.info(
            "Lanzando indexado en Gemini para %s (archivos válidos=%s)",
            store_name,
            len(valid_files),
        )

        gemini.upload_files_to_store(
            store_name=store_name,
            file_paths=[str(p) for p in valid_files],
            wait_for_index=True,
        )

        update_meta_after_index(store_name)

    logger.info("==== Job de scraping + indexado terminado ====")
