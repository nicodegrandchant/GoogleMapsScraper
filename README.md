# GoogleMapsScraper
This is a full-featured Python pipeline that scrapes business listings from Google Maps by combining shapefile-based geography, keyword-based searches, and parallelized scraping with Selenium. It outputs clean CSV files for analysis.

Designed for grid-based, region-specific business discovery in Latin America — optimized for quality, retries, and modular post-processing.

## How to use:
run python3 Main.py

You will be prompted a few times, but mainly to:

1. Input the path to a .shp shapefile (default: Departamentos.shp)
2. Prompted whether or not you want to clean a column and will be prompted to input a column name to clean after being give the lisf of columns
3.Specify a radius (default: 1000 meters)
4. Choose whether to pick the department to by name or code
5. Input the name or code of the department depending on what you chose
6. If the file for the grid exists, whether you want to override it or not
7. If the file with all the jobs already exists, whether you want to override it or not

This script will:
- Clean department names
- Build a grid of lat/lon coordinates
- Export the grid to <City>_grid.csv
- Generate search jobs for each point and keyword
- Run a parallel scraper using Selenium
- Save results to results_<City>.csv
- Retry failed jobs if any
- Extract and save amenities to a separate CSV





## Structure:

Load and clean department names from shapefiles (CleanDep.py)
- Loads a shapefile and applies normalization + human-cleaned department name mappings. Saves a cleaned shapefile.

Create evenly spaced geographic coordinate grids inside selected departments (Departamento.py)
- Generates a latitude/longitude grid from a shapefile for a selected department.

Export coordinate grids to CSV (Gridexporter.py)
- Exports coordinate grid points to CSV format.


Generate scraping jobs per coordinate and keyword (GoogleMapsScraper.py)
- Core scraping logic. Loads grid, builds jobs, runs Selenium ChromeDriver, and extracts business listings with BeautifulSoup
- Parallel scraping using Selenium and BeautifulSoup

Holds the elements location (ItemTemplate.py)
- Defines the field parsing logic for Google Maps cards (e.g., name, link, rating, price, amenities).

Error logging and retry logic for failed jobs (Retry.py)
- Reloads failed jobs and retries them, then merges the results.

Modular result processing, amenity parsing, and ID tagging (Processor.py)
- 	Cleans and processes the scraped CSV: deduplication, amenity extraction, and field reformatting.

## Parameters

GLOBAL VARIABLES
SCROLL_MAX:	Max number of page-down scrolls per search job:	int	50
WAIT_TIMEOUT:	Seconds to wait for search results to appear:	int	20
NUM_PROCESSES:	Number of parallel scraping processes	int:	3
SCROLL_INTERVAL:	Delay between scroll actions:	float	0.8
SCROLL_TIMEOUT:	How long to wait before assuming scrolling has stalled:	int	4
KEYWORDS:	List of search terms used for scraping:	list,	16 strings, in Main.py
CLEAN_NAMES:	Mapping of incorrect → correct department names: dict, in Main.py

clean_department_names() in CleanDep.py
- shapefile_path = Path to input .shp file,	str,	default = User input
- clean_names	= Dict of normalization mappings,	dict, default =	CLEAN_NAMES
- dep_col =	Optional column name to clean,	str or None, default = Auto-detected

build_grid_from_shapefile() in Departamento.py
- shapefile_path = Path to cleaned shapefile,	str, default = From previous
- spacing =	Spacing (meters) between grid points,	float, default = radius_m * 0.8

export_grid_to_csv() in Gridexporter.py
- points = List of (lat, lon) tuples,	list, default =	From grid
- output_path =	Path to save CSV,	str, default =	cityname_grid.csv
- force	= Overwrite existing file without prompt,	bool, default =	False

GoogleMapsScraper.__init__() in GoogleMapsScraper.py
- driver_manager = Chrome Driver manager,	object, default =	Required
- jobs = List of (lat, lon, keyword) jobs,	list, default =	Required
- city_name	= City label used in logs/output,	str, default =	Required
- radius_m = Radius in meters for location filtering,	int, default = 1000
- scroll_max = Max page-downs before stopping, int,	default = From Main.py
- wait_timeout =	Wait time for page to load,	int, default =	From Main.py
- scroll_interval	= Delay between scrolls,	float,	default = From Main.py
- scroll_timeout =	How long to wait before scroll is considered stuck,	int, default =	From Main.py

retry_and_merge() in Retry.py
- master_df =	Original scraped data,	DataFrame, default = Required
- failed_jobs	= List of jobs that failed,	list, default =	Required
- city_name	= City name for output naming/logging,	str, default =	Required
- radius_m	= Radius in meters,	int, default =	1000
- scroll_max = Max page-downs,	int, default =	150
- wait_timeout = Max wait before page is considered failed,	int, default =	40

process_scraped_csv() in Processor.py
- filename =	Path to CSV file to clean and reformat,	str, default = User-defined



