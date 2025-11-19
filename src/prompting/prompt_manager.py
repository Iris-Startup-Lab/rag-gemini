from pathlib import Path
from typing import Any, Dict

import yaml

from src.utils.logger import logger

BASE_DIR = Path(__file__).resolve().parents[2]
PROMPTS_DIR = BASE_DIR / "prompts"


class PromptNotFoundError(Exception):
    pass


def load_prompt(profile: str = "default") -> Dict[str, Any]:
    """
    Carga un prompt YAML de la carpeta /prompts.

    Estructura sugerida del YAML:
    ---
    system_instruction: |
      Texto de instrucciones de sistema...
    """
    path = PROMPTS_DIR / f"{profile}.yaml"

    if not path.exists():
        logger.warning(f"Prompt profile '{profile}' no encontrado. Usando 'default'.")
        path = PROMPTS_DIR / "default.yaml"

        if not path.exists():
            raise PromptNotFoundError(
                f"No se encontró default.yaml en {PROMPTS_DIR}"
            )

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data
