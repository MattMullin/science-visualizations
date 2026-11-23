import json
import shutil

import scripts.build_gallery as gallery

build = gallery.build


def test_unapproved_candidate_is_excluded(tmp_path):
    build(tmp_path / "public", "/science/")
    assert json.loads((tmp_path / "public/catalog.json").read_text()) == []


def test_approved_unpublished_demo_is_deployed_but_unlisted(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    shutil.copytree(gallery.ROOT / "gallery", root / "gallery")
    shutil.copytree(gallery.ROOT / "projects", root / "projects")
    shutil.copytree(gallery.ROOT / "shared", root / "shared")
    manifest = root / "projects/001-saharan-dust/manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["approved"] = True
    data["assets"]["source_url"] = "https://github.com/example/science-visualizations/tree/main/projects/001-saharan-dust"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(gallery, "ROOT", root)
    build(root / "dist/science", "/science/")
    assert json.loads((root / "dist/science/catalog.json").read_text()) == []
    assert (root / "dist/science/assets/001-saharan-dust/demo/index.html").is_file()


def test_mock_approval_only_affects_local_demo(tmp_path):
    state = tmp_path / "mock.json"
    state.write_text(json.dumps({"pull_requests": [{"project_id": "001-saharan-dust", "status": "approved_mock"}]}))
    build(tmp_path / "demo", "/mock-gallery/science/", state)
    catalog = json.loads((tmp_path / "demo/catalog.json").read_text())
    assert len(catalog) == 1
    assert catalog[0]["date"] == "LOCAL DEMO"
    assert catalog[0]["demo"] == "assets/001-saharan-dust/demo/"
    assert (tmp_path / "demo/assets/001-saharan-dust/demo/dust_snapshot.json").is_file()
    build(tmp_path / "public", "/science/")
    assert json.loads((tmp_path / "public/catalog.json").read_text()) == []
