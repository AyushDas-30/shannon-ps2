"""CSV ingestion and trajectory velocity estimation."""

import csv
import math
from dataclasses import replace
from collections import defaultdict
from pathlib import Path

from .schema import TrackPoint


REQUIRED_COLUMNS = {"source_id", "timestamp_s", "track_id", "class", "x_m", "y_m"}


def class_group(road_user_class: str) -> str:
    name = road_user_class.lower().replace("_", " ")
    if name in {"person", "pedestrian", "human"}:
        return "pedestrian"
    if name in {"bicycle", "bike", "motorcycle", "motorbike", "scooter", "auto rickshaw"}:
        return "two-wheeler"
    if name in {"car", "bus", "truck", "van", "vehicle"}:
        return "vehicle"
    return "other road user"


def load_tracks(path: str | Path) -> list[TrackPoint]:
    points: list[TrackPoint] = []
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"Missing required CSV columns: {', '.join(sorted(missing))}")

        for row_number, row in enumerate(reader, start=2):
            try:
                timestamp = float(row["timestamp_s"])
                x_m = float(row["x_m"])
                y_m = float(row["y_m"])
                radius = float(row.get("radius_m") or 1.0)
                confidence = float(row["confidence"]) if row.get("confidence") else None
                if not all(math.isfinite(v) for v in (timestamp, x_m, y_m, radius)):
                    raise ValueError("timestamp, position, and radius must be finite")
                if timestamp < 0 or radius <= 0:
                    raise ValueError("timestamp must be nonnegative and radius must be positive")
                if confidence is not None and not 0 <= confidence <= 1:
                    raise ValueError("confidence must be between 0 and 1")
                track_id = (row.get("track_id") or "").strip()
                road_user_class = (row.get("class") or "").strip().lower()
                source_id = (row.get("source_id") or "").strip()
                if not track_id or not road_user_class or not source_id:
                    raise ValueError("source_id, track_id, and class cannot be empty")
                flags = tuple(
                    flag.strip() for flag in (row.get("quality_flags") or "").split(";")
                    if flag.strip()
                )
                source_type = (row.get("source_type") or "sumo_gt").strip().lower()
                coordinate_system = (row.get("coordinate_system") or "local_m").strip()
                if source_type not in {"sumo_gt", "sumo_detected", "video"}:
                    raise ValueError("source_type must be sumo_gt, sumo_detected, or video")
                points.append(TrackPoint(
                    source_id=source_id, timestamp_s=timestamp, track_id=track_id,
                    road_user_class=road_user_class, x_m=x_m, y_m=y_m,
                    confidence=confidence, radius_m=radius, quality_flags=flags,
                    source_type=source_type,
                    class_group=(row.get("class_group") or class_group(road_user_class)).strip().lower(),
                    coordinate_system=coordinate_system,
                ))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid row {row_number}: {exc}") from exc

    points.sort(key=lambda p: (p.source_id, p.source_type, p.track_id, p.timestamp_s))
    grouped = defaultdict(list)
    for point in points:
        grouped[(point.source_id, point.source_type, point.track_id)].append(point)
    flagged = []
    for track in grouped.values():
        previous = None
        for point in track:
            flags = set(point.quality_flags)
            if previous and point.timestamp_s == previous.timestamp_s:
                flags.add("duplicate_timestamp")
            if previous and point.timestamp_s - previous.timestamp_s > 1.0:
                flags.add("large_time_gap")
            flagged.append(replace(point, quality_flags=tuple(sorted(flags))))
            previous = point
    return sorted(flagged, key=lambda p: (p.source_id, p.source_type, p.track_id, p.timestamp_s))


def estimate_velocities(points: list[TrackPoint]) -> dict[tuple[str, str, float], tuple[float, float]]:
    """Estimate per-track velocity using neighboring observations in metres/second."""
    grouped: dict[tuple[str, str], list[TrackPoint]] = defaultdict(list)
    for point in points:
        grouped[(point.source_id, point.track_id)].append(point)

    velocities: dict[tuple[str, str, float], tuple[float, float]] = {}
    for key, track in grouped.items():
        track.sort(key=lambda p: p.timestamp_s)
        for i, point in enumerate(track):
            left = track[max(0, i - 1)]
            right = track[min(len(track) - 1, i + 1)]
            dt = right.timestamp_s - left.timestamp_s
            if dt <= 0:
                continue
            velocities[(key[0], key[1], point.timestamp_s)] = (
                (right.x_m - left.x_m) / dt,
                (right.y_m - left.y_m) / dt,
            )
    return velocities
