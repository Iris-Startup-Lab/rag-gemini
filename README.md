# 🧠 RAG-Gemini — Sistema RAG con Google Gemini File Search

Backend modular en FastAPI para cargas, indexado y consultas con trazabilidad.

Este proyecto implementa un Sistema RAG (Retrieval-Augmented Generation) utilizando la API oficial de Google Gemini File Search, permitiendo a un equipo cargar documentos (leyes, trámites, lineamientos…), indexarlos y realizar consultas cuyos resultados siempre incluyen fuentes verificables.

El backend está diseñado para ser robusto, modular y escalable, pero también optimizado para MVP y control de costos, incorporando filtros inteligentes antes de interactuar con Gemini.

---

## 📌 Objetivos del Proyecto

- Permitir el upload masivo de documentos (ej. los ~180 PDFs actuales).
- Validar archivos antes de enviarlos a Gemini para:
  - Evitar costos inesperados.
  - Respetar límites de la versión gratuita.
  - Mantener la calidad del corpus.
- Indexar documentos en File Search Stores de Gemini.
- Consultar mediante un RAG que:
  - Recupera fragmentos relevantes.
  - Genera explicaciones basadas en evidencia.
  - Forzosamente entrega las fuentes (archivo/página/snippet).
- Incluir un módulo de prompts/roles para controlar el estilo de respuesta.
- Exponer toda la lógica a través de una API REST en FastAPI, lista para ser consumida por un futuro frontend.

> ⚠️ **Nota**: Este repositorio incluye únicamente el backend, pero está preparado para integrarse con una interfaz web en un segundo repositorio.

---

## 🧩 Endpoints Principales

(Basado en [03-api-endpoints.md](docs/03-api-endpoints.md))

- **✔️ GET /health**  
  Checa que la API esté viva.

- **✔️ POST /create-store**  
  Crea un store de documentos en Gemini.

- **✔️ POST /upload-files/{store_name}**  
  Valida, limpia y sube archivos.

- **✔️ POST /query/{store_name}**  
  Consulta un corpus usando RAG + roles personalizados.

---

## 🧠 Módulos Clave

### 🔹 Módulo de limpieza (`src/preprocessing/cleaner.py`)
- Filtra por tamaño.
- Revisa extensiones.
- Controla costos del File Search.
- Incluye lista de archivos descartados.

### 🔹 Servicios de Gemini (`src/services/gemini_service.py`)
- Crear stores.
- Subir documentos.
- Ejecutar consultas RAG.

### 🔹 Gestión de prompts (`src/prompting/prompt_manager.py`)
- Carga prompts YAML.
- Control de comportamiento del modelo.
- Obliga a incluir trazabilidad en las respuestas.