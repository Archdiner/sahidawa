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
SITE_ROOT = "https://www.genericdrugscan.com"
OUTPUT_DIR = Path(__file__).parent.parent / "raw"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_DELAY = 1.5  # seconds between requests — be respectful


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
    seen = set()
    prefix = f"{SITE_ROOT}/jan-aushadhi-stores/"
    for link in soup.find_all("a", href=True):
        href = link["href"].rstrip("/")
        # Match both full URLs and relative paths
        if href.startswith(prefix):
            slug = href[len(prefix):].strip("/")
        elif href.startswith("/jan-aushadhi-stores/"):
            slug = href[len("/jan-aushadhi-stores/"):].strip("/")
        else:
            continue

        # Must be a single-level slug (state, not state/district)
        if not slug or "/" in slug or slug in seen:
            continue

        name = link.get_text(strip=True)
        if name and len(name) < 80:
            states.append({"name": name, "slug": slug})
            seen.add(slug)
    return states


def scrape_district_list(state_slug: str) -> list[dict]:
    """Get list of districts for a state with their URL slugs."""
    url = f"{BASE_URL}/{state_slug}"
    soup = get_soup(url)
    districts = []
    seen = set()
    # Match both full URLs and relative paths for districts
    full_prefix = f"{SITE_ROOT}/jan-aushadhi-stores/{state_slug}/"
    rel_prefix = f"/jan-aushadhi-stores/{state_slug}/"
    for link in soup.find_all("a", href=True):
        href = link["href"].rstrip("/")
        if href.startswith(full_prefix):
            slug = href[len(full_prefix):].strip("/")
        elif href.startswith(rel_prefix):
            slug = href[len(rel_prefix):].strip("/")
        else:
            continue

        if not slug or "/" in slug or slug in seen:
            continue

        name = link.get_text(strip=True)
        if name and len(name) < 100:
            districts.append({"name": name, "slug": slug})
            seen.add(slug)
    return districts


def scrape_district_stores(state_slug: str, district_slug: str) -> list[dict]:
    """Scrape all store cards from a district page.

    Page structure is label/value pairs on separate lines:
      Store Code
      PMBJK00863
      Address
      Mm-1/70 Sector-A ...
      District
      Lucknow
      ...
    """
    url = f"{BASE_URL}/{state_slug}/{district_slug}"
    soup = get_soup(url)
    stores = []
    seen_codes = set()

    full_text = soup.get_text(separator="\n")
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]

    # Walk through lines; when we see "Store Code" label, the next line is the code
    i = 0
    while i < len(lines):
        if lines[i] == "Store Code" and i + 1 < len(lines):
            code = lines[i + 1].strip()
            if not re.match(r"PMBJK\d+", code):
                i += 1
                continue
            if code in seen_codes:
                i += 1
                continue
            seen_codes.add(code)

            store = {"store_code": code}
            # Read subsequent label/value pairs until we hit next "Store Code" or end
            j = i + 2
            while j < len(lines):
                label = lines[j].strip()
                if label == "Store Code":
                    break  # next store
                if label in ("Address", "District", "State", "Pin Code",
                             "Contact Person", "Contact Detail", "Status") and j + 1 < len(lines):
                    val = lines[j + 1].strip()
                    if label == "Address":
                        store["address"] = val
                    elif label == "District":
                        store["district"] = val
                    elif label == "State":
                        store["state"] = val
                    elif label == "Pin Code":
                        pin = re.search(r"\d{6}", val)
                        store["pin_code"] = pin.group(0) if pin else val
                    elif label == "Contact Detail":
                        phone = val
                        if phone.startswith("Mobile---"):
                            phone = phone.replace("Mobile---", "").strip()
                        if phone in ("N", "N/A", "TBU", "To be updated", ""):
                            phone = ""
                        store["phone"] = phone
                    elif label == "Status":
                        store["status"] = val
                    j += 2  # skip label + value
                else:
                    j += 1

            if store.get("address") or store.get("pin_code"):
                stores.append(store)
            i = j
        else:
            i += 1

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
