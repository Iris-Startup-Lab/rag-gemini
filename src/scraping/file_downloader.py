from pathlib import Path
from typing import Iterable, List
import hashlib
import logging

import requests

from src.scraping import DATA_ROOT

logger = logging.getLogger(__name__)

def download_new_files(pdf_urls: Iterable[str], category: str) -> List[Path]:
    """
    Descarga PDFs que no existan aún en data/<category>/.

    - Nombra los archivos con: <hash10>_<nombre_original.pdf>
    - Devuelve la lista de rutas de archivos NUEVOS (no incluye los ya existentes).
    """
    target_dir = DATA_ROOT / category
    target_dir.mkdir(parents=True, exist_ok=True)

    new_files: List[Path] = []

    for url in pdf_urls:
        url = url.strip()
        if not url:
            continue

        url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
        filename = url.split("/")[-1] or "file.pdf"
        if not filename.lower().endswith(".pdf"):
            # Si más adelante quieres TXT, DOCX, etc., aquí puedes ampliarlo.
            logger.debug("Saltando URL no-PDF: %s", url)
            continue

        path = target_dir / f"{url_hash}_{filename}"

        if path.exists():
            logger.debug("Archivo ya existe, no se descarga: %s", path.name)
            continue

        logger.info("Descargando archivo nuevo: %s -> %s", url, path)
        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with path.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
        except Exception as exc:
            logger.exception("Error descargando %s: %s", url, exc)
            if path.exists():
                path.unlink(missing_ok=True)
            continue

        new_files.append(path)

    return new_files
