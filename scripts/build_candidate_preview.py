"""Build a candidate-only gallery artifact without changing approval state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_gallery import ROOT, build


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("--out", type=Path, default=ROOT / "output/candidate-preview")
    args = parser.parse_args()
    manifest = ROOT / "projects" / args.project_id / "manifest.json"
    if not manifest.is_file():
        raise SystemExit(f"Missing project: {args.project_id}")
    args.out.mkdir(parents=True, exist_ok=True)
    state = args.out / "mock-state.json"
    state.write_text(json.dumps({"pull_requests": [{"project_id": args.project_id,
                                                    "status": "approved_mock"}]}) + "\n", encoding="utf-8")
    build(args.out / "science", "/science/", state)
