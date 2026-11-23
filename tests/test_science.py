import json
from pathlib import Path

from scripts.validate import ROOT, validate
from scripts.generate_calendar import generate


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


def test_backlog_has_180_unique_numbered_ideas():
    backlog = json.loads((ROOT / "backlog.json").read_text(encoding="utf-8"))
    projects = backlog["projects"]
    assert len(projects) == 180
    assert [p["number"] for p in projects] == list(range(1, 181))
    assert len({p["slug"] for p in projects}) == 180
    assert [p["slug"] for p in projects[:3]] == ["saharan-dust", "atmospheric-rivers", "ocean-currents"]


def test_calendar_records_first_publication(tmp_path):
    output = tmp_path / "calendar.json"
    generate(output)
    entries = json.loads(output.read_text(encoding="utf-8"))["entries"]
    assert len(entries) == 180
    assert entries[0]["planned_date"] == "2026-11-23"
    assert entries[0]["published_at"] == "2026-11-23"
    assert entries[0]["video_url"].endswith("saharan-dust.mp4")
    assert entries[1]["published_at"] is None
