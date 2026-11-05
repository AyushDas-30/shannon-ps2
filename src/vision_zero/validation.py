"""Scenario/event validation and threshold sensitivity summaries."""

import csv
from pathlib import Path

from .indicators import detect_ttc_events
from .schema import RiskEvent, TrackPoint


def event_match_counts(reference: list[RiskEvent], candidate: list[RiskEvent], *, tolerance_s: float = 1.0) -> dict:
    """Greedy one-to-one match by source, neutral pair, type, and event time."""
    unmatched = set(range(len(candidate)))
    matched = 0
    errors = []
    for expected in reference:
        options = []
        for index in unmatched:
            observed = candidate[index]
            same_pair = {expected.road_user_a, expected.road_user_b} == {
                observed.road_user_a, observed.road_user_b
            }
            if (expected.source_id == observed.source_id and same_pair
                    and expected.indicator_type == observed.indicator_type
                    and abs(expected.timestamp_s - observed.timestamp_s) <= tolerance_s):
                options.append((abs(expected.timestamp_s - observed.timestamp_s), index))
        if options:
            _, index = min(options)
            unmatched.remove(index)
            matched += 1
            errors.append(abs(expected.indicator_value_s - candidate[index].indicator_value_s))
    return {
        "reference_events": len(reference),
        "candidate_events": len(candidate),
        "matched_events": matched,
        "event_recall": matched / len(reference) if reference else None,
        "spurious_events": len(unmatched),
        "spurious_rate": len(unmatched) / len(candidate) if candidate else 0.0,
        "indicator_mae_s": sum(errors) / len(errors) if errors else None,
        "match_tolerance_s": tolerance_s,
    }


def compare_sources(points: list[TrackPoint], *, max_ttc_s: float = 3.0) -> dict:
    groups: dict[str, list[TrackPoint]] = {}
    for point in points:
        groups.setdefault(point.source_type, []).append(point)
    metric = lambda entries: [p for p in entries if p.coordinate_system != "pixel"]
    reference = detect_ttc_events(metric(groups.get("sumo_gt", [])), max_ttc_s=max_ttc_s)
    result = {"ground_truth_event_count": len(reference), "comparisons": {}}
    for source_type in ("sumo_detected", "video"):
        if not groups.get(source_type):
            continue  # no tracks from this source in the run: nothing to compare
        observed = detect_ttc_events(metric(groups.get(source_type, [])), max_ttc_s=max_ttc_s)
        result["comparisons"][source_type] = event_match_counts(reference, observed)
    return result


def threshold_sensitivity(points: list[TrackPoint], *, base_ttc_s: float = 3.0) -> dict:
    output = {}
    for factor in (0.7, 0.8, 1.0, 1.2, 1.3):
        threshold = base_ttc_s * factor
        events = detect_ttc_events(points, max_ttc_s=threshold)
        counts = {}
        for event in events:
            cell = f"{int(event.x_m // 25)},{int(event.y_m // 25)}"
            counts[cell] = counts.get(cell, 0) + 1
        ranking = [key for key, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]
        output[f"{factor:.1f}x"] = {
            "threshold_s": threshold,
            "event_count": len(events),
            "hotspot_ranking": ranking,
            "hotspot_counts": counts,
        }
    return output


def compare_with_ssm(events: list[RiskEvent], ssm_rows: list[dict]) -> dict:
    """Compare candidate events with SUMO encounter values when IDs are present."""
    pairs = {}
    for row in ssm_rows:
        ego, foe = row.get("ego"), row.get("foe")
        if not ego or not foe:
            continue
        key = frozenset((str(ego), str(foe)))
        current = pairs.setdefault(key, {})
        for measure in ("ttc", "pet", "drac"):
            values = row.get(measure, [])
            if values:
                current[measure] = min(values) if measure in {"ttc", "pet"} else max(values)
    errors = {"TTC": [], "PET": []}
    matched = {"TTC": 0, "PET": 0}
    for event in events:
        measure = event.indicator_type.lower()
        reference = pairs.get(frozenset((event.road_user_a, event.road_user_b)), {}).get(measure)
        if reference is not None and measure.upper() in errors:
            errors[measure.upper()].append(abs(event.indicator_value_s - reference))
            matched[measure.upper()] += 1
    return {
        "ssm_encounters": len(ssm_rows),
        "matched_events": matched,
        "mean_absolute_error_s": {
            key: sum(values) / len(values) if values else None for key, values in errors.items()
        },
    }


def validate_seeded_events(events: list[RiskEvent], expected_csv: str | Path,
                           *, tolerance_s: float = 1.0) -> dict:
    with Path(expected_csv).open(newline="", encoding="utf-8-sig") as handle:
        expected = list(csv.DictReader(handle))
    unmatched = set(range(len(events)))
    matched = 0
    for row in expected:
        pair = {row["road_user_1"], row["road_user_2"]}
        expected_time = float(row["expected_time_s"])
        choices = []
        for index in unmatched:
            event = events[index]
            if (event.source_id == row["source_id"]
                    and {event.road_user_a, event.road_user_b} == pair
                    and event.indicator_type == row.get("indicator_type", "TTC")
                    and abs(event.timestamp_s - expected_time) <= tolerance_s):
                choices.append((abs(event.timestamp_s - expected_time), index))
        if choices:
            _, selected = min(choices)
            unmatched.remove(selected)
            matched += 1
    return {
        "seeded_expected_events": len(expected),
        "matched_events": matched,
        "event_recall": matched / len(expected) if expected else None,
        "unmatched_expected_events": len(expected) - matched,
        "extra_candidate_events": len(unmatched),
        "time_tolerance_s": tolerance_s,
    }
