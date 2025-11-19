Estructura de Carpetas

La estructura sigue principios de separación de responsabilidades, inspirada en Clean Architecture y MVC, con módulos específicos para:

- API (controladores)
- Servicios de negocio (Gemini, archivos, prompts)
- Preprocesamiento y limpieza
- Modelos de datos (Pydantic)
- Utilidades (logging, excepciones)
- Tests

rag-gemini/
├── src/                        # Código fuente principal
│   ├── api/                    # Endpoints de la API (controladores)
│   │   ├── __init__.py
│   │   └── routes.py           # Definición de rutas FastAPI
│   │
│   ├── services/               # Lógica de negocio (servicios)
│   │   ├── __init__.py
│   │   ├── gemini_service.py   # Interacción con Gemini API (stores, indexado, consultas)
│   │   ├── file_service.py     # Manejo de archivos (subida, validación básica)
│   │   └── prompt_service.py   # Orquestación de prompts/roles para consultas RAG
│   │
│   ├── preprocessing/          # Filtros de tamaño y limpieza ligera
│   │   ├── __init__.py
│   │   └── cleaner.py          # Validación de tamaño, tipo de archivo, descarte
│   │
│   ├── prompting/              # Gestión de prompts de alto nivel
│   │   ├── __init__.py
│   │   └── prompt_manager.py   # Carga de prompts desde archivos YAML/JSON
│   │
│   ├── models/                 # Modelos de datos (Pydantic)
│   │   ├── __init__.py
│   │   └── schemas.py          # Esquemas para requests/responses
│   │
│   ├── utils/                  # Utilidades reutilizables
│   │   ├── __init__.py
│   │   ├── logger.py           # Configuración de logging (loguru)
│   │   └── exceptions.py       # Excepciones personalizadas
│   │
│   └── config.py               # Configuraciones globales (API key, límites, entorno)
│
├── prompts/                    # Definición de prompts/roles (datos)
│   ├── default.yaml            # Prompt general para consultas RAG
│   ├── compliance.yaml         # Prompt orientado a validación de cumplimiento
│   └── explain.yaml            # Prompt para explicaciones pedagógicas
│
├── tests/                      # Pruebas unitarias e integradas
│   ├── test_gemini_service.py
│   ├── test_file_service.py
│   └── test_api_routes.py
│
├── docs/                       # Documentación adicional
│   ├── 01-overview-proposito.md        # 
│   ├── 02-setup-entorno-local.md       # 
│   ├── 03-api-endpoints.md             # 
│   ├── 04-arquitectura-estructura.md   # 
│   └── 05-pipeline-gemini-rag.md       # 
├── .env                        # Variables de entorno (no commitear)
├── requirements.txt            # Dependencias
├── main.py                     # Punto de entrada (app FastAPI)
└── README.md                   # 



Resumen de responsabilidades

src/api/
Exposición de endpoints FastAPI. Se apoya en inyección de dependencias para instanciar servicios (gemini_service, file_service, prompt_service).

src/services/gemini_service.py
Encapsula la comunicación con la API de Gemini:

Crear stores de File Search.

Subir documentos aprobados a los stores.

Ejecutar consultas RAG sobre un store.

src/preprocessing/cleaner.py
Aplica reglas previas a la subida:

Valida tamaño vs MAX_FREE_TIER_FILE_SIZE_MB.

Verifica extensiones soportadas.

Marca y registra archivos descartados.

src/prompting/prompt_manager.py & src/services/prompt_service.py
Carga y gestiona prompts/roles desde la carpeta prompts/:

Selecciona el prompt adecuado según el tipo de consulta.

Construye el mensaje para Gemini de forma consistente.

Asegura que la respuesta incluya fuentes obligatorias.

src/models/schemas.py
Define los esquemas de entrada/salida. Especialmente importantes:

UploadResponse → incluye listas de archivos aceptados y descartados.

QueryRequest → consulta y tipo de prompt/rol.

QueryResponse → respuesta con fuentes obligatorias.