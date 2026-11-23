"""Generate the 180-day editorial calendar and performance record schema."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generate(out: Path):
    config = json.loads((ROOT / "series.json").read_text(encoding="utf-8"))
    backlog = json.loads((ROOT / "backlog.json").read_text(encoding="utf-8"))
    start = dt.date.fromisoformat(config["planned_start_date"])
    projects = {p["number"]: p for p in backlog["projects"]}
    manifests = {}
    for path in (ROOT / "projects").glob("[0-9][0-9][0-9]-*/manifest.json"):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifests[manifest["id"]] = manifest
    entries = []
    for index in range(config["planned_days"]):
        number = index + 1
        project = projects.get(number, {})
        project_id = f"{number:03d}-{project['slug']}" if project else None
        manifest = manifests.get(project_id, {})
        assets = manifest.get("assets", {})
        review = manifest.get("review", {})
        entries.append({
            "day": number,
            "planned_date": (start + dt.timedelta(days=index)).isoformat(),
            "project_id": project_id,
            "production_status": project.get("status", "unassigned"),
            "github_pr_url": review.get("pull_request_url"),
            "github_pr_status": review.get("pull_request_status"),
            "review_status": review.get("status", "pending"),
            "video_url": assets.get("video", {}).get("url"),
            "demo_url": assets.get("demo_url"),
            "published_at": manifest.get("published_at"),
            "x_post_url": None,
            "x_impressions": None,
            "x_engagements": None,
            "followers_gained": None,
            "github_stars": None,
            "github_forks": None,
            "github_traffic_views": None,
        })
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"schema_version": 1, "timezone": config["timezone"],
                               "tentative": True, "entries": entries}, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(entries)} consecutive tentative days: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "output/calendar.json")
    args = parser.parse_args()
    generate(args.out)
