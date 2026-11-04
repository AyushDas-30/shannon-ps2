"""Metric-grid aggregation for candidate conflict locations."""

from collections import defaultdict

from .schema import Hotspot, RiskEvent, TrackPoint


def aggregate_hotspots(events: list[RiskEvent], points: list[TrackPoint] | None = None,
                       *, cell_size_m: float = 25.0, minimum_exposure: int = 10) -> list[Hotspot]:
    if cell_size_m <= 0:
        raise ValueError("cell_size_m must be positive")
    cells: dict[tuple[int, int], list[RiskEvent]] = defaultdict(list)
    for event in events:
        cells[(int(event.x_m // cell_size_m), int(event.y_m // cell_size_m))].append(event)

    tracks_by_cell: dict[tuple[int, int], set[tuple[str, str]]] = defaultdict(set)
    times_by_cell: dict[tuple[int, int], list[float]] = defaultdict(list)
    for point in points or []:
        if point.coordinate_system == "pixel":
            continue
        key = (int(point.x_m // cell_size_m), int(point.y_m // cell_size_m))
        tracks_by_cell[key].add((point.source_id, point.track_id))
        times_by_cell[key].append(point.timestamp_s)

    hotspots = []
    for (cell_x, cell_y), group in cells.items():
        hotspots.append(Hotspot(
            cell_x=cell_x,
            cell_y=cell_y,
            event_count=len(group),
            minimum_indicator_s=min(event.indicator_value_s for event in group),
            event_types=tuple(sorted({event.indicator_type for event in group})),
            observed_road_users=len(tracks_by_cell[(cell_x, cell_y)]),
            observation_minutes=(max(times_by_cell[(cell_x, cell_y)]) - min(times_by_cell[(cell_x, cell_y)])
                                 if times_by_cell[(cell_x, cell_y)] else 0.0) / 60,
            rate_per_1000=_rate(len(group), len(tracks_by_cell[(cell_x, cell_y)])),
            rate_ci_low=_rate_ci(len(group), len(tracks_by_cell[(cell_x, cell_y)]))[0],
            rate_ci_high=_rate_ci(len(group), len(tracks_by_cell[(cell_x, cell_y)]))[1],
            dominant_conflict_type=_dominant_conflict(group),
            coverage_flags=(("low_exposure",) if len(tracks_by_cell[(cell_x, cell_y)]) < minimum_exposure else ()),
            lat=(sum(e.lat for e in group if e.lat is not None) /
                 sum(e.lat is not None for e in group) if any(e.lat is not None for e in group) else None),
            lon=(sum(e.lon for e in group if e.lon is not None) /
                 sum(e.lon is not None for e in group) if any(e.lon is not None for e in group) else None),
            min_ttc_s=min((e.indicator_value_s for e in group if e.indicator_type == "TTC"), default=None),
            min_pet_s=min((e.indicator_value_s for e in group if e.indicator_type == "PET"), default=None),
            dominant_road_user_pair=_dominant_pair(group),
        ))
    return sorted(hotspots, key=lambda item: (-item.event_count, item.minimum_indicator_s))


def _rate(events: int, exposure: int) -> float | None:
    return events * 1000 / exposure if exposure else None


def _rate_ci(events: int, exposure: int) -> tuple[float | None, float | None]:
    if exposure == 0:
        return None, None
    # Normal approximation is shown only as a rough screening interval.
    scale = 1000 / exposure
    spread = 1.96 * (events ** 0.5) * scale
    center = events * scale
    return max(0.0, center - spread), center + spread


def _dominant_conflict(group: list[RiskEvent]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for event in group:
        counts[event.conflict_type] += 1
    return max(counts, key=counts.get) if counts else "other"


def _dominant_pair(group: list[RiskEvent]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for event in group:
        counts[f"{event.class_a} / {event.class_b}"] += 1
    return max(counts, key=counts.get) if counts else "unknown pair"
