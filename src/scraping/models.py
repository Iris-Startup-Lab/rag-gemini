from pydantic import BaseModel, HttpUrl
from typing import Optional

class ScraperSource(BaseModel):
    id: str
    name: str
    category: str         # leyes / tramites / info / glosario...
    store_env: str        # p.ej. "GEMINI_STORE_LEYES"
    type: str             # "listing_page", "direct_pdf", etc.
    base_url: HttpUrl
    link_selector: str
    follow_pagination: bool = False
