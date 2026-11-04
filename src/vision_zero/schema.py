"""Shared input and event records."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackPoint:
    source_id: str
    timestamp_s: float
    track_id: str
    road_user_class: str
    x_m: float
    y_m: float
    confidence: float | None = None
    radius_m: float = 1.0
    quality_flags: tuple[str, ...] = ()
    source_type: str = "sumo_gt"
    class_group: str = "other road user"
    coordinate_system: str = "local_m"
    lat: float | None = None
    lon: float | None = None
    min_ttc_s: float | None = None
    min_pet_s: float | None = None
    dominant_road_user_pair: str = "unknown pair"


@dataclass(frozen=True)
class RiskEvent:
    event_id: str
    source_id: str
    timestamp_s: float
    road_user_a: str
    class_a: str
    road_user_b: str
    class_b: str
    indicator_type: str
    indicator_value_s: float
    x_m: float
    y_m: float
    min_separation_m: float
    quality_flags: tuple[str, ...] = ()
    source_type: str = "sumo_gt"
    conflict_type: str = "other"
    secondary_indicator_value: float | None = None
    severity_band: str = "unrated"
    segment_id: str | None = None
    lat: float | None = None
    lon: float | None = None
    evidence_ref: str | None = None
    ssm_reference_value: float | None = None


@dataclass(frozen=True)
class Hotspot:
    cell_x: int
    cell_y: int
    event_count: int
    minimum_indicator_s: float
    event_types: tuple[str, ...]
    observed_road_users: int = 0
    observation_minutes: float = 0.0
    rate_per_1000: float | None = None
    rate_ci_low: float | None = None
    rate_ci_high: float | None = None
    dominant_conflict_type: str = "other"
    coverage_flags: tuple[str, ...] = ()
    lat: float | None = None
    lon: float | None = None
