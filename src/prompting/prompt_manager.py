# src/prompting/prompt_manager.py

from pathlib import Path
from typing import Dict, Any

import yaml

# Ruta base al archivo de configuración de prompts
PROMPT_CONFIG_PATH = Path("prompts") / "prompt_config.yaml"


def _load_config() -> Dict[str, Any]:
    """
    Carga el archivo prompts/prompt_config.yaml y devuelve el diccionario de configuración.
    """
    if not PROMPT_CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de configuración de prompts: {PROMPT_CONFIG_PATH}"
        )

    with PROMPT_CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    if "profiles" not in config or not isinstance(config["profiles"], dict):
        raise ValueError(
            "El archivo prompt_config.yaml debe contener una clave 'profiles' con un dict de perfiles."
        )

    return config


def _resolve_profile_config(profile: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dado un nombre de perfil y la configuración completa, devuelve la sección de config
    correspondiente. Si el perfil no existe, usa 'default'. Si tampoco existe, usa el
    primer perfil definido.
    """
    profiles = config["profiles"]

    if profile in profiles:
        profile_cfg = profiles[profile]
    elif "default" in profiles:
        profile_cfg = profiles["default"]
    else:
        # Fallback: primer perfil definido
        profile_cfg = next(iter(profiles.values()))

    return profile_cfg


def _read_file(path_str: str) -> str:
    """
    Lee un archivo de texto UTF-8 dado un path (puede ser absoluto o relativo al root del repo).
    """
    path = Path(path_str)
    if not path.is_absolute():
        # Asumimos ejecución desde la raíz del proyecto
        path = Path.cwd() / path

    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de prompt: {path}")

    return path.read_text(encoding="utf-8")


# -------------------------------------------------------------------------
# ⚙️ API PRINCIPAL USADA POR prompt_service: load_prompt(profile)
# -------------------------------------------------------------------------
def load_prompt(profile: str) -> Dict[str, str]:
    """
    Carga el prompt según el perfil indicado.

    Devuelve un dict con al menos:
      - system_instruction: texto de instrucciones de sistema
      - context_template: plantilla donde se insertará el contexto ({{context}})

    Esto mantiene compatibilidad con el import:
      from src.prompting.prompt_manager import load_prompt
    """
    config = _load_config()
    profile_cfg = _resolve_profile_config(profile, config)

    # Soportamos dos formas:
    # 1) perfil como string: "prompts/base_prompt.txt"
    # 2) perfil como dict: { system_instruction_file: "...", context_template_file: "..." }
    if isinstance(profile_cfg, str):
        system_instruction_file = profile_cfg
        context_template_file = None
    elif isinstance(profile_cfg, dict):
        system_instruction_file = profile_cfg.get("system_instruction_file")
        context_template_file = profile_cfg.get("context_template_file")
    else:
        raise ValueError(
            f"Formato de perfil inválido en prompt_config.yaml para perfil '{profile}'."
        )

    if not system_instruction_file:
        raise ValueError(
            f"El perfil '{profile}' no tiene 'system_instruction_file' definido en prompt_config.yaml."
        )

    system_instruction = _read_file(system_instruction_file)

    if context_template_file:
        context_template = _read_file(context_template_file)
    else:
        # Fallback sencillo si no se especificó plantilla
        context_template = "[DOCUMENTOS RELEVANTES]\n{{context}}"

    return {
        "system_instruction": system_instruction,
        "context_template": context_template,
    }


# -------------------------------------------------------------------------
# 🧱 Clase opcional (por si luego quieres usar un manager orientado a objetos)
# -------------------------------------------------------------------------
class PromptManager:
    """
    Versión orientada a objetos. No es obligatoria para que funcione el backend,
    pero puede ser útil más adelante.
    """

    def __init__(self, config_path: str | Path = PROMPT_CONFIG_PATH):
        self.config_path = Path(config_path)
        self.config = _load_config()

    def get_prompt(self, profile: str) -> Dict[str, str]:
        """
        Devuelve el mismo dict que load_prompt(profile).
        """
        return load_prompt(profile)

    def get_system_instruction(self, profile: str) -> str:
        return self.get_prompt(profile)["system_instruction"]

    def get_context_template(self, profile: str) -> str:
        return self.get_prompt(profile)["context_template"]
