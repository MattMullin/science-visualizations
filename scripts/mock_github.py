"""Local-only GitHub PR and review simulator. Never contacts GitHub."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from build_gallery import ROOT, build
from validate import validate

STATE = ROOT / "output/mock-github.json"
PROJECT = ROOT / "projects/001-saharan-dust"


def read_state(path=STATE):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"pull_requests": [], "feedback": []}


def save_state(state, path=STATE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def prepare(path=STATE):
    errors = validate(PROJECT)
    if errors:
        raise ValueError("Validation failed: " + "; ".join(errors))
    m = json.loads((PROJECT / "manifest.json").read_text(encoding="utf-8"))
    if not (ROOT / m["assets"]["video"]["local_path"]).is_file():
        raise ValueError("MP4 is missing; run the renderer first")
    state = read_state(path)
    if any(p["project_id"] == m["id"] and p["status"] in ("ready_for_review", "approved_mock") for p in state["pull_requests"]):
        raise ValueError("A mock PR already exists for this project")
    pr = {"number": len(state["pull_requests"]) + 1,
          "project_id": m["id"], "branch": "project/001-saharan-dust",
          "status": "ready_for_review", "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
          "url": "mock://pull/001-saharan-dust",
          "summary": m["summary"], "dataset_url": m["data"]["source_url"],
          "video_path": m["assets"]["video"]["local_path"],
          "test_result": "scripts/validate.py PASS", "deployment_preview": "local gallery after mock approval"}
    state["pull_requests"].append(pr)
    save_state(state, path)
    return pr


def review(decision, path=STATE):
    state = read_state(path)
    open_prs = [p for p in state["pull_requests"] if p["status"] == "ready_for_review"]
    if not open_prs:
        raise ValueError("No mock PR ready for review")
    pr = open_prs[-1]
    pr["status"] = "approved_mock" if decision == "approve" else "rejected_mock"
    pr["reviewed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    save_state(state, path)
    if decision == "approve":
        build(ROOT / "output/mock-gallery/science", "/mock-gallery/science/", path)
    return pr


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "approve", "reject", "status"))
    args = parser.parse_args()
    result = (prepare() if args.action == "prepare" else
              review(args.action) if args.action in ("approve", "reject") else read_state())
    print(json.dumps(result, indent=2))

