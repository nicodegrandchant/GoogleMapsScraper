import logging, os, pandas as pd
from GoogleMapsScraper import GoogleMapsScraper, DriverManager

def load_failed(path: str):
    if not os.path.exists(path):
        logging.info("No failures to retry.")
        return []
    df = pd.read_csv(path)
    return [
        (row.latitude, row.longitude, row.keyword)
        for row in df.itertuples(index=False)
        if pd.notna(row.latitude) and pd.notna(row.longitude)
    ]

def retry_and_merge(
    master_df: pd.DataFrame,
    failed_jobs: list,
    city_name: str,
    radius_m: int = 1000,
    scroll_max: int = 150,
    wait_timeout: int = 40
) -> pd.DataFrame:
    if not failed_jobs:
        return master_df

    mgr = DriverManager(headless=True)
    scraper = GoogleMapsScraper(
        mgr, failed_jobs, city_name,
        radius_m=1000,
        scroll_max=120,
        wait_timeout=35,
        scroll_interval=1.5,
        scroll_timeout=8
    )
    retry_df, still = scraper.scrape()

    combined = pd.concat([master_df, retry_df], ignore_index=True)
    combined = combined.drop_duplicates("link").reset_index(drop=True)

    # scraper already wrote any still‑failed back to CSV
    return combined
