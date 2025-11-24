# src/scraping/jobs/scrape_and_index.py
import logging

from src.scraping.runner import run_scraper_and_maybe_index
from src.scraping.playwright_scraper import BaseScraper

from src.scraping.strategies.consar_leyes import ConsarLeyesScraper
from src.scraping.strategies.consar_tramites import ConsarTramitesScraper
from src.scraping.strategies.sep_glosario import SepGlosarioScraper
# from src.scraping.strategies.ine_docs import IneDocsScraper  # cuando lo tengas listo

logger = logging.getLogger(__name__)

SCRAPERS: list[BaseScraper] = [
    ConsarLeyesScraper(),
    ConsarTramitesScraper(),
    SepGlosarioScraper(),
    # IneDocsScraper(),
]


def main() -> None:
    if not SCRAPERS:
        logger.warning("No hay scrapers registrados en SCRAPERS.")
        return

    run_scraper_and_maybe_index(SCRAPERS)


if __name__ == "__main__":
    main()
