from typing import Tuple

from src.prompting.prompt_manager import load_prompt
from src.utils.logger import logger


class PromptService:
    """
    Capa fina sobre prompt_manager para centralizar lógica
    de cómo construimos las instrucciones de sistema.
    """

    def get_system_instruction(
        self,
        profile: str,
    ) -> Tuple[str, str]:
        """
        Regresa (profile_usado, system_instruction).
        Si no existe el perfil solicitado, cae a 'default'.
        """
        data = load_prompt(profile)
        system_instruction = data.get("system_instruction", "").strip()

        if not system_instruction:
            logger.warning(
                f"Prompt profile '{profile}' sin system_instruction. "
                "Usando texto mínimo de fallback."
            )
            system_instruction = (
                "Eres un asistente experto en el Sistema de Ahorro para el Retiro. "
                "Responde con precisión, en español, y siempre incluye una sección "
                "'Fuentes' con las citas de los documentos utilizados."
            )

        return profile, system_instruction
