from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from math import radians, sin, cos, sqrt, atan2
import unicodedata
from urllib.parse import quote_plus
from math import radians, sin, cos, atan2, sqrt
from bs4 import BeautifulSoup
import pandas as pd
import logging
import os
import time
import sys
import re

from ItemTemplate import build_item

logging.basicConfig(level=logging.INFO)

def _setup_error_logger(city: str) -> logging.Logger:
    logger = logging.getLogger(f"errors.{city}")
    if not logger.handlers:
        logger.setLevel(logging.ERROR)
        fh = logging.FileHandler(f"errors_{city}.log", mode="a", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s"))
        logger.addHandler(fh)
    return logger


def _coords_from_link(url: str) -> tuple[float, float] | None:
    m = re.search(r"!3d([-\d.]+)!4d([-\d.]+)", url)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None

def haversine(lat, lon, lat2, lon2):
    """Returns distance in meters between two lat/lon points."""
    R = 6371000  # Earth radius in meters
    dlat = radians(lat2 - lat)
    dlon = radians(lon2 - lon)
    a = sin(dlat / 2)**2 + cos(radians(lat)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

def clean_text(text: str) -> str:
    if not text:
        return ''
    # 1) Normalize compatibility/composed forms
    text = unicodedata.normalize('NFKC', text)
    # 2) Replace non-breaking spaces
    text = text.replace('\xa0', ' ')
    # 3) Drop any Unicode “Other”/control characters
    cleaned = ''.join(
        c for c in text
        if c.isprintable() and not unicodedata.category(c).startswith('C')
    )
    return cleaned.strip()


class DriverManager:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None

    def start_driver(self):
        logging.info("Initializing Chrome driver (local)…")
        options = Options()
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=es-419")
        if self.headless:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")

        chrome_path = os.path.join(os.getcwd(), 'chromedriver-mac-arm64', 'chromedriver')
        service = Service(executable_path=chrome_path)
        self.driver = webdriver.Chrome(service=service, options=options)
        return self.driver

    def stop_driver(self):
        if self.driver:
            logging.info("Closing Chrome driver.")
            self.driver.quit()

class GridLoader:
    def __init__(self, grid_path: str, keywords: list):
        self.grid_path = grid_path
        self.keywords = keywords

    def load_grid(self):
        logging.info(f"Loading grid from {self.grid_path}...")
        df = pd.read_csv(self.grid_path)
        if df.empty:
            raise ValueError("CSV file is empty or not found.")
        if not {'latitude', 'longitude'}.issubset(df.columns):
            raise ValueError("CSV must contain 'latitude' and 'longitude' columns.")
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        coords = list(zip(df['latitude'], df['longitude']))
        logging.info(f"Loaded {len(coords)} coordinates from grid.")
        return coords

    def generate_jobs(self):
        coords = self.load_grid()
        jobs = []
        for i, (lat, lon) in enumerate(coords):
            for kw in self.keywords:
                jobs.append((lat, lon, kw))
            if i % 50 == 0:
                logging.info(f"Processed {i}/{len(coords)} coordinates...")
        logging.info(f"Generated {len(jobs)} search jobs.")
        return jobs

class GoogleMapsScraper:
    def __init__(self, driver_manager: DriverManager, jobs: list, city_name: str,
                 radius_m: int = 1000, scroll_max: int = 60, wait_timeout: int = 20,
                 scroll_interval: float = 1.0, scroll_timeout: int = 4):
        self.driver_manager = driver_manager
        self.jobs = jobs
        self.city_name = city_name
        self.radius_m = radius_m
        self.scroll_max = scroll_max
        self.wait_timeout = wait_timeout
        self.scroll_interval = scroll_interval
        self.scroll_timeout = scroll_timeout
        self.error_logger = _setup_error_logger(city_name)

    def _scroll_and_check(self, panel, check_interval=0.8, timeout=4, max_total_scrolls=100):

        scrolls = 0
        prev_n = 0
        stall_time = 0
        soup = None

        while scrolls < max_total_scrolls:
            panel.send_keys(Keys.PAGE_DOWN)
            time.sleep(check_interval)
            scrolls += 1

            html = panel.get_attribute("innerHTML")
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select("div.Nv2PK.THOPZb.CpccDe")
            n = len(cards)

            if n > prev_n:
                prev_n = n
                stall_time = 0  # reset stall counter if new cards load
            else:
                stall_time += check_interval

            if stall_time >= timeout:
                logging.info(f"🛑 Scroll halted after {scrolls} scrolls and {n} cards.")
                break
        
        return soup


    def scrape(self):
        # ── 1) Start the browser ──
        driver = self.driver_manager.start_driver()

        results: list[dict] = []
        failed: list[tuple] = []
        total = len(self.jobs)

        try:
            # ── 2) Main loop ──
            for idx, (lat, lon, kw) in enumerate(self.jobs, start=1):
                before = len(results)
                try:
                    lat, lon = float(lat), float(lon)
                    logging.info("Job %s/%s: %s at (%.5f, %.5f)", idx, total, kw, lat, lon)

                    # ── (4) Include locale param for stable Spanish panels ──
                    url = (
                        f"https://www.google.com/maps/search/{quote_plus(kw)}/"
                        f"@{lat},{lon},{self.radius_m}m/data=!3m1!4b1?hl=es-419&gl=PY"
                    )
                    driver.get(url)

                    WebDriverWait(driver, self.wait_timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a.hfpxzc"))
                    )
                    time.sleep(1)

                    panel = driver.find_element(
                        By.XPATH, f"//div[@aria-label='Resultados de {kw}']"
                    )
                    soup = self._scroll_and_check(
                        panel,
                        check_interval=self.scroll_interval,
                        timeout=self.scroll_timeout,
                        max_total_scrolls=self.scroll_max
                    )
                    if not soup:
                        self.error_logger.warning("No soup for '%s' @(%f,%f)", kw, lat, lon)
                        failed.append((lat, lon, kw))
                        continue

                    # pull out every result link
                    # ── grab every result link anchor ──
                    anchors = soup.select("a.hfpxzc[aria-label]")
                    logging.info("🔎 Found %d result links for %s", len(anchors), kw)

                    # if absolutely nothing showed up, mark as failure
                    if not anchors:
                        failed.append((lat, lon, kw))
                        continue

                    accepted = 0
                    skipped_outside_radius = 0

                    for anchor in anchors:
                        link = anchor.get("href", "")
                        coords = _coords_from_link(link)
                        if not coords:
                            continue

                        # radius filter
                        dist_m = haversine(lat, lon, coords[0], coords[1])
                        if dist_m > self.radius_m:
                            skipped_outside_radius += 1
                            continue

                        # try several ways to find the "card" wrapper
                        card = (
                            anchor.find_parent("div", class_="CpccDe") or
                            anchor.find_parent("div", class_="Nv2PK") or
                            anchor.find_parent("div", class_="section-result")
                        )
                        if not card:
                            logging.warning("⚠️  Couldn't find card container for %s → skipping", link)
                            continue

                        def safe_get_text(elem, default=""):
                            return clean_text(elem.get_text(strip=True)) if elem else default

                        try:
                            item = build_item(
                                version="loc1",
                                card=card,
                                coords=coords,
                                kw=kw,
                                anchor=anchor,
                                safe_get_text=safe_get_text,
                                clean_text=clean_text
                            )
                            results.append(item)
                            accepted += 1
                        except Exception as ex:
                            logging.warning("Error building item for %s: %s", kw, ex)

                    # per-job summary
                    if skipped_outside_radius:
                        logging.info("⛔ Filtered %d outside %dm radius", skipped_outside_radius, self.radius_m)

                except Exception as exc:
                    logging.error("Job %s failed: %s", idx, exc)
                    self.error_logger.error(
                        "Job %s failed for %s at (%s,%s) %s",
                        idx, kw, lat, lon, repr(exc), exc_info=True
                    )
                    failed.append((lat, lon, kw))
                finally:
                    # ── snapshot after each job ──
                    after = len(results)
                    new = after - before
                    if new:
                        logging.info("✅ Job %s appended %d records", idx, new)
                    else:
                        logging.info("🚨 Job %s yielded NO results", idx)

        finally:
            # ── (3) Always quit the browser, even if something blows up ──
            driver.quit()

        # ── unified DataFrame creation + dedupe ──
        df = (
            pd.DataFrame.from_records(results)
              .reset_index(drop=True)
        ) if results else pd.DataFrame(columns=[
            "latitude","longitude","keyword","name","link","rating",
            "category","address","phone","hours","services","price","amenities"
        ])

        logging.info("✅ scrape() returning %d rows and %d failed jobs", len(df), len(failed))
        return df, failed
