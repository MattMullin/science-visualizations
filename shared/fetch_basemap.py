"""Fetch Natural Earth 110m land GeoJSON for the cartographic layer."""
import hashlib
from pathlib import Path

import requests

URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson"
OUT = Path(__file__).resolve().parent / "ne_110m_land.geojson"

if __name__ == "__main__":
    response = requests.get(URL, timeout=60)
    response.raise_for_status()
    OUT.write_bytes(response.content)
    print(f"Saved {OUT} SHA256 {hashlib.sha256(response.content).hexdigest()}")
