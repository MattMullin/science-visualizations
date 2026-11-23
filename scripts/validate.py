"""Scientific and packaging gates for project manifests."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(project: Path):
    errors = []
    manifest_path = project / "manifest.json"
    try:
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{manifest_path}: {exc}"]
    if project.name != m.get("id"):
        errors.append("manifest id does not match directory")
    for filename in ("README.md", "PROMPT.md", "fetch_data.py"):
        if not (project / filename).is_file():
            errors.append(f"missing {filename}")
    demo_path = m.get("assets", {}).get("demo_path")
    if demo_path and not (project / demo_path).is_file():
        errors.append(f"missing interactive demo {demo_path}")
    elif demo_path and hashlib.sha256((project / demo_path).read_bytes()).hexdigest() != m["assets"].get("demo_sha256"):
        errors.append("interactive demo checksum mismatch")
    for key in ("name", "provider", "source_url", "original_source_url", "variable", "units", "limitations"):
        if not m.get("data", {}).get(key):
            errors.append(f"missing data.{key}")
    if m.get("approved") and not m.get("assets", {}).get("source_url"):
        errors.append("approved manifest needs a public source URL")
    if m.get("published_at") and not m.get("approved"):
        errors.append("published project must be approved")
    if m.get("published_at") and not m.get("assets", {}).get("video", {}).get("url"):
        errors.append("published project needs an external video URL")
    thumb = project / m.get("assets", {}).get("thumbnail", "")
    if not thumb.is_file():
        errors.append(f"missing thumbnail {thumb}")
    elif hashlib.sha256(thumb.read_bytes()).hexdigest() != m["assets"].get("thumbnail_sha256"):
        errors.append("thumbnail checksum mismatch")
    snapshot = project / m.get("data", {}).get("snapshot", "")
    if not snapshot.is_file():
        errors.append(f"missing snapshot {snapshot}")
        return errors
    if hashlib.sha256(snapshot.read_bytes()).hexdigest() != m["data"].get("snapshot_sha256"):
        errors.append("snapshot checksum mismatch")
    basemap = ROOT / m.get("provenance", {}).get("basemap", "")
    if not basemap.is_file() or hashlib.sha256(basemap.read_bytes()).hexdigest() != m["provenance"].get("basemap_sha256"):
        errors.append("basemap missing or checksum mismatch")
    video = ROOT / m["assets"]["video"]["local_path"]
    if video.is_file() and hashlib.sha256(video.read_bytes()).hexdigest() != m["assets"]["video"].get("sha256"):
        errors.append("local video checksum mismatch")
    try:
        d = json.loads(snapshot.read_text(encoding="utf-8"))
        times = d["times_utc"]
        points = d["points"]
        if d["variable"] != m["data"]["variable"] or d["domain"] != m["data"]["model_domain"]:
            errors.append("snapshot variable or model domain differs from manifest")
        if len(points) < 20 or len(times) < 24:
            errors.append("insufficient spatial or temporal coverage")
        if times != sorted(set(times)):
            errors.append("time axis is not strictly increasing")
        for p in points:
            if len(p["dust"]) != len(times):
                errors.append("point timeseries length mismatch")
                break
            if not (-90 <= p["lat"] <= 90 and -180 <= p["lon"] <= 180):
                errors.append("coordinate out of range")
                break
            if any(v is not None and (not isinstance(v, (float, int)) or not math.isfinite(v) or v < 0) for v in p["dust"]):
                errors.append("invalid concentration")
                break
        if not any((v or 0) > 0 for p in points for v in p["dust"]):
            errors.append("all concentrations are zero or missing")
        if not d.get("request_url", "").startswith("https://air-quality-api.open-meteo.com/"):
            errors.append("missing exact API request URL")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"invalid snapshot: {exc}")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path)
    args = parser.parse_args()
    projects = [args.project] if args.project else sorted((ROOT / "projects").glob("[0-9][0-9][0-9]-*"))
    all_errors = []
    for project in projects:
        errors = validate(project)
        print(f"{project.name}: {'PASS' if not errors else 'FAIL'}")
        all_errors.extend(f"{project.name}: {e}" for e in errors)
    for error in all_errors:
        print(error)
    if all_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

