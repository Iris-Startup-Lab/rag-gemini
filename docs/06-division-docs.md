## 📂 Carga e indexación de documentos en Gemini File Search

Esta sección explica **cómo se llenan de PDFs** los stores de Gemini que usa el backend, y cómo se conectan con el resto del pipeline RAG.

---

### 1. Concepto: stores por categoría (`leyes`, `tramites`, `general`)

El backend usa **Gemini File Search** como capa de almacenamiento/indexación.
Cada categoría de documentos se mapea a un **File Search Store** distinto:

* `GEMINI_STORE_LEYES` → PDFs normativos (leyes, reglamentos, disposiciones, etc.).
* `GEMINI_STORE_TRAMITES` → PDFs de trámites (fichas, guías, requisitos).
* `GEMINI_STORE_GENERAL` → combinación de **leyes + trámites** para búsquedas globales.

En el frontend:

* Si el usuario selecciona **“Solo leyes”**, se consulta `GEMINI_STORE_LEYES`.
* Si selecciona **“Solo trámites”**, se consulta `GEMINI_STORE_TRAMITES`.
* Si selecciona **“General”**, se consulta `GEMINI_STORE_GENERAL`.

> Nota: `GEMINI_STORE_GENERAL` contiene una copia de ambos conjuntos de documentos. Es redundante, pero simplifica mucho el MVP.

---

### 2. Cambios realizados e integración al pipeline

A nivel de arquitectura del backend se añadieron varios módulos:

1. **Servicio Gemini (`src/services/gemini_service.py`)**

   * Envuelve al SDK `google-genai`.
   * Funciones clave:

     * `create_store(display_name)` → crea un File Search Store.
     * `upload_files_to_store(store_name, file_paths, wait_for_index=True)` → sube archivos locales al store y espera a que se indexen.
     * `query_with_rag(store_name, query, system_instruction, generation_config)` → ejecuta la consulta RAG contra un store.

2. **Servicio de archivos (`src/services/file_service.py`)**

   * Orquesta la subida:

     * Valida archivos mediante `src.preprocessing.cleaner` (tamaño y extensión).
     * Los guarda temporalmente en disco.
     * Llama a `GeminiService.upload_files_to_store`.
   * Devuelve un `UploadResponse` con:

     * `accepted_files`: lista de archivos aceptados.
     * `discarded_files`: archivos descartados (por tamaño/extensión).

3. **Módulo de limpieza (`src/preprocessing/cleaner.py`)**

   * Aplica filtro previo para la versión gratuita de Gemini:

     * Tamaño máximo (MB) controlado por `MAX_FREE_TIER_FILE_SIZE_MB` en `.env`.
     * Extensiones soportadas: `.pdf`, `.txt`, `.md`, `.docx`.
   * Evita subir archivos demasiado grandes o con extensiones no soportadas.

4. **Gestor de prompts (`src/prompting/prompt_manager.py` + `src/services/prompt_service.py`)**

   * Carga archivos YAML desde la carpeta `prompts/`.
   * Perfil por defecto: `prompts/default.yaml`.
   * `PromptService` expone `get_system_instruction(profile)` para obtener el texto de sistema que se envía al modelo.

5. **Nuevos endpoints FastAPI (`src/api/routes.py`)**

   * `GET /health` → comprobar estado del backend.
   * `POST /create-store` → crear un File Search Store (Gemini).
   * `POST /upload-files/{store_name:path}` → subir y validar archivos a un store.
   * `POST /query/{store_name:path}` → consultar un store con el perfil de prompt elegido.

6. **Script de carga en lotes (`scripts/batch_upload.py`)**

   * Permite subir carpetas completas desde el disco local hacia un store de Gemini.
   * Soporta `--batch-size` para dividir grandes volúmenes (ej. 150 PDFs de leyes) en varios lotes y evitar timeouts.

En conjunto, el pipeline de indexación queda así:

> Carpeta local (`data/leyes`, `data/tramites`)
> ➜ `scripts/batch_upload.py`
> ➜ Endpoint `POST /upload-files/{store_name}`
> ➜ `FileService` + `cleaner`
> ➜ `GeminiService.upload_files_to_store`
> ➜ **Gemini File Search Store** (`leyes`, `tramites`, `general`)

Y el pipeline de consulta:

> Frontend / Swagger (`/query/{store_name}`)
> ➜ `PromptService` (carga `default.yaml`)
> ➜ `GeminiService.query_with_rag`
> ➜ Gemini File Search + modelo
> ➜ Respuesta `QueryResponse { answer, sources[] }`

---

### 3. Preparación del entorno y creación de stores

#### 3.1. Estructura de carpetas local

En el repositorio, organizar así:

```bash
data/
  leyes/
    # ~150 PDFs de leyes
  tramites/
    # ~20 PDFs de trámites
```

#### 3.2. Levantar el backend

```bash
uvicorn main:app --reload
```

Esto expone la API en:
`http://127.0.0.1:8000`

#### 3.3. Crear los 3 File Search Stores en Gemini

Desde `http://127.0.0.1:8000/docs`:

1. Abrir `POST /create-store`.
2. Ejecutar tres veces con estos cuerpos:

```json
{ "display_name": "leyes" }
```

