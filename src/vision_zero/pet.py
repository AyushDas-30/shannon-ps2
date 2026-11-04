"""Post-encroachment time for explicitly defined planar conflict zones."""

from collections import defaultdict

from .indicators import classify_conflict, severity_band
from .schema import RiskEvent, TrackPoint


def detect_pet_events(
    points: list[TrackPoint],
    zones: dict[str, list[tuple[float, float]]],
    *,
    max_pet_s: float = 3.0,
) -> list[RiskEvent]:
    """Compute PET only for valid polygons and tracks that both traverse a zone.

    The zone polygon is supplied in the same metric coordinate system as tracks.
    Tracks ending inside a zone are treated as censored and produce no PET.
    """
    if max_pet_s <= 0:
        raise ValueError("max_pet_s must be positive")
    valid_zones = {name: polygon for name, polygon in zones.items() if _valid_polygon(polygon)}
    by_source: dict[str, list[TrackPoint]] = defaultdict(list)
    for point in points:
        by_source[point.source_id].append(point)

    events: list[RiskEvent] = []
    for source_id, source_points in by_source.items():
        tracks: dict[str, list[TrackPoint]] = defaultdict(list)
        for point in source_points:
            tracks[point.track_id].append(point)
        traversals: dict[str, list[tuple[float, float, TrackPoint]]] = defaultdict(list)
        for track in tracks.values():
            track.sort(key=lambda p: p.timestamp_s)
            for zone_id, polygon in valid_zones.items():
                inside = [p for p in track if _inside((p.x_m, p.y_m), polygon)]
                if (not inside or _inside((track[0].x_m, track[0].y_m), polygon)
                        or _inside((track[-1].x_m, track[-1].y_m), polygon)):
                    continue
                # Sampling limits precision; mark it explicitly in the event.
                traversals[zone_id].append((inside[0].timestamp_s, inside[-1].timestamp_s, inside[0]))
        for zone_id, crossings in traversals.items():
            crossings.sort(key=lambda c: c[0])
            for i, (entry_a, exit_a, point_a) in enumerate(crossings):
                for entry_b, exit_b, point_b in crossings[i + 1:]:
                    if point_a.track_id == point_b.track_id:
                        continue
                    if entry_b >= exit_a:
                        pet_s, first, second, event_time = entry_b - exit_a, point_a, point_b, exit_a
                    elif entry_a >= exit_b:
                        pet_s, first, second, event_time = entry_a - exit_b, point_b, point_a, exit_b
                    else:
                        # Occupancy overlapped; PET is unresolved rather than zero.
                        continue
                    if pet_s > max_pet_s:
                        continue
                    if first.track_id > second.track_id:
                        first, second = second, first
                    x_m = (point_a.x_m + point_b.x_m) / 2
                    y_m = (point_a.y_m + point_b.y_m) / 2
                    events.append(RiskEvent(
                        event_id=f"{source_id}:{point_a.source_type}:{zone_id}:{first.track_id}:{second.track_id}",
                        source_id=source_id, timestamp_s=event_time,
                        road_user_a=first.track_id, class_a=first.road_user_class,
                        road_user_b=second.track_id, class_b=second.road_user_class,
                        indicator_type="PET", indicator_value_s=pet_s,
                        x_m=x_m, y_m=y_m, min_separation_m=float("nan"),
                        quality_flags=("sampled_zone_entry_exit_estimate",),
                        source_type=point_a.source_type,
                        conflict_type=classify_conflict(point_a.class_group, point_b.class_group),
                        severity_band=severity_band(pet_s), segment_id=zone_id,
                    ))
    return sorted(events, key=lambda event: event.timestamp_s)


def _valid_polygon(polygon: list[tuple[float, float]]) -> bool:
    return len(polygon) >= 3 and len(set(polygon)) >= 3


def _inside(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    previous = polygon[-1]
    for current in polygon:
        x1, y1 = current
        x2, y2 = previous
        if (y1 > y) != (y2 > y):
            crossing_x = (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1
            if x < crossing_x:
                inside = not inside
        previous = current
    return inside
