import hashlib
from pathlib import Path
from typing import Iterable
import httpx

def download_new_files(pdf_urls: Iterable[str], category: str) -> list[Path]:
    data_dir = Path("data") / category
    data_dir.mkdir(parents=True, exist_ok=True)

    new_files: list[Path] = []

    for url in pdf_urls:
        # Nombre de archivo basado en hash + nombre original
        url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
        filename = url.split("/")[-1] or "file.pdf"
        target = data_dir / f"{url_hash}_{filename}"

        if target.exists():
            continue  # ya descargado

        with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as r:
            r.raise_for_status()
            with open(target, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)

        new_files.append(target)

    return new_files
