"""Regression tests for the schema fix and per-encounter event collapsing."""

import csv
import subprocess
import sys
from pathlib import Path

from vision_zero.hotspots import aggregate_hotspots
from vision_zero.indicators import detect_ttc_events
from vision_zero.ingest import load_tracks
from vision_zero.pipeline import analyze_run

ROOT = Path(__file__).resolve().parents[1]


def _sample(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "examples" / "generate_sample.py")], check=True)
    return ROOT / "examples" / "sample_tracks.csv"


def test_one_event_per_encounter(tmp_path):
    points = load_tracks(_sample(tmp_path))
    raw = detect_ttc_events(points, collapse=False)
    merged = detect_ttc_events(points)
    pairs = {frozenset((e.road_user_a, e.road_user_b)) for e in merged}
    assert len(merged) == len(pairs) < len(raw)
    for pair in pairs:
        lowest = min(e.indicator_value_s for e in raw
                     if frozenset((e.road_user_a, e.road_user_b)) == pair)
        kept = [e for e in merged if frozenset((e.road_user_a, e.road_user_b)) == pair]
        assert kept[0].indicator_value_s == lowest


def test_separate_encounters_stay_separate():
    from vision_zero.schema import TrackPoint
    pts = []
    for t10 in range(0, 200, 2):  # head-on pass at t~5s and again at t~15s
        t = t10 / 10
        for tid, sign in (("a", 1), ("b", -1)):
            x = sign * abs(((t % 10) - 5)) * 3
            pts.append(TrackPoint("s", t, tid, "car", x, 0.0, radius_m=1.0, class_group="vehicle"))
    events = detect_ttc_events(pts, max_ttc_s=3.0)
    assert len(events) == 2


def test_analyze_run_writes_bundle(tmp_path):
    points = load_tracks(_sample(tmp_path))
    run = analyze_run(points, tmp_path, run_id="t", source_type="sumo_gt")
    for name in ("events.csv", "hotspots.parquet", "hotspots.geojson", "engineer_summary.md", "validation.json"):
        assert (run / name).exists()
    hotspots = aggregate_hotspots(detect_ttc_events(points), points)
    assert hotspots and hotspots[0].dominant_road_user_pair != "unknown pair"
