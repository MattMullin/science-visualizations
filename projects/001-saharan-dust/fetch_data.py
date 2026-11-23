"""Fetch a dated CAMS European dust snapshot via Open-Meteo.

The committed small snapshot makes the render deterministic. Refreshing the
snapshot intentionally changes its forecast provenance and must be reviewed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

import requests

API = "https://air-quality-api.open-meteo.com/v1/air-quality"
HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "dust_snapshot.json"
LATS = [30, 33, 36, 39, 42, 45]
LONS = [-18, -13, -8, -3, 2, 7, 12, 17]


def get_points(points, **params):
    query = {
        "latitude": ",".join(str(p[0]) for p in points),
        "longitude": ",".join(str(p[1]) for p in points),
        "hourly": "dust",
        "domains": "cams_europe",
        "timezone": "GMT",
        **params,
    }
    response = requests.get(API, params=query, timeout=90)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        payload = [payload]
    if len(payload) != len(points):
        raise ValueError("API returned the wrong number of locations")
    for item in payload:
        values = item.get("hourly", {}).get("dust", [])
        times = item.get("hourly", {}).get("time", [])
        if not values or len(values) != len(times):
            raise ValueError("Missing or inconsistent dust timeseries")
        if item.get("hourly_units", {}).get("dust") not in ("μg/m³", "µg/m³"):
            raise ValueError("Unexpected dust concentration unit")
    return payload, response.url


def select_day(sample):
    times = sample[0]["hourly"]["time"]
    scores = {}
    for index, stamp in enumerate(times):
        day = stamp[:10]
        values = [s["hourly"]["dust"][index] for s in sample]
        values = [v for v in values if isinstance(v, (int, float)) and v >= 0]
        if values:
            scores.setdefault(day, []).extend(values)
    if not scores:
        raise ValueError("No valid modeled dust values in sample")
    # The peak and spatial mean favor a visible, regionally meaningful event.
    return max(scores, key=lambda d: max(scores[d]) + sum(scores[d]) / len(scores[d]))


def fetch(day=None):
    sample_points = [(lat, lon) for lat in (30, 36, 42) for lon in (-13, -3, 7, 17)]
    if day is None:
        sample, sample_url = get_points(sample_points, past_days=90, forecast_days=0)
        day = select_day(sample)
    else:
        sample_url = None
        dt.date.fromisoformat(day)
    start = dt.date.fromisoformat(day) - dt.timedelta(days=1)
    end = dt.date.fromisoformat(day) + dt.timedelta(days=1)
    points = [(lat, lon) for lat in LATS for lon in LONS]
    result, url = get_points(points, start_date=start.isoformat(), end_date=end.isoformat())
    times = result[0]["hourly"]["time"]
    if len(times) < 24:
        raise ValueError("Not enough hourly data")
    rows = []
    for point, item in zip(points, result):
        if item["hourly"]["time"] != times:
            raise ValueError("Time grids differ across locations")
        rows.append({"lat": point[0], "lon": point[1], "dust": item["hourly"]["dust"]})
    snapshot = {
        "schema_version": 1,
        "source": "CAMS European Air Quality Forecast via Open-Meteo Air Quality API",
        "variable": "dust",
        "units": "micrograms per cubic meter",
        "height": "approximately 10 m above ground",
        "domain": "cams_europe",
        "event_day": day,
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "request_url": url,
        "selection_request_url": sample_url,
        "times_utc": times,
        "points": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes((json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(f"Saved {len(rows)} locations × {len(times)} hours; event {day}: {OUT}")
    print(f"SHA256 {hashlib.sha256(OUT.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", help="YYYY-MM-DD; otherwise select strongest recent event")
    args = parser.parse_args()
    fetch(args.day)

