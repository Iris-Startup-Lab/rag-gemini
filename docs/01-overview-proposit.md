# 🧠 Sistema RAG con Google Gemini

## Descripción

Este proyecto implementa un sistema de Retrieval-Augmented Generation (RAG) utilizando la API de Google Gemini **File Search**, expuesto a través de un backend en **FastAPI**. El objetivo es permitir que un equipo de innovación cargue, procese e indexe documentos públicos (leyes, trámites, procedimientos, etc.) y realice consultas con respuestas trazables y citadas.

El sistema está diseñado como un **backend autónomo y escalable**, sin dependencias externas de orquestadores (como n8n). Se usa:

- **Python 3.10+**
- **FastAPI** como framework web.
- **SDK oficial de Google Gemini (`google-generativeai`)** para indexado y consultas.
- **Railway** como plataforma de despliegue del backend (la API sólo orquesta peticiones y lógica; el almacenamiento pesado se delega a Gemini).

Desde el MVP se contemplan:

- Filtros para **cuidar la versión gratuita de Gemini y los costos** (control de tamaños de archivo).
- Un **módulo de limpieza y descarte** de archivos antes de subirlos.
- Un **módulo de prompts/roles** para que la API siempre responda con un estilo y comportamiento controlado.
- Respuestas que **siempre incluyen las fuentes** (archivo y fragmento).

> ⚠️ Nota: este repositorio cubre **sólo el backend**. La interfaz web se implementará en un repositorio separado, pero la API ya está preparada para servir a un frontend.

---

## Propósito

El propósito principal es proporcionar una herramienta para que un **equipo de innovación** valide ideas contra el marco regulatorio (leyes, trámites, lineamientos, etc.) de forma rápida y confiable, apoyándose en documentos públicos.

Con este backend, el equipo puede:

- Cargar en bloque documentos en bruto (por ejemplo, los **~180 archivos** actuales de leyes y trámites).
- Aplicar un filtro previo y limpieza ligera para:
  - Descarta archivos demasiado pesados o problemáticos.
  - Mantenerse dentro de los límites de uso de la **versión gratuita de Gemini** o dentro de umbrales de costos definidos.
- Indexar los documentos aprobados en **stores de File Search** de Gemini.
- Lanzar consultas tipo chat, donde el modelo:
  - Recupera fragmentos de los documentos indexados.
  - Genera una respuesta **argumentada y trazable**.
  - **Siempre devuelve las fuentes** (archivo y fragmento).

En la práctica, esto permite:

- Validar rápidamente si una idea de innovación respeta leyes y trámites.
- Evitar la búsqueda manual en PDFs largos.
- Fomentar una innovación **segura y compliant**.

---

## Consideraciones sobre la versión gratuita de Gemini y costos

Una de las prioridades del diseño es **cuidar el uso de la API de Gemini**, especialmente en la versión gratuita y en escenarios con presupuesto acotado. Para ello, el backend incorpora:

1. **Filtro de tamaño antes de subir documentos**
   - Antes de enviar cualquier archivo a Gemini, pasa por un módulo de **preprocesamiento** que:
     - Verifica tamaño de archivo contra un umbral configurable (por ejemplo `MAX_FREE_TIER_FILE_SIZE_MB` en `config.py`).
     - Si el archivo excede el límite:
       - No se sube a Gemini.
       - Se registra en logs.
       - Se incluye en la respuesta de la API como **“descartado por tamaño”**.

2. **Módulo de limpieza (MVP)**
   - En esta primera versión, el módulo de limpieza:
     - Puede aplicar reglas básicas (validación de extensión, tamaños, tipo de contenido).
     - No modifica el contenido del archivo, pero **decide si se descarta o se permite el upload**.
     - Devuelve al cliente:
       - Lista de archivos aceptados.
       - Lista de archivos descartados y motivo (por ejemplo: tamaño, extensión no soportada, etc.).
   - A futuro, este módulo se puede extender para:
     - Limpiar metadatos.
     - Normalizar texto.
     - Eliminar páginas vacías o ruido.

De esta forma, el sistema **protege el uso de la API de Gemini** y reduce el riesgo de costos inesperados o uso ineficiente de la cuota gratuita.

---

## Requisitos

- **Python** 3.10 o superior.
- Cuenta en **Google AI Studio** para obtener la clave API de Gemini.
- Dependencias Python (se instalan con `requirements.txt`):
  - `fastapi`
  - `uvicorn`
  - `google-generativeai`
  - `pydantic`
  - `python-dotenv`
  - `loguru`
  - `pytest`

- Variables de entorno:
  - `GEMINI_API_KEY` → clave de la API de Gemini.
  - Opcionales (recomendado definirlas en `config.py` o `.env`):
    - `MAX_FREE_TIER_FILE_SIZE_MB`
    - `APP_ENV` (`dev`, `staging`, `prod`)

- Hosting:
  - **Railway** para desplegar el backend FastAPI (la API es stateless; el almacenamiento de documentos se delega a Gemini).

