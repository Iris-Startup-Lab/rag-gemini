Buenísima pregunta, aquí está justo el “cómo se llena de PDFs” este backend 💾📚

Te respondo en tres partes:

1. **Concepto general (leyes / trámites / general)**
2. **Flujo concreto paso a paso**
3. **Script para cargar carpetas locales (leyes y trámites)**

---

## 1️⃣ Concepto: cómo mapeamos leyes / trámites / general

Con el código que ya tenemos, **cada “categoría” es un File Search Store de Gemini**:

* Un store para **leyes**
* Un store para **trámites**
* (Opcional pero súper útil) un store **general** que tenga *ambas cosas* para búsquedas globales.

Entonces:

* Si en el frontend seleccionan **“Solo leyes”** → llamas al backend con el `store_name` de leyes.
* Si seleccionan **“Solo trámites”** → usas el `store_name` de trámites.
* Si seleccionan **“General”** → usas el `store_name` del store general (donde subimos leyes + trámites).

👀 Sí, esto implica duplicar los documentos en el `store_general`, pero con ~170 archivos es totalmente manejable para un MVP y mantiene el backend simple.

---

## 2️⃣ Paso a paso: antes / después de `uvicorn main:app --reload`

En realidad, **necesitas tener el servidor levantado** para poder usar los endpoints de carga, así que el orden sano es:

### Paso 0 — Estructura de carpetas local

En tu repo, crea algo así:

```bash
data/
  leyes/
    (aquí pones tus ~150 PDFs de leyes)
  tramites/
    (aquí pones tus ~20 PDFs de trámites)
```

No hace falta que el backend “vea” estas carpetas directamente: las vamos a usar desde un script que llama al endpoint de carga.

---

### Paso 1 — Levantar el backend

```bash
uvicorn main:app --reload
```

Backend escuchando en `http://localhost:8000`.

---

### Paso 2 — Crear los 3 stores en Gemini vía API

Ve a `http://localhost:8000/docs` (Swagger) y:

1. Abre `POST /create-store`.

2. En “Request body”, pon algo como:

   * Para **leyes**:

     ```json
     {
       "display_name": "leyes"
     }
     ```
   * Para **trámites**:

     ```json
     {
       "display_name": "tramites"
     }
     ```
   * Para **general**:

     ```json
     {
       "display_name": "general"
     }
     ```

3. Ejecuta cada uno y **guarda los `store_name`** que te regrese la API (son IDs largos tipo `projects/xxx/locations/xxx/fileStores/yyy`).

Te sugiero apuntarlos en tu `.env` para tenerlos a la mano:

```env
GEMINI_STORE_LEYES=projects/.../stores/...
GEMINI_STORE_TRAMITES=projects/.../stores/...
GEMINI_STORE_GENERAL=projects/.../stores/...
```

---

### Paso 3 — Cargar tus PDFs desde carpetas locales

Aquí es donde entra la parte de “¿se puede tener una ruta específica para que los tome?”.

Vamos a añadir un **script pequeño** que:

* Lee una carpeta local (`data/leyes` o `data/tramites`).
* Envía TODOS los archivos al endpoint `POST /upload-files/{store_name}`.

De esta forma tú solo dejas los PDFs en la carpeta y ejecutas un comando.

---

## 3️⃣ Script: `scripts/batch_upload.py`

Crea la carpeta `scripts/` y dentro el archivo `batch_upload.py`:

```python
# scripts/batch_upload.py
import argparse
import os
from pathlib import Path
import mimetypes

import requests


API_BASE = "http://localhost:8000"


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
            # Por defecto asumimos PDF si no se puede adivinar
            mime = "application/pdf"

        fileobj = open(entry, "rb")
        files_payload.append(
            (
                "files",  # debe coincidir con el parámetro 'files' del endpoint
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
        help="Nombre completo del File Search store (store_name devuelto por /create-store).",
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
    print(f"    {args.store-name}")

    resp = requests.post(
        f"{API_BASE}/upload-files/{args.store-name}",
        files=files_payload,
        timeout=600,  # hasta 10 minutos, por si son archivos pesados
    )

    # IMPORTANTE: cerrar archivos locales
    for _, file_tuple in files_payload:
        file_tuple[1].close()

    print(f"[+] Status: {resp.status_code}")
    try:
        print(resp.json())
    except Exception:
        print(resp.text)


if __name__ == "__main__":
    main()
```

> Ojo: en el script, donde puse `args.store-name` debe ser `args.store_name` (en Python no se aceptan guiones en nombres de variables). Corrijo en el ejemplo de uso abajo.

---

### Cómo usarlo para tus 3 categorías

Con el backend corriendo:

```bash
# 1) LEYES (~150 archivos)
python scripts/batch_upload.py \
  --store-name "EL_STORE_NAME_DE_LEYES" \
  --folder "data/leyes"

# 2) TRÁMITES (~20 archivos)
python scripts/batch_upload.py \
  --store-name "EL_STORE_NAME_DE_TRAMITES" \
  --folder "data/tramites"

# 3) GENERAL (leyes + trámites)
python scripts/batch_upload.py \
  --store-name "EL_STORE_NAME_DE_GENERAL" \
  --folder "data/leyes"

python scripts/batch_upload.py \
  --store-name "EL_STORE_NAME_DE_GENERAL" \
  --folder "data/tramites"
```

Y listo:

* Tienes **un store solo de leyes**,
* **otro solo de trámites**,
* y **uno general con todo mezclado**.

---

## 4️⃣ Cómo se consulta luego (leyes / trámites / general)

Una vez cargado todo, puedes probar en Swagger o con `curl`:

```bash
# Solo LEYES
curl -X POST "http://localhost:8000/query/EL_STORE_NAME_DE_LEYES" \
  -H "Content-Type: application/json" \
  -d '{
        "query": "¿Cuál es el límite máximo de comisiones que pueden cobrar las AFORE?",
        "prompt_profile": "default"
      }'

# Solo TRÁMITES
curl -X POST "http://localhost:8000/query/EL_STORE_NAME_DE_TRAMITES" \
  -H "Content-Type: application/json" \
  -d '{
        "query": "¿Qué documentos necesito para un retiro parcial por desempleo?",
        "prompt_profile": "default"
      }'

# GENERAL
curl -X POST "http://localhost:8000/query/EL_STORE_NAME_DE_GENERAL" \
  -H "Content-Type: application/json" \
  -d '{
        "query": "Explica cómo funciona el SAR y qué trámites básicos existen",
        "prompt_profile": "default"
      }'
```

En el frontend, lo único que tienes que hacer es:

* Guardar/mapear los 3 `store_name`s.
* Ofrecer un selector:

  * `topic = "leyes"` → usa `STORE_LEYES`
  * `topic = "tramites"` → usa `STORE_TRAMITES`
  * `topic = "general"` → usa `STORE_GENERAL`

y mandar ese `store_name` al endpoint `/query/{store_name}`.

---

Si quieres, en el siguiente mensaje puedo:

* Ajustar cualquier detalle del script (por ejemplo dividir en lotes de 30 archivos).
* O bien hacer una versión donde en lugar de usar los `store_name` directamente, uses `topic=leyes|tramites|general` y el backend se encargue de traducirlo a IDs leyendo el `.env`.
