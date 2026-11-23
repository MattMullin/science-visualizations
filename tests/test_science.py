import json
from pathlib import Path

from scripts.validate import ROOT, validate


def test_committed_snapshot_passes_scientific_gates():
    assert validate(ROOT / "projects/001-saharan-dust") == []


def test_snapshot_is_a_dated_model_grid():
    path = ROOT / "projects/001-saharan-dust/data/dust_snapshot.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["source"].startswith("CAMS European")
    assert data["units"] == "micrograms per cubic meter"
    assert len(data["times_utc"]) == 72
    assert len({(p["lat"], p["lon"]) for p in data["points"]}) == 48
    assert any((v or 0) > 0 for p in data["points"] for v in p["dust"])
