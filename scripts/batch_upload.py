# scripts/batch_upload.py
import argparse
import mimetypes
from pathlib import Path
from typing import List

import requests

API_BASE = "http://127.0.0.1:8000"


def list_files(folder: Path) -> List[Path]:
    """
    Regresa la lista de archivos dentro de la carpeta.
    """
    return [p for p in sorted(folder.iterdir()) if p.is_file()]


def chunked(items: List[Path], size: int):
    """
    Genera sublistas (batches) de tamaño 'size'.
    """
    for i in range(0, len(items), size):
        yield items[i : i + size]


def main():
    parser = argparse.ArgumentParser(
        description="Sube en batch archivos de una carpeta a un File Search store."
    )
    parser.add_argument(
        "--store-name",
        required=True,
        help="store_name devuelto por /create-store.",
    )
    parser.add_argument(
        "--folder",
        required=True,
        help="Ruta a la carpeta local con los archivos (ej. data/leyes).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=30,
        help="Número de archivos por lote (default: 30).",
    )

    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        raise SystemExit(f"La carpeta '{folder}' no existe o no es un directorio.")

    all_files = list_files(folder)
    if not all_files:
        raise SystemExit(f"No se encontraron archivos en la carpeta '{folder}'.")

    print(
        f"[+] Encontrados {len(all_files)} archivos en '{folder}'. "
        f"Subiendo en lotes de {args.batch_size}..."
    )

    batch_num = 0
    for batch in chunked(all_files, args.batch_size):
        batch_num += 1

        files_payload = []
        for entry in batch:
            mime, _ = mimetypes.guess_type(entry.name)
            if mime is None:
                mime = "application/pdf"

            fileobj = open(entry, "rb")
            files_payload.append(
                (
                    "files",
                    (entry.name, fileobj, mime),
                )
            )

        print(
            f"[+] Lote {batch_num}: subiendo {len(batch)} archivos al store "
            f"{args.store_name}..."
        )

        try:
            resp = requests.post(
                f"{API_BASE}/upload-files/{args.store_name}",
                files=files_payload,
                timeout=1800,  # 30 minutos por lote (muy amplio para estar tranquilos)
            )
        finally:
            # Cerrar SIEMPRE los archivos
            for _, file_tuple in files_payload:
                file_tuple[1].close()

        print(f"    Status: {resp.status_code}")
        try:
            print(f"    Respuesta: {resp.json()}")
        except Exception:
            print(f"    Texto: {resp.text}")


if __name__ == "__main__":
    main()
