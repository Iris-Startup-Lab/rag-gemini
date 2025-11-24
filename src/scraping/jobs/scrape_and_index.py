import asyncio
import os
from datetime import datetime
from pathlib import Path
from src.scraping.models import ScraperSource
from src.scraping.playwright_scraper import fetch_pdf_links
from src.scraping.file_downloader import download_new_files
from src.services.gemini_service import GeminiService
from src.preprocessing.cleaner import filter_valid_files  # suponiendo existe algo así

MIN_FILES_TO_INDEX = 5        # configurable por env
MAX_WAIT_DAYS = 7             # configurable por env
META_FILE = Path("data/meta/scraper_meta.json")

def load_sources_from_yaml() -> list[ScraperSource]:
    import yaml
    from pathlib import Path
    cfg = yaml.safe_load(Path("configs/scraper_sources.yaml").read_text())
    return [ScraperSource(**raw) for raw in cfg["sources"]]

async def process_source(source: ScraperSource) -> list[Path]:
    pdf_urls = await fetch_pdf_links(source)
    new_files = download_new_files(pdf_urls, category=source.category)
    return new_files

def run_scraper_and_maybe_index() -> None:
    sources = load_sources_from_yaml()

    # 1) Scraping + descarga
    new_files_by_store: dict[str, list[Path]] = {}

    async def scrape_all():
        for src in sources:
            new_files = await process_source(src)
            if not new_files:
                continue
            store_name = os.environ[src.store_env]
            new_files_by_store.setdefault(store_name, []).extend(new_files)

    asyncio.run(scrape_all())

    # 2) Decidir si indexar y llamar a Gemini
    gemini = GeminiService()

    for store_name, paths in new_files_by_store.items():
        valid_files = filter_valid_files(paths)  # usa el cleaner ya existente
        if not should_index_now(store_name, valid_files):
            continue
        gemini.upload_files_to_store(
            store_name=store_name,
            file_paths=[str(p) for p in valid_files],
            wait_for_index=True,
        )
        update_meta_after_index(store_name)

def should_index_now(store_name: str, new_files: list[Path]) -> bool:
    if not new_files:
        return False

    meta = load_meta()  # lee JSON con {store_name: last_index_iso}
    last_str = meta.get(store_name)
    last_dt = datetime.fromisoformat(last_str) if last_str else None
    now = datetime.utcnow()

    enough_files = len(new_files) >= MIN_FILES_TO_INDEX
    waited_enough = (
        last_dt is None or (now - last_dt).days >= MAX_WAIT_DAYS
    )

    return enough_files or waited_enough
