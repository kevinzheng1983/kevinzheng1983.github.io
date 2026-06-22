#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROFILE_URL = "https://scholar.google.com.au/citations?user=EM-l50cAAAAJ&hl=en"
AUTHOR_ID = "EM-l50cAAAAJ"
SERPAPI_URL = "https://serpapi.com/search.json"
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "scholar-metrics.json"


class ScholarStatsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_stats_table = False
        self.in_row = False
        self.in_cell = False
        self.row_cells = []
        self.cell_text = []
        self.stats = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "table" and attributes.get("id") == "gsc_rsb_st":
            self.in_stats_table = True
        elif self.in_stats_table and tag == "tr":
            self.in_row = True
            self.row_cells = []
        elif self.in_row and tag == "td":
            self.in_cell = True
            self.cell_text = []

    def handle_data(self, data):
        if self.in_cell:
            self.cell_text.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self.in_cell:
            self.row_cells.append("".join(self.cell_text).strip())
            self.in_cell = False
            self.cell_text = []
        elif tag == "tr" and self.in_row:
            if len(self.row_cells) >= 2:
                label = self.row_cells[0]
                digits = re.sub(r"[^0-9]", "", self.row_cells[1])
                if label and digits:
                    self.stats[label] = int(digits)
            self.in_row = False
            self.row_cells = []
        elif tag == "table" and self.in_stats_table:
            self.in_stats_table = False


def fetch_profile():
    request = Request(
        PROFILE_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_from_serpapi(api_key):
    query = urlencode(
        {
            "engine": "google_scholar_author",
            "author_id": AUTHOR_ID,
            "hl": "en",
            "api_key": api_key,
        }
    )
    request = Request(
        f"{SERPAPI_URL}?{query}",
        headers={"User-Agent": "Kai-Zheng-academic-homepage/1.0"},
    )
    with urlopen(request, timeout=30) as response:
        data = json.load(response)

    if data.get("error"):
        raise RuntimeError(f"SerpApi error: {data['error']}")

    table = data.get("cited_by", {}).get("table", [])
    citations = None
    h_index = None
    for row in table:
        if "citations" in row:
            citations = row["citations"].get("all")
        elif "h_index" in row:
            h_index = row["h_index"].get("all")

    if citations is None or h_index is None:
        raise RuntimeError("SerpApi response did not contain citations and h-index metrics.")

    return int(citations), int(h_index)


def fetch_directly():
    parser = ScholarStatsParser()
    parser.feed(fetch_profile())

    citations = parser.stats.get("Citations")
    h_index = parser.stats.get("h-index")
    if citations is None or h_index is None:
        raise RuntimeError(
            "Google Scholar metrics were not found; the response may be rate-limited or a CAPTCHA page."
        )

    return citations, h_index


def main():
    api_key = os.environ.get("SERPAPI_KEY")
    if api_key:
        citations, h_index = fetch_from_serpapi(api_key)
    elif os.environ.get("GITHUB_ACTIONS") == "true":
        raise RuntimeError(
            "SERPAPI_KEY is required in GitHub Actions because Google Scholar blocks hosted runner IPs."
        )
    else:
        citations, h_index = fetch_directly()

    metrics = {
        "citations": citations,
        "h_index": h_index,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": PROFILE_URL,
    }
    OUTPUT_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(f"Updated citations={citations}, h-index={h_index}")


if __name__ == "__main__":
    main()
