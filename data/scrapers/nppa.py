"""Scraper for NPPA DPCO 2026 ceiling prices.

The official NPPA site (nppa.gov.in) publishes PDFs. However, laafon.com
has already parsed the 2026 ceiling price data into an interactive page
with the data embedded as a JS constant (NPPA_DATA).

This scraper extracts that embedded data and writes it to CSV.

Fallback: We also try the official NPPA gazette notification PDFs.
"""

import csv
import json
import re
from pathlib import Path

import requests

OUTPUT_DIR = Path(__file__).parent.parent / "raw"
LAAFON_URL = "https://laafon.com/nppa-dpco-2026-drug-price-list/"
HEADERS = {"User-Agent": "SahiDawa-DataPipeline/0.1 (health-data-research)"}


def scrape_nppa_from_laafon(output_path: str | None = None) -> list[dict]:
    """Extract NPPA ceiling price data from laafon.com's embedded JS."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(output_path) if output_path else OUTPUT_DIR / "nppa_ceiling_prices.csv"

    print("Fetching NPPA data from laafon.com...")
    resp = requests.get(LAAFON_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    # The page embeds data as: const NPPA_DATA = [{...}, ...];
    # or similar JS constant. Try multiple patterns.
    patterns = [
        r"(?:const|var|let)\s+NPPA_DATA\s*=\s*(\[[\s\S]*?\]);",
        r"data\s*[:=]\s*(\[[\s\S]*?\])\s*[;,]",
        r"formulations\s*[:=]\s*(\[[\s\S]*?\])\s*[;,]",
    ]

    data = None
    for pattern in patterns:
        match = re.search(pattern, resp.text)
        if match:
            try:
                raw = match.group(1)
                # Clean up JS to valid JSON (single quotes → double, trailing commas)
                raw = raw.replace("'", '"')
                raw = re.sub(r",\s*([}\]])", r"\1", raw)
                data = json.loads(raw)
                break
            except json.JSONDecodeError:
                continue

    if not data:
        # Fallback: try to extract from HTML table
        print("Could not find embedded JS data. Trying HTML table extraction...")
        data = _extract_from_html_table(resp.text)

    if not data:
        print("ERROR: Could not extract NPPA data from laafon.com")
        print("You may need to manually download from nppa.gov.in")
        return []

    # Normalize field names
    normalized = []
    for entry in data:
        row = {
            "drug_name": entry.get("drug_name") or entry.get("name") or entry.get("drug", ""),
            "dosage_form": entry.get("dosage_form") or entry.get("form", ""),
            "strength": entry.get("strength") or entry.get("dose", ""),
            "unit": entry.get("unit", ""),
            "ceiling_price_2026": entry.get("price_2026")
            or entry.get("price")
            or entry.get("ceiling_price", ""),
            "so_number": entry.get("so_number") or entry.get("so", ""),
            "so_date": entry.get("so_date") or entry.get("date", ""),
        }
        normalized.append(row)

    fieldnames = [
        "drug_name",
        "dosage_form",
        "strength",
        "unit",
        "ceiling_price_2026",
        "so_number",
        "so_date",
    ]
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(normalized)

    print(f"Extracted {len(normalized)} ceiling price entries")
    print(f"Saved to: {out}")
    return normalized


def _extract_from_html_table(html: str) -> list[dict]:
    """Fallback: extract from HTML table if JS extraction fails."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        return []

    # Find the table with drug data (largest table usually)
    table = max(tables, key=lambda t: len(t.find_all("tr")))
    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    # Extract headers
    headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]

    data = []
    for row in rows[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
        if len(cells) == len(headers):
            entry = dict(zip(headers, cells))
            data.append(entry)

    return data


if __name__ == "__main__":
    scrape_nppa_from_laafon()
