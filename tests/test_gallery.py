import json
import shutil

import scripts.build_gallery as gallery


def copied_repo(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(gallery.ROOT / "gallery", root / "gallery")
    shutil.copytree(gallery.ROOT / "projects", root / "projects")
    shutil.copytree(gallery.ROOT / "shared", root / "shared")
    return root


def test_published_project_is_in_public_catalog(tmp_path):
    gallery.build(tmp_path / "public", "/science/")
    catalog = json.loads((tmp_path / "public/catalog.json").read_text())
    assert len(catalog) == 1
    assert catalog[0]["id"] == "001-saharan-dust"
    assert catalog[0]["date"] == "2026-11-23"
    assert catalog[0]["video"].endswith("/day-001-saharan-dust/saharan-dust.mp4")
    assert (tmp_path / "public/assets/001-saharan-dust/demo/index.html").is_file()


def test_unapproved_candidate_is_excluded(tmp_path, monkeypatch):
    root = copied_repo(tmp_path)
    manifest = root / "projects/001-saharan-dust/manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["approved"] = False
    data["published_at"] = None
    data["assets"]["source_url"] = None
    manifest.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(gallery, "ROOT", root)
    gallery.build(root / "dist/science", "/science/")
    assert json.loads((root / "dist/science/catalog.json").read_text()) == []


def test_approved_unpublished_demo_is_deployed_but_unlisted(tmp_path, monkeypatch):
    root = copied_repo(tmp_path)
    manifest = root / "projects/001-saharan-dust/manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["published_at"] = None
    data["status"] = "approved"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(gallery, "ROOT", root)
    gallery.build(root / "dist/science", "/science/")
    assert json.loads((root / "dist/science/catalog.json").read_text()) == []
    assert (root / "dist/science/assets/001-saharan-dust/demo/index.html").is_file()
