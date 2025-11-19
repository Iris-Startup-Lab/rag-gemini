# scripts/batch_upload.py
import argparse
import mimetypes
from pathlib import Path

import requests

API_BASE = "http://127.0.0.1:8000"


def collect_files(folder: Path):
    """
    Recorre la carpeta y prepara la lista de (campo, (filename, fileobj, mimetype))
    para el multipart/form-data que espera FastAPI.
    """
    files_payload = []

    for entry in sorted(folder.iterdir()):
        if not entry.is_file():
            continue

        mime, _ = mimetypes.guess_type(entry.name)
        if mime is None:
            mime = "application/pdf"

        fileobj = open(entry, "rb")
        files_payload.append(
            (
                "files",  # nombre del parámetro en el endpoint /upload-files
                (entry.name, fileobj, mime),
            )
        )

    return files_payload


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

    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        raise SystemExit(f"La carpeta '{folder}' no existe o no es un directorio.")

    files_payload = collect_files(folder)
    if not files_payload:
        raise SystemExit(f"No se encontraron archivos en la carpeta '{folder}'.")

    print(f"[+] Subiendo {len(files_payload)} archivos de '{folder}' al store:")
    print(f"    {args.store_name}")

    resp = requests.post(
        f"{API_BASE}/upload-files/{args.store_name}",
        files=files_payload,
        timeout=600,
    )

    # Cerrar archivos locales
    for _, file_tuple in files_payload:
        file_tuple[1].close()

    print(f"[+] Status: {resp.status_code}")
    try:
        print(resp.json())
    except Exception:
        print(resp.text)


if __name__ == "__main__":
    main()
