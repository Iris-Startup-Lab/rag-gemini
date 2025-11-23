# Documentación del Proyecto

## Importaciones Clave y Dependencias

### **Archivo requirements.txt:**
```plaintext
fastapi==0.115.0
uvicorn[standard]==0.30.6

google-genai

pydantic==2.9.2
pydantic-settings==2.6.0

python-dotenv==1.0.1
loguru==0.7.2
requests==2.32.3
pytest==8.3.3

python-multipart
```

### **Importaciones Clave:**

#### gemini_service.py:
```python
import google.genai as genai
from loguru import logger
```

#### file_service.py:
```python
import os
from fastapi import UploadFile
from src.preprocessing.cleaner import validate_file
```

#### prompt_manager.py:
```python
import yaml
from pathlib import Path
```

#### schemas.py (ejemplo simplificado):
```python
from pydantic import BaseModel
from typing import List, Optional

class Source(BaseModel):
    filename: str
    page: Optional[int] = None
    snippet: str

class QueryRequest(BaseModel):
    query: str
    prompt_profile: str = "default"
```

#### routes.py:
```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from src.models.schemas import QueryRequest, QueryResponse
```

## Pipeline de Trabajo (MVP)

### **1. Creación de Store en Gemini**

#### Endpoint:
`POST /create-store`

#### **Body de ejemplo:**
```json
{ "display_name": "docs_innovacion" }
```

#### **Lógica:**
- `gemini_service.create_store(display_name)` crea un File Search store.
- Devuelve:
```json
{ "store_name": "projects/.../locations/.../collections/.../dataStores/..." }
```

---

### **2. Subida y Preprocesamiento de Archivos**

#### Endpoint:
`POST /upload-files/{store_name}`

#### **Flujo:**
1. Se reciben los archivos (`List[UploadFile]`).
2. Cada archivo pasa por `cleaner.validate_file(file)`:
   - Si supera `MAX_FREE_TIER_FILE_SIZE_MB` → se descarta.
   - Si la extensión no es soportada → se descarta.
3. Los archivos aceptados se suben a Gemini mediante `gemini_service.upload_files(...)`.
4. Se espera a que las operaciones de indexado concluyan (o se registra su operación).

#### **Respuesta (ejemplo conceptual):**
```json
{
  "store_name": "projects/.../stores/...",
  "accepted_files": [
    "leyes_01.pdf",
    "tramites_abc.pdf"
  ],
  "discarded_files": [
    {
      "filename": "leyes_muy_pesadas.pdf",
      "reason": "FILE_TOO_LARGE",
      "size_mb": 120.5
    }
  ]
}
```

---

### **3. Consulta (RAG + Prompts + Fuentes Obligatorias)**

#### Endpoint:
`POST /query/{store_name}`

#### **Body:**
```json
{
  "query": "¿Qué requisitos aplican para este tipo de trámite?",
  "prompt_profile": "compliance"
}
```

#### **Flujo:**
1. `prompt_manager` carga el prompt correspondiente (por ejemplo, `prompts/compliance.yaml`).
2. `prompt_service` construye el mensaje para Gemini:
   - Instrucciones de rol (ej. "Eres un asistente experto en el sistema de ahorro para el retiro…").
   - Instrucciones para que la respuesta incluya siempre:
     - Perspectiva factual.
     - Citas explícitas a los documentos recuperados.
     - Estructura JSON o claramente estructurada.
3. `gemini_service.query_with_rag(...)` ejecuta la consulta RAG contra el `store_name`:
   - Recupera fragmentos relevantes.
   - Genera la respuesta con el modelo.
4. Se parsea la respuesta para ajustar al esquema `QueryResponse`.

#### **Respuesta (ejemplo conceptual):**
```json
{
  "answer": "Para este tipo de trámite se requiere X, Y y Z...",
  "sources": [
    {
      "filename": "ley_tramites_2024.pdf",
      "page": 5,
      "snippet": "Artículo 10.- Para la realización de este trámite se requiere..."
    },
    {
      "filename": "reglamento_operativo.pdf",
      "page": 12,
      "snippet": "En el capítulo II se establecen los requisitos mínimos..."
    }
  ]
}
```

🔎 **Importante:** El contrato de `QueryResponse` hace que tanto el backend como cualquier frontend tengan que mostrar las fuentes; no es opcional.