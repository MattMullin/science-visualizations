import json

from scripts.build_gallery import build


def test_unapproved_candidate_is_excluded(tmp_path):
    build(tmp_path / "public", "/science/")
    assert json.loads((tmp_path / "public/catalog.json").read_text()) == []


def test_mock_approval_only_affects_local_demo(tmp_path):
    state = tmp_path / "mock.json"
    state.write_text(json.dumps({"pull_requests": [{"project_id": "001-saharan-dust", "status": "approved_mock"}]}))
    build(tmp_path / "demo", "/mock-gallery/science/", state)
    catalog = json.loads((tmp_path / "demo/catalog.json").read_text())
    assert len(catalog) == 1
    assert catalog[0]["date"] == "LOCAL DEMO"
    build(tmp_path / "public", "/science/")
    assert json.loads((tmp_path / "public/catalog.json").read_text()) == []
