# GoogleMapsScraper

Este es un pipeline completo en Python que extrae listados de negocios desde Google Maps combinando geografía basada en archivos shapefile, búsquedas por palabras clave y scraping paralelo usando Selenium. Genera archivos CSV limpios para su análisis.

Diseñado para el descubrimiento de negocios por regiones específicas en América Latina — optimizado para calidad, reintentos y post-procesamiento modular.

## Cómo usarlo:
Ejecuta:
python3 Main.py

Se te pedirá que ingreses algunos datos, principalmente:
1. Ruta al archivo .shp (por defecto: Departamentos.shp)
2. Si deseas limpiar los nombres de los departamentos y qué columna limpiar (se mostrará una lista)
3. Especificar el radio de búsqueda en metros (por defecto: 1000)
4. Elegir si deseas seleccionar el departamento por nombre o por código
5. Ingresar el nombre o código del departamento, según la opción anterior
6. Confirmar si deseas sobrescribir el archivo de la grilla si ya existe
7. Confirmar si deseas sobrescribir el archivo de trabajos si ya existe

Este script hará lo siguiente:
- Limpia los nombres de los departamentos
- Crea una grilla de coordenadas latitud/longitud
- Exporta la grilla a <Ciudad>_grid.csv
- Genera trabajos de scraping por punto y palabra clave
- Ejecuta el scraper en paralelo con Selenium
- Guarda los resultados en results_<Ciudad>.csv
- Reintenta los trabajos fallidos automáticamente
- Extrae y guarda las amenidades en un CSV separado

## Estructura del proyecto:
CleanDep.py
- Carga un archivo shapefile y aplica normalización + mapeo manual de nombres de departamentos. Guarda un shapefile limpio.

Departamento.py
- Genera una grilla de coordenadas desde un departamento específico del shapefile.

Gridexporter.py
- Exporta la grilla de coordenadas a formato CSV.

GoogleMapsScraper.py
- Lógica principal del scraping. Carga la grilla, genera trabajos, ejecuta ChromeDriver de Selenium y extrae negocios con BeautifulSoup.
- Soporta scraping paralelo.

ItemTemplate.py
- Define cómo extraer campos como nombre, calificación, enlace, precio y amenidades de las tarjetas de Google Maps.

Retry.py
- Reintenta trabajos fallidos y combina los resultados con los exitosos.

Processor.py
- Limpia y procesa el CSV resultante: deduplicación, extracción de amenidades y reformateo de campos.

## Parámetros
Variables globales (Main.py)
- SCROLL_MAX: Máximo de desplazamientos hacia abajo por búsqueda (int, por defecto: 50)
- WAIT_TIMEOUT: Tiempo máximo para esperar carga de resultados (int, por defecto: 20)
- NUM_PROCESSES: Número de procesos en paralelo (int, por defecto: 3)
- SCROLL_INTERVAL: Tiempo entre desplazamientos (float, por defecto: 0.8)
- SCROLL_TIMEOUT: Tiempo máximo sin cambio antes de detener scroll (int, por defecto: 4)
- KEYWORDS: Lista de palabras clave para búsqueda (lista de 16 términos, en Main.py)
- CLEAN_NAMES: Diccionario de correcciones de nombres de departamentos (en Main.py)

clean_department_names() – CleanDep.py
- shapefile_path: Ruta al archivo .shp (str)
- clean_names: Diccionario de nombres a corregir (dict)
- dep_col: Columna a limpiar (opcional, str o None)

build_grid_from_shapefile() – Departamento.py
- shapefile_path: Ruta al shapefile limpio (str)
- spacing: Distancia entre puntos en la grilla (float, por defecto: radio_m * 0.8)

export_grid_to_csv() – Gridexporter.py
- points: Lista de coordenadas (lat, lon) (list)
- output_path: Ruta para guardar CSV (str)
- force: Sobrescribir archivo existente (bool)

GoogleMapsScraper.init() – GoogleMapsScraper.py
- driver_manager: Administrador del driver de Selenium (objeto)
- jobs: Lista de trabajos (lat, lon, palabra clave)
- city_name: Nombre de ciudad para etiquetas/logs (str)
- radius_m: Radio en metros para filtrar resultados (int, por defecto: 1000)
- scroll_max, wait_timeout, scroll_interval, scroll_timeout: Parámetros de scraping, definidos en Main.py

retry_and_merge() – Retry.py
- master_df: Datos ya scrapeados (DataFrame)
- failed_jobs: Lista de trabajos fallidos (list)
- city_name: Ciudad para logs y archivos de salida (str)
- radius_m, scroll_max, wait_timeout: Parámetros para reintento

process_scraped_csv() – Processor.py
- filename: Ruta al archivo CSV que será limpiado y reformateado (str)

## Dependencias
Instala todo con:
pip install -r requirements.txt

Contenido de requirements.txt:
  pandas
  geopandas
  shapely
  numpy
  selenium
  beautifulsoup4

## Archivos de salida
results_<CITY>.csv: Listado de negocios encontrados

results_<CITY>_amenities.csv: Amenidades extraídas

<CITY>_grid.csv: Grilla de coordenadas generada

all_jobs_<CITY>.csv: Todos los trabajos realizados

jobs_failed_<CITY>.csv: Trabajos fallidos (para retry)

También se incluyen ejemplos en la carpeta sample_output (menos jobs_failed ya que sigue la misma estructura que all_jobs).

Autor:
Nicolas de Grandchanthttps://github.com/nicodegrandchant
