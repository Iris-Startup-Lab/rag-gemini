# 07 – Módulo de Scraping automático (Playwright + Gemini File Search)

## 1. Objetivo del módulo

Este módulo permite:

1. **Scrapear periódicamente** páginas web oficiales (CONSAR, SEP, INE, etc.) usando **Playwright**.  
2. **Detectar nuevos PDFs** publicados en esas páginas.  
3. **Descargar sólo los archivos nuevos** a la carpeta `data/<category>/` del proyecto.  
4. **Decidir automáticamente cuándo indexar** esos nuevos archivos en la **API de Gemini File Search**, agrupando por *store* (leyes, trámites, glosario, etc.).  

Todo esto:

- Sin tocar los endpoints del backend que ya sirven al frontend.
- Respetando la división de documentos por categorías (`leyes`, `tramites`, `info`, `glosario`, …).
- Controlando frecuencia y volumen de indexado para cuidar costos.

---

## 2. Arquitectura y estructura de carpetas

Nueva estructura relevante dentro de `src/`:

```bash
src/
  configs/
    scraper_sources.yaml        # (Opcional) Config futura de fuentes
  scraping/
    __init__.py                 # Rutas base: DATA_ROOT, CONFIGS_DIR, etc.
    file_downloader.py          # Descarga de PDFs a data/<category>/
    models.py                   # Modelos/config (si se usa YAML u otros)
    playwright_scraper.py       # BaseScraper + helper Playwright
    runner.py                   # Orquestador scraping + indexado
    strategies/                 # Un scraper por fuente/página
      __init__.py
      consar_leyes.py
      consar_tramites.py
      ine_docs.py
      sep_glosario.py
    jobs/
      __init__.py
      scrape_and_index.py       # Punto de entrada para cron / Docker
````

Y en la raíz del proyecto:

```bash
data/
  leyes/
  tramites/
  info/
  glosario/
  meta/
    scraper_meta.json           # Tracking de último indexado por store
```

* `data/<category>/` → aquí se guardan los PDFs descargados (por ejemplo `data/leyes/`).
* `data/meta/scraper_meta.json` → JSON interno para saber **cuándo se indexó por última vez** cada *store* de Gemini.

---

## 3. Flujo end-to-end (de la web a Gemini)

### 3.1. Resumen del flujo

1. **Cron / comando manual** llama a:

   ```bash
   python -m src.scraping.jobs.scrape_and_index
   ```

2. `scrape_and_index.py` construye la lista de scrapers registrados:

   ```python
   SCRAPERS = [
       ConsarLeyesScraper(),
       ConsarTramitesScraper(),
       SepGlosarioScraper(),
       # ...
   ]
   ```

3. Llama al orquestador:

   ```python
   run_scraper_and_maybe_index(SCRAPERS)
   ```

4. `runner.py`:

   * Ejecuta cada scraper (clase hija de `BaseScraper`).
   * Cada scraper:

     * Usa Playwright para abrir la página.
     * Encuentra links de PDFs según sus selectores / lógica.
     * Devuelve una lista de URLs.
     * Descarga PDFs **nuevos** a `data/<category>/`.
   * Agrupa archivos nuevos por `store_name` de Gemini.
   * Aplica el filtro de limpieza (`filter_valid_files`).
   * Decide si ya vale la pena indexar.
   * Si sí → llama a `GeminiService.upload_files_to_store(...)`.
   * Actualiza `scraper_meta.json` con el timestamp del último indexado por store.

---

## 4. Detalle de cada archivo

### 4.1. `src/scraping/__init__.py`

Centraliza rutas importantes del proyecto:

```python
from pathlib import Path