```json
{ "display_name": "tramites" }
```

```json
{ "display_name": "general" }
```

3. Guardar los `store_name` devueltos, que tienen forma:

```text
fileSearchStores/leyes-xxxxxxxxxxxx
fileSearchStores/tramites-xxxxxxxxx
fileSearchStores/general-xxxxxxxxxx
```

4. Añadirlos al `.env`:

```env
GEMINI_STORE_LEYES=fileSearchStores/leyes-xxxxxxxxxxxx
GEMINI_STORE_TRAMITES=fileSearchStores/tramites-xxxxxxxxx
GEMINI_STORE_GENERAL=fileSearchStores/general-xxxxxxxxxx
```

---

### 4. Script de carga en lotes (`scripts/batch_upload.py`)

El script final soporta **batches** para evitar timeouts con muchos archivos:

```python
# scripts/batch_upload.py
import argparse
import mimetypes
from pathlib import Path
from typing import List

import requests

API_BASE = "http://127.0.0.1:8000"


def list_files(folder: Path) -> List[Path]:
    return [p for p in sorted(folder.iterdir()) if p.is_file()]


def chunked(items: List[Path], size: int):
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
                timeout=1800,  # 30 minutos por lote
            )
        finally:
            for _, file_tuple in files_payload:
                file_tuple[1].close()

        print(f"    Status: {resp.status_code}")
        try:
            print(f"    Respuesta: {resp.json()}")
        except Exception:
            print(f"    Texto: {resp.text}")


if __name__ == "__main__":
    main()
```

---

### 5. Los 4 comandos clave de carga

Con el backend corriendo (`uvicorn main:app --reload`) y las carpetas `data/leyes` y `data/tramites` listas, estos son los 4 comandos para llenar los stores:

```bash
# 1) LEYES → store de leyes (~150 archivos, en lotes de 30)
python scripts/batch_upload.py --store-name "fileSearchStores/leyes-XXXXXXXXXXXX" --folder "data/leyes" --batch-size 30
```

```bash
# 2) TRÁMITES → store de trámites (~20 archivos)
python scripts/batch_upload.py --store-name "fileSearchStores/tramites-XXXXXXXX" --folder "data/tramites"
```

```bash
# 3) LEYES → store general (para búsquedas globales)
python scripts/batch_upload.py --store-name "fileSearchStores/general-XXXXXXXXXX" --folder "data/leyes" --batch-size 30
```

```bash
# 4) TRÁMITES → store general
python scripts/batch_upload.py --store-name "fileSearchStores/general-XXXXXXXXXX" --folder "data/tramites"
```

> Sustituye los `XXXXXXXX` por los IDs reales que te devolvió `/create-store`.

---

### 6. Cómo hacer consultas al RAG

Una vez que los stores están llenos, se pueden hacer consultas de dos maneras: vía Swagger o vía `curl`/frontend.

#### 6.1. Consultas desde Swagger

1. Ir a `http://127.0.0.1:8000/docs`.

2. Buscar `POST /query/{store_name}`.

3. Clic en **“Try it out”**.

4. En el campo `store_name` (path), elegir uno:

   * Solo leyes:
     `fileSearchStores/leyes-XXXXXXXXXXXX`
   * Solo trámites:
     `fileSearchStores/tramites-XXXXXXXX`
   * General:
     `fileSearchStores/general-XXXXXXXXXX`

5. En el cuerpo (`Request body`), usar:

```json
{
  "query": "¿Cuál es el límite máximo de comisiones que pueden cobrar las AFORE?",
  "prompt_profile": "default"
}
```

6. Clic en **Execute**.
   La respuesta tendrá forma:

```json
{
  "answer": "Texto generado por el modelo...",
  "sources": [
    {
      "filename": "Aviso por el cual la CONSAR da a conocer el máximo al que estarán sujetas las comisiones....pdf",
      "page": 2,
      "snippet": "Fragmento relevante..."
    }
  ]
}
```

#### 6.2. Consultas vía `curl` (útil para frontend / pruebas CLI)

```bash
# Solo LEYES
curl -X POST "http://127.0.0.1:8000/query/fileSearchStores/leyes-XXXXXXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{
        "query": "¿Cuál es el límite máximo de comisiones que pueden cobrar las AFORE?",
        "prompt_profile": "default"
      }'
```

```bash
# Solo TRÁMITES
curl -X POST "http://127.0.0.1:8000/query/fileSearchStores/tramites-XXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{
        "query": "¿Qué trámites básicos existen en el SAR?",
        "prompt_profile": "default"
      }'
```

```bash
# GENERAL (leyes + trámites)
curl -X POST "http://127.0.0.1:8000/query/fileSearchStores/general-XXXXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{
        "query": "Explica cómo funciona el SAR y qué trámites básicos existen",
        "prompt_profile": "default"
      }'
```

En el frontend, bastará con mapear:

* `topic = "leyes"`    → `GEMINI_STORE_LEYES`
* `topic = "tramites"` → `GEMINI_STORE_TRAMITES`
* `topic = "general"`  → `GEMINI_STORE_GENERAL`

y construir la URL:

```text
POST /query/{store_name}
```

con el JSON:

```json
{
  "query": "<pregunta del usuario>",
  "prompt_profile": "default"
}
```
