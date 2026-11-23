# Science Visualizations

An open-source science visualization atlas designed for a 180-day publishing
series. The reference project is [Saharan Dust](projects/001-saharan-dust/README.md).

This checkout contains the **public project package and reusable renderer**.
The private scheduling, credential and long-running worker infrastructure is
kept outside this public repository. The current reference is a candidate, not
an approved release.

## Reference workflow

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/validate.py
python -m pytest -q
python engines/dust/render.py --seconds 20 --fps 20
python scripts/mock_github.py prepare
python scripts/dashboard.py
```

Open `http://127.0.0.1:8765/` to inspect the video, source, limits and mock PR.
The dashboard can record natural-language feedback, reject a candidate, or
**simulate** approval. Simulated approval builds a local gallery under
`output/mock-gallery/science/`. It never changes public approval status,
contacts GitHub, or publishes to X. The public gallery build uses only
manifests with `approved: true` and a public project URL:

```powershell
python scripts/build_gallery.py --base-path /science-visualizations/science/
```

Static output is in `dist/science/`. The base path is configurable for a site
mounted at `/science/`; routing `mattmullin.space/science` requires a domain or
reverse-proxy setup. The GitHub Pages workflow uses the repository path by
default. No custom domain is connected yet.

## GitHub flow

The production adapter in `scripts/github_api.py` creates a candidate branch,
uploads the project package with GitHub's authenticated REST Git API, and opens
a **draft** PR. It requires `GITHUB_REPOSITORY` and a short-lived `GITHUB_TOKEN`
with repository contents and pull-request write permission. Do not put tokens
in files or the public dashboard. The adapter never merges. GitHub Actions
validate source and science on PRs, build a downloadable gallery preview, and
deploy the approved gallery on `main`. Production automation should use a
GitHub App token, because PRs created by the standard Actions `GITHUB_TOKEN`
do not trigger downstream PR workflows.

Large MP4s and scientific source datasets are excluded from Git history.
Release media needs external storage and URL assignment before publication.
The small frozen model snapshot is committed to make the renderer reproducible.

## Release rule

Scientific and editorial review, a human PR approval, a working media URL,
and a valid public source URL are required before marking a manifest approved
and merging. No workflow posts to X. The seven-project buffer and three
candidate daily budget are targets in `backlog.json`; they are not active
production automation yet.

`python scripts/generate_calendar.py` creates a tentative 180-day calendar
starting 1 December 2026. It includes fields for PRs, reviews, media, X
performance and GitHub metrics; collection and publishing remain manual until
authenticated integrations are configured.

## Current status

The Saharan dust source snapshot, renderer, 20-second MP4, thumbnail,
documentation and local review flow have been built. Public repository
creation, authenticated PR submission, external worker queue, hosted domain,
and X analytics still require service setup and human publication approval.

