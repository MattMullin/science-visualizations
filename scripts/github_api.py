"""Authenticated GitHub REST publishing adapter.

Intended for a private orchestrator with a short-lived, narrowly scoped token.
Never used by the local mock workflow. No merge happens in submit().
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com"


class GitHub:
    def __init__(self, repository, token):
        if not repository or "/" not in repository or not token:
            raise ValueError("GITHUB_REPOSITORY and GITHUB_TOKEN are required")
        self.repository = repository
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}",
                                     "Accept": "application/vnd.github+json",
                                     "X-GitHub-Api-Version": "2022-11-28"})

    def call(self, method, path, **kwargs):
        response = self.session.request(method, API + f"/repos/{self.repository}" + path,
                                        timeout=60, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None

    def submit_project(self, project_id, base="main"):
        project = ROOT / "projects" / project_id
        manifest = json.loads((project / "manifest.json").read_text(encoding="utf-8"))
        if manifest["approved"]:
            raise ValueError("Submit only unapproved candidate manifests")
        from validate import validate
        errors = validate(project)
        if errors:
            raise ValueError("Validation failed: " + "; ".join(errors))
        base_ref = self.call("GET", f"/git/ref/heads/{base}")
        base_sha = base_ref["object"]["sha"]
        base_commit = self.call("GET", f"/git/commits/{base_sha}")
        branch = f"project/{project_id}"
        self.call("POST", "/git/refs", json={"ref": f"refs/heads/{branch}", "sha": base_sha})
        files = list(project.rglob("*"))
        files = [p for p in files if p.is_file() and p.suffix.lower() not in (".mp4", ".mov", ".webm")]
        tree_entries = []
        for file in files:
            rel = file.relative_to(ROOT).as_posix()
            content = file.read_bytes()
            if len(content) > 5_000_000:
                raise ValueError(f"Oversized Git asset: {rel}")
            blob = self.call("POST", "/git/blobs", json={"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"})
            tree_entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = self.call("POST", "/git/trees", json={"base_tree": base_commit["tree"]["sha"], "tree": tree_entries})
        commit = self.call("POST", "/git/commits", json={"message": f"Add {manifest['title']} candidate", "tree": tree["sha"], "parents": [base_sha]})
        self.call("PATCH", f"/git/refs/heads/{branch}", json={"sha": commit["sha"], "force": False})
        video = manifest["assets"]["video"].get("url") or "Video preview pending external upload"
        body = (f"## {manifest['title']}\n\n{manifest['summary']}\n\n"
                f"**Video:** {video}\n\n"
                f"**Scientific source:** {manifest['data']['source_url']}\n\n"
                f"**Limitations:** {manifest['data']['limitations']}\n\n"
                f"**Validation:** run `python scripts/validate.py` and the project reproduction command.\n\n"
                f"**Deployment preview:** available after the gallery preview workflow runs.\n\n"
                "Scientific and editorial approval required. Do not auto-merge.")
        return self.call("POST", "/pulls", json={"title": f"Project {manifest['number']:03d}: {manifest['title']}",
                                                  "head": branch, "base": base, "body": body, "draft": True})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    args = parser.parse_args()
    github = GitHub(os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN"))
    pr = github.submit_project(args.project_id)
    print(pr["html_url"])

