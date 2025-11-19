import tempfile
from pathlib import Path
from typing import List

from fastapi import UploadFile

from src.models.schemas import UploadResponse, DiscardedFile
from src.preprocessing.cleaner import validate_file
from src.services.gemini_service import GeminiService
from src.utils.logger import logger


class FileService:
    def __init__(self, gemini_service: GeminiService) -> None:
        self.gemini_service = gemini_service

    def process_and_upload(
        self,
        store_name: str,
        files: List[UploadFile],
    ) -> UploadResponse:
        accepted_files: List[str] = []
        discarded_files: List[DiscardedFile] = []
        temp_paths: List[str] = []

        # 1) Validar cada archivo
        for file in files:
            accepted, reason, size_mb = validate_file(file)

            if not accepted:
                logger.info(
                    f"Archivo descartado: {file.filename} | {reason} | {size_mb} MB"
                )
                discarded_files.append(
                    DiscardedFile(
                        filename=file.filename or "unknown",
                        reason=reason or "UNKNOWN_REASON",
                        size_mb=size_mb,
                    )
                )
                continue

            # 2) Guardar archivo aceptado en tmp
            suffix = Path(file.filename or "").suffix
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as tmp:
                content = file.file.read()
                tmp.write(content)
                tmp_path = tmp.name

            temp_paths.append(tmp_path)
            accepted_files.append(file.filename or tmp_path)

        # 3) Subir a Gemini (solo si hay aceptados)
        if temp_paths:
            logger.info(
                f"Subiendo {len(temp_paths)} archivos a store {store_name}..."
            )
            self.gemini_service.upload_files_to_store(
                store_name=store_name,
                file_paths=temp_paths,
                wait_for_index=True,
            )

        # Nota: al ser un MVP no limpiamos los temporales aún.
        return UploadResponse(
            store_name=store_name,
            accepted_files=accepted_files,
            discarded_files=discarded_files,
        )
