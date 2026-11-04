"""Transparent screening indicators derived from road-user tracks."""

import math
from collections import defaultdict

from .schema import RiskEvent, TrackPoint


def detect_ttc_events(
    points: list[TrackPoint],
    *,
    horizon_s: float = 5.0,
    max_ttc_s: float = 3.0,
    minimum_sample_s: float = 0.05,
) -> list[RiskEvent]:
    """Find pairs predicted to overlap within the horizon under constant velocity.

    Tracks are compared only at timestamps observed for both users. A pair with
    missing or very widely spaced observations is skipped rather than extrapolated.
    """
    if horizon_s <= 0 or max_ttc_s <= 0 or minimum_sample_s <= 0:
        raise ValueError("TTC horizons and minimum_sample_s must be positive")
    coordinate_systems = {point.coordinate_system for point in points}
    if any(system == "pixel" for system in coordinate_systems):
        raise ValueError("Metric TTC requires a valid road-plane calibration; pixel tracks are not metres")
    if len(coordinate_systems) > 1:
        raise ValueError("All tracks in one analysis must use the same coordinate system")

    by_time: dict[tuple[str, str, float], list[TrackPoint]] = defaultdict(list)
    for point in points:
        by_time[(point.source_id, point.source_type, point.timestamp_s)].append(point)

    velocities = _velocities(points)
    events: list[RiskEvent] = []
    seen: set[tuple[str, str, float, str, str]] = set()
    for (source_id, source_type, timestamp), snapshot in by_time.items():
        for index, a in enumerate(snapshot):
            for b in snapshot[index + 1:]:
                if a.track_id == b.track_id:
                    continue
                va = velocities.get((source_id, source_type, a.track_id, timestamp))
                vb = velocities.get((source_id, source_type, b.track_id, timestamp))
                if va is None or vb is None:
                    continue
                pair = tuple(sorted((a.track_id, b.track_id)))
                key = (source_id, source_type, timestamp, pair[0], pair[1])
                if key in seen:
                    continue
                seen.add(key)
                result = _first_overlap(a, b, va, vb, horizon_s)
                if result is None:
                    continue
                ttc_s, separation, x_m, y_m = result
                if ttc_s > max_ttc_s:
                    continue
                if a.track_id <= b.track_id:
                    first, second = a, b
                else:
                    first, second = b, a
                flags = set(a.quality_flags) | set(b.quality_flags)
                flags.add("constant_velocity_screening_estimate")
                if ttc_s == 0:
                    flags.add("overlap_at_observation_unresolved")
                if 0 < ttc_s < minimum_sample_s:
                    flags.add("below_sampling_resolution")
                if a.confidence is not None and a.confidence < 0.4:
                    flags.add("low_detection_confidence")
                if b.confidence is not None and b.confidence < 0.4:
                    flags.add("low_detection_confidence")
                conflict_type = classify_motion_conflict(a.class_group, b.class_group, va, vb)
                closing_speed = -((a.x_m - b.x_m) * (va[0] - vb[0]) + (a.y_m - b.y_m) * (va[1] - vb[1])) / max(
                    ((a.x_m - b.x_m) ** 2 + (a.y_m - b.y_m) ** 2) ** 0.5, 1e-9
                )
                drac = (closing_speed ** 2) / (2 * max(separation, 0.1)) if closing_speed > 0 else None
                events.append(RiskEvent(
                    event_id=f"{source_id}:{source_type}:{timestamp:.3f}:{pair[0]}:{pair[1]}",
                    source_id=source_id, timestamp_s=timestamp,
                    road_user_a=first.track_id, class_a=first.road_user_class,
                    road_user_b=second.track_id, class_b=second.road_user_class,
                    indicator_type="TTC", indicator_value_s=ttc_s,
                    x_m=x_m, y_m=y_m, min_separation_m=separation,
                    quality_flags=tuple(sorted(flags)),
                    source_type=a.source_type,
                    conflict_type=conflict_type,
                    secondary_indicator_value=drac,
                    severity_band=("unresolved" if ttc_s < minimum_sample_s else severity_band(ttc_s)),
                    lat=((a.lat + b.lat) / 2 if a.lat is not None and b.lat is not None else None),
                    lon=((a.lon + b.lon) / 2 if a.lon is not None and b.lon is not None else None),
                ))
    return sorted(events, key=lambda event: event.timestamp_s)


