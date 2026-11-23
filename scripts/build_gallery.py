"""Build the static public atlas from explicitly approved project manifests."""
from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(out: Path, base_path="/science/", mock_state=None):
    if not base_path.startswith("/") or not base_path.endswith("/"):
        raise ValueError("base path must start and end with /")
    out.mkdir(parents=True, exist_ok=True)
    cards = []
    mock_approved = set()
    if mock_state:
        state = json.loads(Path(mock_state).read_text(encoding="utf-8"))
        mock_approved = {p["project_id"] for p in state.get("pull_requests", []) if p["status"] == "approved_mock"}
    for manifest_path in sorted((ROOT / "projects").glob("[0-9][0-9][0-9]-*/manifest.json")):
        project = manifest_path.parent
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        is_mock = project.name in mock_approved
        if not m.get("approved") and not is_mock:
            continue
        if not is_mock and (not m.get("published_at") or not m.get("assets", {}).get("source_url")):
            raise ValueError(f"Incomplete approved manifest: {project.name}")
        thumb = project / m["assets"]["thumbnail"]
        if not thumb.is_file():
            raise ValueError(f"Missing thumbnail: {thumb}")
        destination = out / "assets" / project.name
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(thumb, destination / "thumbnail.png")
        if is_mock:
            shutil.copy2(project / "README.md", destination / "README.md")
        demo_path = m["assets"].get("demo_path")
        if demo_path:
            demo_source = project / demo_path
            if not demo_source.is_file():
                raise ValueError(f"Missing interactive demo: {demo_source}")
            demo_dest = destination / "demo"
            demo_dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(demo_source, demo_dest / "index.html")
            shutil.copy2(project / m["data"]["snapshot"], demo_dest / "dust_snapshot.json")
            shutil.copy2(ROOT / m["provenance"]["basemap"], demo_dest / "ne_110m_land.geojson")
        card = {"id": m["id"], "title": m["title"], "summary": m["summary"],
                "date": m["published_at"] or ("LOCAL DEMO" if is_mock else ""), "dataset": m["data"]["name"],
                "provider": m["data"]["provider"],
                "thumbnail": f"assets/{project.name}/thumbnail.png",
                "video": m["assets"]["video"].get("url"),
                "demo": m["assets"].get("demo_url") or (f"assets/{project.name}/demo/" if demo_path else None),
                "source": m["assets"]["source_url"] or f"assets/{project.name}/README.md",
                "dataset_url": m["data"]["source_url"]}
        card["source_label"] = "Local source package" if is_mock else "GitHub source"
        if is_mock:
            local_video = ROOT / m["assets"]["video"]["local_path"]
            if local_video.is_file():
                shutil.copy2(local_video, destination / "saharan-dust.mp4")
                card["video"] = f"assets/{project.name}/saharan-dust.mp4"
        cards.append(card)
    (out / "catalog.json").write_text(json.dumps(cards, indent=2) + "\n", encoding="utf-8")
    card_html = "".join(card_markup(c) for c in cards)
    if not cards:
        card_html = '<div class="empty"><h2>The atlas is being prepared.</h2><p>Approved projects will appear here after scientific review.</p></div>'
    page = (ROOT / "gallery/template.html").read_text(encoding="utf-8")
    page = page.replace("{{BASE_PATH}}", html.escape(base_path, quote=True))
    page = page.replace("{{COUNT}}", str(len(cards)))
    page = page.replace("{{COUNT_LABEL}}", "local demo projects" if mock_state else "approved projects")
    page = page.replace("{{CARDS}}", card_html)
    (out / "index.html").write_text(page, encoding="utf-8")
    shutil.copy2(ROOT / "gallery/style.css", out / "style.css")
    mode = "mock preview" if mock_state else "approved public catalog"
    print(f"Built {len(cards)} projects in {mode} at {out}")


def card_markup(c):
    esc = lambda x: html.escape(str(x), quote=True)
    video = (f'<a class="button" href="{esc(c["video"])}" target="_blank" rel="noopener">Watch film</a>'
             if c["video"] else '<span class="muted">Film pending release</span>')
    demo = (f'<a class="text-link" href="{esc(c["demo"])}" target="_blank" rel="noopener">Interactive demo</a>'
            if c["demo"] else '')
    return f'''<article class="card">
      <div class="card-image"><img src="{esc(c['thumbnail'])}" alt="Map visualization for {esc(c['title'])}" loading="lazy"></div>
      <div class="card-body"><div class="eyebrow">{esc(c['date'])} <span>·</span> {esc(c['id'])}</div>
      <h2>{esc(c['title'])}</h2><p>{esc(c['summary'])}</p>
      <div class="dataset">DATASET <a href="{esc(c['dataset_url'])}" target="_blank" rel="noopener">{esc(c['dataset'])}</a><small>{esc(c['provider'])}</small></div>
      <div class="links">{video}<a class="text-link" href="{esc(c['source'])}" target="_blank" rel="noopener">{esc(c['source_label'])}</a>{demo}</div></div>
    </article>'''


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "dist/science")
    parser.add_argument("--base-path", default="/science/")
    parser.add_argument("--mock-state", type=Path, help="local demonstration only")
    args = parser.parse_args()
    build(args.out, args.base_path, args.mock_state)

