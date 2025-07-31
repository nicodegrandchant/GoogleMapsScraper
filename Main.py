import logging
import os
import pandas as pd
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context

from CleanDep   import clean_department_names
from Departamento import build_grid_from_shapefile
from Gridexporter import export_grid_to_csv
from GoogleMapsScraper import DriverManager, GridLoader, GoogleMapsScraper
from Retry      import retry_and_merge, load_failed
from Processor import process_scraped_csv

# ───── GLOBAL CONFIG ─────────────────────────────────────────
SCROLL_MAX       = 50        # how many PAGE_DOWNs per job
WAIT_TIMEOUT     = 20        # seconds to wait for results panel
NUM_PROCESSES    = 3         # parallel job chunks
SCROLL_INTERVAL  = 0.8       # time between scrolls
SCROLL_TIMEOUT   = 4         # seconds to wait with no new cards

KEYWORDS = [
    "Centro Comercial", "Mercado", "Concesionario", "Supermercado",
    "Clinica", "Hotel", "Centro Medico", "Hospital", "Universidad",
    "Restaurante", "Galeria Comercial", "Tienda", "Store",
    "Consultorio", "Shopping", "Farmacia"
]

CLEAN_NAMES = {
    "ALTO PARANÃ": "ALTO PARANÁ", "ASUNCIÃN": "ASUNCIÓN",
    "BOQUERÃN": "BOQUERÓN",  "CAAGUAZÃ": "CAAGUAZÚ",
    "CAAZAPÃ": "CAAZAPÁ",   "CANINDEYÃ": "CANINDEYÚ",
    "CONCEPCIÃN": "CONCEPCIÓN", "GUAIRÃ": "GUAIRÁ",
    "ITAPÃA": "ITAPÚA",     "ÃEEMBUCÃ": "ÑEEMBUCÚ",
    "PARAGUARÃ": "PARAGUARÁ"
}


def process_job_chunk(chunk, city_name, radius_m):
    mgr = DriverManager(headless=True)
    scraper = GoogleMapsScraper(
        driver_manager=mgr,
        jobs=chunk,
        city_name=city_name,
        radius_m=radius_m,
        scroll_max=SCROLL_MAX,
        wait_timeout=WAIT_TIMEOUT,
        scroll_interval=SCROLL_INTERVAL,
        scroll_timeout=SCROLL_TIMEOUT,
    )
    df, failed = scraper.scrape()
    logging.info(f"🔎 Chunk done: {len(df)} rows, {len(failed)} failures")
    return df, failed


def chunk_jobs(jobs, n):
    k, m = divmod(len(jobs), n)
    return [
        jobs[i*k + min(i,m):(i+1)*k + min(i+1,m)]
        for i in range(n)
    ]


def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("🚀 Starting full scrape workflow")

    # 1) Clean shapefile names
    shp = input("Shapefile path (default Departamentos.shp): ").strip() or "Departamentos.shp"
    cleaned_shp = clean_department_names(shp, CLEAN_NAMES)

    # 2) Build grid
    rad = input("Search radius in meters (default 1000): ").strip()
    radius_m = int(rad) if rad.isdigit() else 1000
    spacing = radius_m * 0.8
    grid_pts, city_name = build_grid_from_shapefile(cleaned_shp, spacing = spacing)

    # 3) Export grid CSV
    grid_csv = f"{city_name}_grid.csv"
    export_grid_to_csv(grid_pts, grid_csv, force=False)

    # 4) Generate jobs
    loader = GridLoader(grid_csv, KEYWORDS)
    jobs = loader.generate_jobs()
    jobs_csv = f"all_jobs_{city_name}.csv"
    
    if os.path.exists(jobs_csv):
        resp = input(f"⚠️ '{jobs_csv}' already exists. Overwrite? [y/n]: ").strip().lower()
        if resp == 'y':
            pd.DataFrame(jobs, columns=["latitude","longitude","keyword"]) \
            .to_csv(jobs_csv, index=False)
            logging.info("✅ Overwrote existing job file.")
        else:
            logging.info("📄 Using existing job file instead.")
            jobs = pd.read_csv(jobs_csv).values.tolist()
    else:
        pd.DataFrame(jobs, columns=["latitude","longitude","keyword"]) \
        .to_csv(jobs_csv, index=False)
        logging.info("✅ Saved new job file.")


    # 5) Parallel scrape
    job_chunks = chunk_jobs(jobs, NUM_PROCESSES)
    ctx = get_context("spawn")
    all_results, all_failed = [], []

    with ProcessPoolExecutor(max_workers=NUM_PROCESSES, mp_context=ctx) as exe:
        futures = [
            exe.submit(process_job_chunk, chunk, city_name, radius_m)
            for chunk in job_chunks
        ]
        for fut in futures:
            df_chunk, failed_chunk = fut.result()
            all_results.append(df_chunk)
            all_failed.extend(failed_chunk)

    # 7) Merge results and de-duplicate
    merged = pd.concat(all_results, ignore_index=True)
    total_before = len(merged)

    deduped = (
        merged
        .drop_duplicates(subset=["link"])
        .sort_values(["longitude", "latitude"])
        .reset_index(drop=True)
    )
    total_after = len(deduped)
    removed = total_before - total_after

    # log how many got deduped
    logging.info("🔀 Dropped %d duplicate rows (from %d → %d)", removed, total_before, total_after)
    logging.info("✅ Final results: %d rows → results_%s.csv", total_after, city_name)

    # write out
    deduped.to_csv(f"results_{city_name}.csv", index=False)
    # Only postprocess if there were NO failures
    if not all_failed:
        process_scraped_csv(f"results_{city_name}.csv")

    # 8) Write the single failure file
    failure_file = f"jobs_failed_{city_name}.csv"
    if all_failed:
        pd.DataFrame(all_failed, columns=["latitude","longitude","keyword"]) \
          .to_csv(failure_file, index=False)
        logging.info("💾 Wrote %d failed jobs → %s", len(all_failed), failure_file)
    else:
        if os.path.exists(failure_file):
            os.remove(failure_file)
            logging.info("🗑️  No failures → removed %s", failure_file)

    # 9) Retry failures
    failed_jobs = load_failed(failure_file)
    if failed_jobs:
        # feed full_df back into retry_and_merge, overwrite full_df
        full_df = retry_and_merge(
            deduped,
            failed_jobs,
            city_name,
            radius_m=radius_m
        )
        full_df.to_csv(f"results_{city_name}.csv", index=False)
        process_scraped_csv(f"results_{city_name}.csv")
        logging.info("🔁 Retried failures; now %d rows → %s", len(full_df), f"results_{city_name}.csv")

    logging.info("🎉 Workflow complete.")


if __name__ == "__main__":
    main()