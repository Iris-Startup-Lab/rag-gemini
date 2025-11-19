# Documentación del Proyecto

## Requisitos Previos

### Crear y activar entorno virtual (opcional pero recomendado):
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

### Instalar dependencias:
```bash
pip install -r requirements.txt
```

### Configurar variables de entorno:
Por ejemplo, con un archivo `.env` en la raíz del proyecto:
```env
GEMINI_API_KEY=tu-clave
MAX_FREE_TIER_FILE_SIZE_MB=20  # ejemplo, ajustar según límites vigentes
```

## Ejecución del Servidor

### Ejecutar el servidor en local:
```bash
uvicorn main:app --reload
```

### Probar la documentación interactiva de la API:
Abrir en el navegador:
[http://localhost:8000/docs](http://localhost:8000/docs)