SCRAPING_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRAPING_DIR.parent
PROJECT_ROOT = SRC_DIR.parent
DATA_ROOT = PROJECT_ROOT / "data"
CONFIGS_DIR = SRC_DIR / "configs"
```

* `DATA_ROOT` → base para todas las operaciones de archivos (`data/`).
* `CONFIGS_DIR` → base para leer archivos como `scraper_sources.yaml` en `src/configs/`.

Esto evita problemas de rutas relativas y permite usar:

```python
from src.scraping import DATA_ROOT, CONFIGS_DIR
```

en cualquier módulo.

---

### 4.2. `src/scraping/file_downloader.py`

Responsable de **descargar PDFs nuevos**:

* Entrada:

  * Lista de URLs (`pdf_urls`)
  * Nombre de categoría (`category`: `"leyes"`, `"tramites"`, etc.)
* Salida:

  * Lista de `Path` con **archivos nuevos** guardados en `data/<category>/`.

Puntos clave de la lógica:

* Crea `data/<category>/` si no existe.
* Obtiene un **hash SHA1 de la URL** para evitar duplicados y colisiones:

  * Nombre final de archivo: `<hash10>_<nombre_original.pdf>`
* Si el archivo ya existe, se salta la descarga.
* Si hay error en la descarga, se borra el parcial y se continúa.

Ejemplo conceptual de uso:

```python
new_files = download_new_files(pdf_urls, category="leyes")
# → devuelve solo los PDFs que no existían antes
```

---

### 4.3. `src/scraping/playwright_scraper.py`

Este archivo define:

1. `collect_links_from_page(url, link_selector)`
2. `BaseScraper` (clase abstracta para todos los scrapers específicos)

#### 4.3.1. `collect_links_from_page`

Función helper que encapsula el uso básico de Playwright:

* Abre Chromium en modo headless.
* Visita `url`.
* Espera `networkidle` (la red se queda quieta).
* Ejecuta JS sobre `link_selector` para extraer todos los `href`.

Ejemplo:

```python
links = await collect_links_from_page(
    url="https://www.gob.mx/consar/documentos/leyes",
    link_selector="a[href$='.pdf']"
)
```

Esto te devuelve una lista de URLs (strings) a PDFs encontrados.

#### 4.3.2. `BaseScraper`

Molde común para todos los scrapers:

```python
class BaseScraper(ABC):
    id: str           # identificador lógico del scraper
    name: str         # nombre descriptivo ("CONSAR - Leyes")
    category: str     # carpeta en data/ (leyes, tramites, info...)
    store_env: str    # nombre de la env var con el store_name de Gemini
    base_url: str     # URL principal desde donde arranca el scraping
```

Propiedades y métodos clave:

* `store_name`:

  * Lee `os.getenv(self.store_env)`.
  * Si la variable no está definida, lanza error.
  * Mapea cada scraper a un **store** de Gemini:

    * Ej: `GEMINI_STORE_LEYES` → `fileSearchStores/leyes-XXXX`

* `data_dir`:

  * Ruta `data/<category>/` asociada a ese scraper.

* `async def fetch_pdf_urls(self) -> List[str]`:

  * **Método abstracto** a implementar por cada scraper.
  * Aquí va la lógica concreta de:

    * abrir páginas (puede ser solo `base_url` o varias),
    * seguir paginación,
    * filtrar links, etc.

* `async def run(self) -> List[Path]`:

  * Flujo estándar:

    1. Llama a `fetch_pdf_urls()`.
    2. Llama a `download_new_files(urls, category=self.category)`.
    3. Devuelve lista de rutas a archivos nuevos.

---

### 4.4. `src/scraping/runner.py`

Es el **orquestador** de scraping + indexado.

#### Responsabilidades:

1. Ejecutar una lista de scrapers `BaseScraper`.
2. Agrupar los nuevos archivos por `store_name`.
3. Pasar archivos por el filtro de limpieza (`filter_valid_files`).
4. Decidir si indexar inmediato o esperar.
5. Llamar al servicio de Gemini para indexar.
6. Registrar en `scraper_meta.json` el momento del último indexado.

#### Configuración por variables de entorno

* `SCRAPER_MIN_FILES_TO_INDEX` (default: `5`)

  * Mínimo de archivos nuevos para lanzar indexado.
* `SCRAPER_MAX_WAIT_DAYS` (default: `7`)

  * Máximo de días a esperar antes de indexar, aunque haya pocos archivos.

#### Decisión de indexado: `should_index_now`

La lógica es:

```python
enough_files = len(new_files) >= MIN_FILES_TO_INDEX
waited_enough = last_dt is None or (now - last_dt).days >= MAX_WAIT_DAYS
return enough_files or waited_enough
```

Traducción:

* **Indexar si:**

  * Hay suficientes archivos nuevos **o**
  * Ya pasó demasiado tiempo desde el último indexado.

Esto permite balancear costo / frescura:

* No indexas por 1 archivo cada hora.
* Pero tampoco pueden pasar semanas acumulando sin indexar.

#### `scraper_meta.json`

* Estructura esperada:

  ```json
  {
    "fileSearchStores/leyes-XXXX": "2025-01-01T12:34:56.789000",
    "fileSearchStores/tramites-YYYY": "2025-01-03T09:10:11.000000"
  }
  ```
* Se actualiza en `update_meta_after_index(store_name)`.

---

### 4.5. `src/scraping/jobs/scrape_and_index.py`

Es el **punto de entrada** del módulo:

* Define la lista de scrapers activos:

```python
SCRAPERS = [
    ConsarLeyesScraper(),
    ConsarTramitesScraper(),
    SepGlosarioScraper(),
    # IneDocsScraper(),
]
```

* Ejecuta:

```python
def main() -> None:
    if not SCRAPERS:
        logger.warning("No hay scrapers registrados en SCRAPERS.")
        return

    run_scraper_and_maybe_index(SCRAPERS)
