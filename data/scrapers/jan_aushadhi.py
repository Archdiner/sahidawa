"""Scraper for Jan Aushadhi store directory from genericdrugscan.com.

The official janaushadhi.gov.in is a JS SPA with no public API.
genericdrugscan.com mirrors 7,942 stores in static HTML, organized:
  /jan-aushadhi-stores/                -> state list
  /jan-aushadhi-stores/{state}/        -> district list with store counts
  /jan-aushadhi-stores/{state}/{dist}/ -> individual store cards

Fields per store: store_code, address, district, state, pin_code, phone, status.
"""

import csv
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.genericdrugscan.com/jan-aushadhi-stores"
OUTPUT_DIR = Path(__file__).parent.parent / "raw"
HEADERS = {"User-Agent": "SahiDawa-DataPipeline/0.1 (health-data-research)"}
REQUEST_DELAY = 1.0  # seconds between requests — be respectful


def get_soup(url: str) -> BeautifulSoup:
    """Fetch a URL and return parsed BeautifulSoup."""
    time.sleep(REQUEST_DELAY)
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def scrape_state_list() -> list[dict]:
    """Get list of all states with their URL slugs."""
    soup = get_soup(BASE_URL)
    states = []
    # State links follow pattern /jan-aushadhi-stores/{state-slug}/
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.startswith("/jan-aushadhi-stores/") and href.count("/") == 3:
            slug = href.strip("/").split("/")[-1]
            name = link.get_text(strip=True)
            if slug and name and slug != "jan-aushadhi-stores":
                states.append({"name": name, "slug": slug})
    return states


def scrape_district_list(state_slug: str) -> list[dict]:
    """Get list of districts for a state with their URL slugs."""
    url = f"{BASE_URL}/{state_slug}/"
    soup = get_soup(url)
    districts = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        prefix = f"/jan-aushadhi-stores/{state_slug}/"
        if href.startswith(prefix) and href != prefix:
            slug = href.strip("/").split("/")[-1]
            name = link.get_text(strip=True)
            # Filter out non-district links (nav, footer, etc.)
            if slug and name and len(name) < 100:
                districts.append({"name": name, "slug": slug})
    return districts


def scrape_district_stores(state_slug: str, district_slug: str) -> list[dict]:
    """Scrape all store cards from a district page."""
    url = f"{BASE_URL}/{state_slug}/{district_slug}/"
    soup = get_soup(url)
    stores = []

    # Store data is in card-like blocks with labeled fields
    # Look for consistent patterns: store code, address, pin, phone
    for card in soup.find_all(["div", "article", "section"], class_=True):
        text = card.get_text(separator="\n")
        if "PMBJK" not in text and "Address" not in text:
            continue

        store = {}
        # Extract store code
        code_match = re.search(r"(PMBJK\d+)", text)
        if code_match:
            store["store_code"] = code_match.group(1)

        # Extract labeled fields
        for line in text.split("\n"):
            line = line.strip()
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip().lower()
                val = val.strip()
                if "address" in key:
                    store["address"] = val
                elif "district" in key:
                    store["district"] = val
                elif "state" in key:
                    store["state"] = val
                elif "pin" in key:
                    store["pin_code"] = val
                elif "contact detail" in key or "phone" in key:
                    store["phone"] = val if val not in ("N/A", "TBU", "") else ""
                elif "status" in key:
                    store["status"] = val

        if store.get("store_code") or store.get("address"):
            stores.append(store)

    return stores


def scrape_all_stores(output_path: str | None = None) -> list[dict]:
    """Scrape all Jan Aushadhi stores across all states and districts.

    Writes incrementally to CSV so progress isn't lost on failures.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(output_path) if output_path else OUTPUT_DIR / "jan_aushadhi_stores.csv"

    fieldnames = ["store_code", "address", "district", "state", "pin_code", "phone", "status"]
    all_stores = []

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        states = scrape_state_list()
        print(f"Found {len(states)} states")

        for si, state in enumerate(states):
            print(f"[{si+1}/{len(states)}] Scraping {state['name']}...")
            try:
                districts = scrape_district_list(state["slug"])
            except Exception as e:
                print(f"  ERROR listing districts for {state['name']}: {e}")
                continue

            for di, district in enumerate(districts):
                try:
                    stores = scrape_district_stores(state["slug"], district["slug"])
                    for s in stores:
                        s.setdefault("state", state["name"])
                        s.setdefault("district", district["name"])
                        writer.writerow({k: s.get(k, "") for k in fieldnames})
                    all_stores.extend(stores)
                    if stores:
                        print(f"  {district['name']}: {len(stores)} stores")
                except Exception as e:
                    print(f"  ERROR scraping {district['name']}: {e}")
                    continue

            f.flush()

    print(f"\nTotal stores scraped: {len(all_stores)}")
    print(f"Saved to: {out}")
    return all_stores


if __name__ == "__main__":
    scrape_all_stores()
