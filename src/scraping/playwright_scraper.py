# src/scraping/playwright_scraper.py
from __future__ import annotations

import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from playwright.async_api import async_playwright  # requiere `pip install playwright`
from src.scraping.file_downloader import download_new_files
from src.scraping import DATA_ROOT

logger = logging.getLogger(__name__)


async def collect_links_from_page(url: str, link_selector: str) -> List[str]:
    """
    Helper genérico:
    - Abre una página con Chromium.
    - Espera a `networkidle`.
    - Extrae los `href` de todos los elementos que matchean `link_selector`.
    """
    logger.info("Navegando a %s para recolectar links (%s)", url, link_selector)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")

        links = await page.eval_on_selector_all(
            link_selector,
            "elements => elements.map(e => e.href)"
        )

        await browser.close()

    # Normalizamos y limpiamos
    clean_links = [l.strip() for l in links if isinstance(l, str) and l.strip()]
    logger.info("Links encontrados en %s: %s", url, len(clean_links))
    return clean_links


class BaseScraper(ABC):
    """
    Clase base para todos los scrapers:

    - Define `id`, `name`, `category`, `store_env`, `base_url`.
    - Expone `store_name` (lee env var) y `data_dir`.
    - Implementa `run()`:
        1) llama a `fetch_pdf_urls()`
        2) descarga archivos nuevos a data/<category>/
        3) devuelve lista de Paths nuevos
    """

    # Cada subclase debe sobrescribir estas propiedades de clase
    id: str
    name: str
    category: str          # p.ej. "leyes", "tramites", "info", "glosario"
    store_env: str         # p.ej. "GEMINI_STORE_LEYES"
    base_url: str

    def __init__(self) -> None:
        self.data_dir: Path = DATA_ROOT / self.category

    @property
    def store_name(self) -> str:
        value = os.getenv(self.store_env)
        if not value:
            raise RuntimeError(
                f"Variable de entorno {self.store_env} no está definida "
                f"para el scraper {self.id}"
            )
        return value

    @abstractmethod
    async def fetch_pdf_urls(self) -> List[str]:
        """
        Cada scraper implementa su lógica para:
        - navegar la página
        - encontrar enlaces a PDFs
        - devolver lista de URLs (strings)
        """
        raise NotImplementedError

    async def run(self) -> List[Path]:
        """
        Orquesta el flujo de un scraper concreto:
        1) obtiene URLs de PDFs
        2) descarga archivos nuevos
        """
        logger.info("Ejecutando scraper %s (%s)", self.id, self.name)
        urls = await self.fetch_pdf_urls()
        if not urls:
            logger.info("Scraper %s no encontró nuevas URLs", self.id)
            return []

        new_files = download_new_files(urls, category=self.category)
        logger.info(
            "Scraper %s terminó. Nuevos archivos: %s",
            self.id,
            len(new_files),
        )
        return new_files
