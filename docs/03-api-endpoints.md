# Documentación del Proyecto

## Introducción
Breve descripción del proyecto, su propósito y alcance.

## Requisitos Previos
- **Entorno Virtual**: Crear y activar un entorno virtual.
  ```bash
  python -m venv .venv
  source .venv/bin/activate  # Linux/Mac
  .venv\Scripts\activate     # Windows
  ```
- **Dependencias**: Instalar dependencias.
  ```bash
  pip install -r requirements.txt
  ```
- **Variables de Entorno**: Configurar las variables necesarias.
  ```env
  GEMINI_API_KEY=tu-clave
  MAX_FREE_TIER_FILE_SIZE_MB=20
  ```

## Endpoints de la API

### **GET /health**
Verifica que el servicio esté levantado. Útil para monitoreo básico.

---

### **POST /create-store**
Crea un nuevo store de File Search en Gemini.

#### **Body mínimo**:
```json
{ "display_name": "docs_innovacion" }
```

---

### **POST /upload-files/{store_name}**
Recibe múltiples archivos, ejecuta filtros y sube los aceptados.

#### **Devuelve**:
- **Store usado**.
- **Archivos aceptados**.
- **Archivos descartados y motivos**.

---

### **POST /query/{store_name}**
Realiza consultas sobre un store.

#### **Recibe**:
```json
{
  "query": "texto de la consulta",
  "prompt_profile": "default"
}
```

#### **Devuelve**:
- **answer**: Respuesta generada.
- **sources**: Fuentes utilizadas.

## Despliegue

### **Despliegue en Railway**
1. Crear un proyecto en Railway.
2. Configurar variables de entorno:
   - `GEMINI_API_KEY`
   - `MAX_FREE_TIER_FILE_SIZE_MB` (opcional).
3. Definir el comando de arranque:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### **Visión General**
- Railway ejecutará el contenedor y expondrá la API.
- El backend será un orquestador de peticiones:
  - No almacena archivos de forma permanente.
  - Usa Gemini para almacenamiento e indexado.

## Seguridad y Mejoras Futuras

### **MVP**
- Sin autenticación/autorización compleja.
- Uso interno o controlado.

### **Futuras Mejoras**:
- Autenticación por JWT.
- Monitoreo con Prometheus/Grafana.
- Módulo de limpieza avanzado.
- Soporte para otros proveedores RAG.

## Contribuciones
- **Módulo de limpieza**: Extender para normalización, anonimización, etc.
- **Gestión de stores**: Listar, renombrar, eliminar y auditar.
- **Prompts**: Añadir más perfiles y afinarlos según feedback.

## Licencia
Incluir detalles sobre la licencia del proyecto.

## Contacto
Información de contacto para soporte o contribuciones.