```

* Se ejecuta desde consola / cron como:

```bash
python -m src.scraping.jobs.scrape_and_index
```

---

## 5. Rutas de los links y cómo se obtienen los PDFs

Cada scraper en `src/scraping/strategies/` controla:

* **`base_url`**: Página desde donde empieza a buscar.
* **Selectores / lógica de navegación**:

  * Normalmente basado en `collect_links_from_page(base_url, link_selector)`.
  * Ej: `"a[href$='.pdf']"` para todos los links que terminan en `.pdf`.
  * Pueden ser más complejos:

    * Seguir paginación.
    * Click en botones “Ver más”.
    * Entrar a subpáginas antes de encontrar PDFs.

### Ejemplo (conceptual) de `ConsarLeyesScraper`

```python
# src/scraping/strategies/consar_leyes.py
from typing import List
from src.scraping.playwright_scraper import BaseScraper, collect_links_from_page

class ConsarLeyesScraper(BaseScraper):
    id = "consar_leyes"
    name = "CONSAR - Leyes"
    category = "leyes"
    store_env = "GEMINI_STORE_LEYES"
    base_url = "https://www.gob.mx/consar/documentos/leyes"

    async def fetch_pdf_urls(self) -> List[str]:
        # Estrategia simple:
        # 1. Abrir la página principal de leyes.
        # 2. Tomar todos los links que terminen en .pdf
        links = await collect_links_from_page(
            url=self.base_url,
            link_selector="a[href$='.pdf']"
        )
        return links
```

Este scraper:

1. Visita `https://www.gob.mx/consar/documentos/leyes`.
2. Extrae todos los `href` de links que terminen en `.pdf`.
3. Pasa esa lista de URLs al método `run()`.
4. `run()` descarga los PDFs nuevos a `data/leyes/`.
5. El orquestador los agrupa con otros PDFs nuevos de `leyes` y decide cuándo subirlos a Gemini.

---

## 6. Comandos disponibles hasta ahora

### 6.1. Preparar Playwright (local / build)

Instalar Playwright en el entorno de Python:

```bash
pip install playwright
python -m playwright install chromium
```

> Estos comandos se ejecutan dentro del **virtualenv** o en el contenedor Docker.

---

### 6.2. Ejecutar el scraping + indexado manualmente

Desde la raíz del proyecto:

```bash
python -m src.scraping.jobs.scrape_and_index
```

¿Qué hace este comando?

1. Carga la lista `SCRAPERS` definida en `scrape_and_index.py`.
2. Ejecuta cada scraper:

   * Abre páginas con Playwright.
   * Extrae links de PDFs.
   * Descarga sólo archivos nuevos en `data/<category>/`.
3. Agrupa archivos nuevos por `store_name` (leyes, trámites, glosario, …).
4. Aplica `filter_valid_files` para controlar:

   * Extensión,
   * Tamaño,
   * Otros criterios definidos en tu módulo de limpieza.
5. Si se cumple la condición de indexado:

   * Llama a `GeminiService.upload_files_to_store(...)` con:

     * `store_name`
     * `file_paths`
     * `wait_for_index=True`
6. Actualiza `data/meta/scraper_meta.json` con el timestamp del último indexado por store.

---

## 7. Cómo agregar un nuevo scraper (resumen operativo)

Para añadir una nueva fuente:

1. Crear un archivo en `src/scraping/strategies/`, por ejemplo:

   ```bash
   src/scraping/strategies/ine_docs.py
   ```

2. Heredar de `BaseScraper` y definir:

   * `id`
   * `name`
   * `category` (ej. `"info"`)
   * `store_env` (ej. `GEMINI_STORE_INFO`)
   * `base_url`
   * `fetch_pdf_urls()` con la lógica específica.

3. Añadir el scraper a la lista en `scrape_and_index.py`:

   ```python
   from src.scraping.strategies.ine_docs import IneDocsScraper

   SCRAPERS = [
       ConsarLeyesScraper(),
       ConsarTramitesScraper(),
       SepGlosarioScraper(),
       IneDocsScraper(),
   ]
   ```

4. Definir en `.env` la variable del store correspondiente:

   ```env
   GEMINI_STORE_INFO=fileSearchStores/info-XXXXXXXXXXXX
   ```

5. Ejecutar:

   ```bash
   python -m src.scraping.jobs.scrape_and_index
   ```

---

## 8. Consideraciones finales

* El módulo está diseñado para ser **extensible**:

  * Para agregar o quitar fuentes, basta con modificar `strategies/` y la lista `SCRAPERS`.
* La lógica de limpieza e indexado es **coherente con el pipeline RAG actual**:

  * Se reutiliza `filter_valid_files`.
  * Se reutiliza `GeminiService` para subir a File Search.
* El control de costos se maneja vía:

  * Tamaño y tipo de archivos permitidos.
  * `MIN_FILES_TO_INDEX` y `MAX_WAIT_DAYS`.