def classify_conflict(group_a: str, group_b: str) -> str:
    groups = {group_a, group_b}
    if "pedestrian" in groups and "vehicle" in groups:
        return "vehicle_pedestrian_crossing"
    if "two-wheeler" in groups:
        return "bicycle_two_wheeler_interaction"
    if group_a == group_b == "vehicle":
        return "same_or_crossing_vehicle_approach"
    return "other"


def classify_motion_conflict(group_a: str, group_b: str, va, vb) -> str:
    base = classify_conflict(group_a, group_b)
    if base != "same_or_crossing_vehicle_approach":
        return base
    speed_a = (va[0] ** 2 + va[1] ** 2) ** 0.5
    speed_b = (vb[0] ** 2 + vb[1] ** 2) ** 0.5
    if speed_a < 0.1 or speed_b < 0.1:
        return "other_vehicle_interaction"
    cosine = max(-1.0, min(1.0, (va[0] * vb[0] + va[1] * vb[1]) / (speed_a * speed_b)))
    angle_deg = math.degrees(math.acos(cosine))
    if angle_deg < 30:
        return "same_direction_closing"
    return "turning_or_crossing_vehicle_interaction"


def severity_band(ttc_s: float, *, critical_s: float = 1.0, elevated_s: float = 2.0) -> str:
    if ttc_s <= critical_s:
        return "critical"
    if ttc_s <= elevated_s:
        return "elevated"
    return "watch"


def _velocities(points: list[TrackPoint], *, max_gap_s: float = 1.0) -> dict[tuple[str, str, str, float], tuple[float, float]]:
    grouped: dict[tuple[str, str, str], list[TrackPoint]] = defaultdict(list)
    for point in points:
        grouped[(point.source_id, point.source_type, point.track_id)].append(point)
    result = {}
    for (source_id, source_type, track_id), track in grouped.items():
        track.sort(key=lambda p: p.timestamp_s)
        for i, point in enumerate(track):
            left, right = track[max(0, i - 1)], track[min(len(track) - 1, i + 1)]
            dt = right.timestamp_s - left.timestamp_s
            if 0.05 <= dt <= max_gap_s:
                result[(source_id, source_type, track_id, point.timestamp_s)] = (
                    (right.x_m - left.x_m) / dt,
                    (right.y_m - left.y_m) / dt,
                )
    return result


def _first_overlap(a, b, va, vb, horizon_s: float):
    rx, ry = a.x_m - b.x_m, a.y_m - b.y_m
    vx, vy = va[0] - vb[0], va[1] - vb[1]
    radius = a.radius_m + b.radius_m
    c = rx * rx + ry * ry - radius * radius
    if c <= 0:
        return 0.0, math.hypot(rx, ry), (a.x_m + b.x_m) / 2, (a.y_m + b.y_m) / 2
    aa = vx * vx + vy * vy
    if aa <= 1e-12:
        return None
    bb = 2 * (rx * vx + ry * vy)
    if bb >= 0:
        return None
    discriminant = bb * bb - 4 * aa * c
    if discriminant < 0:
        return None
    ttc_s = (-bb - math.sqrt(discriminant)) / (2 * aa)
    if ttc_s < 0 or ttc_s > horizon_s:
        return None
    ax, ay = a.x_m + va[0] * ttc_s, a.y_m + va[1] * ttc_s
    bx, by = b.x_m + vb[0] * ttc_s, b.y_m + vb[1] * ttc_s
    return ttc_s, math.hypot(ax - bx, ay - by), (ax + bx) / 2, (ay + by) / 2
