import time
from typing import List, Dict, Any

from google import genai
from google.genai import types  # type: ignore

from src.config import settings
from src.utils.logger import logger
from src.utils.exceptions import GeminiServiceError


class GeminiService:
    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise GeminiServiceError("GEMINI_API_KEY no configurada.")

        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = settings.GEMINI_MODEL

    # --------- STORES --------- #

    def create_store(self, display_name: str) -> str:
        """
        Crea un File Search Store y regresa su nombre (ID global).
        """
        try:
            store = self.client.file_search_stores.create(
                config={"display_name": display_name}
            )
            logger.info(f"FileSearchStore creado: {store.name}")
            return store.name
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error al crear FileSearchStore")
            raise GeminiServiceError(str(exc)) from exc

    # --------- UPLOAD / INDEX --------- #

    def upload_files_to_store(
        self,
        store_name: str,
        file_paths: List[str],
        wait_for_index: bool = True,
        poll_interval_sec: int = 5,
    ) -> List[str]:
        """
        Sube archivos locales a un File Search Store.

        file_paths: rutas locales donde ya guardamos los UploadFile.
        Regresa lista de operation_names (o vacía si algo falla).
        """
        operations: List[str] = []

        for path in file_paths:
            try:
                op_name = self.client.file_search_stores.upload_to_file_search_store(
                    file=path,
                    file_search_store_name=store_name,
                )
                logger.info(f"Upload iniciado para {path}: op={op_name}")
                operations.append(op_name)
            except Exception as exc:  # noqa: BLE001
                logger.exception(f"Error al subir archivo a FileSearchStore: {path}")
                # No levantamos excepción global para no frenar todo el batch
                continue

        if wait_for_index and operations:
            self._wait_for_operations(operations, poll_interval_sec=poll_interval_sec)

        return operations

    def _wait_for_operations(
        self,
        operation_names: List[str],
        poll_interval_sec: int = 5,
    ) -> None:
        """
        Espera a que todas las operaciones de import/index finalicen.
        """
        for op_name in operation_names:
            try:
                logger.info(f"Esperando operación de indexado: {op_name}")
                operation = self.client.operations.get(op_name)
                while not operation.done:
                    time.sleep(poll_interval_sec)
                    operation = self.client.operations.get(op_name)

                logger.info(f"Operación completada: {op_name}")
            except Exception as exc:  # noqa: BLE001
                logger.exception(f"Error al esperar operación: {op_name}: {exc}")

    # --------- QUERY RAG --------- #

    def query_with_rag(
        self,
        store_name: str,
        query: str,
        system_instruction: str,
        generation_config: Dict[str, Any] | None = None,
    ) -> Any:  # retornamos el response raw; otra capa lo parsea
        """
        Ejecuta una consulta con File Search habilitado como Tool.
        """
        if generation_config is None:
            generation_config = {
                "temperature": 0.2,
                "max_output_tokens": 1024,
            }

        try:
            tool = types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[store_name],
                )
            )

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[tool],
                **generation_config,
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=query,
                config=config,
            )
            return response
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error al ejecutar query_with_rag")
            raise GeminiServiceError(str(exc)) from exc
