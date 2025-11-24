# src/scraping/__init__.py
from pathlib import Path

# /.../project/src/scraping/__init__.py
SCRAPING_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRAPING_DIR.parent          # /.../project/src
PROJECT_ROOT = SRC_DIR.parent          # /.../project
DATA_ROOT = PROJECT_ROOT / "data"      # /.../project/data
CONFIGS_DIR = SRC_DIR / "configs"      # /.../project/src/configs

__all__ = ["SCRAPING_DIR", "SRC_DIR", "PROJECT_ROOT", "DATA_ROOT", "CONFIGS_DIR"]
