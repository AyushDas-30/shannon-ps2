"""Create deterministic crossing and control tracks for a local demo."""

import csv
from pathlib import Path


def main():
    output = Path(__file__).resolve().parent / "sample_tracks.csv"
    fields = ["source_id", "source_type", "timestamp_s", "track_id", "class", "class_group",
              "x_m", "y_m", "coordinate_system", "radius_m", "confidence"]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for i in range(101):
            t = i * 0.2
            # Two motor vehicles approach a shared conflict area from different directions.
            writer.writerow(_row(t, "veh_1", "car", "vehicle", -20 + 4 * t, 0, 2.2))
            writer.writerow(_row(t, "veh_2", "car", "vehicle", 0, -16 + 3.2 * t, 2.2))
            # A pedestrian crosses near the same area in the seeded-conflict scenario.
            writer.writerow(_row(t, "ped_1", "person", "pedestrian", 0, -10 + 2 * t, 0.35))
            # Separate control movement provides non-conflict exposure.
            writer.writerow(_row(t, "veh_control", "car", "vehicle", 40 + 2 * t, 35, 2.2))
    expected = output.with_name("expected_events.csv")
    with expected.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_id", "road_user_1", "road_user_2", "indicator_type", "expected_time_s"])
        writer.writeheader()
        writer.writerow({"source_id": "seeded_intersection_demo", "road_user_1": "ped_1",
                         "road_user_2": "veh_1", "indicator_type": "TTC", "expected_time_s": "4.5"})
        # veh_2 closes on ped_1 at 1.2 m/s from 6 m; footprints (2.55 m) touch at ~2.9 s.
        writer.writerow({"source_id": "seeded_intersection_demo", "road_user_1": "ped_1",
                         "road_user_2": "veh_2", "indicator_type": "TTC", "expected_time_s": "2.9"})
    print(f"Wrote deterministic sample track CSV: {output}")


def _row(t, track_id, label, group, x, y, radius):
    return {
        "source_id": "seeded_intersection_demo", "source_type": "sumo_gt",
        "timestamp_s": f"{t:.2f}", "track_id": track_id, "class": label,
        "class_group": group, "x_m": f"{x:.3f}", "y_m": f"{y:.3f}",
        "coordinate_system": "local_m", "radius_m": radius, "confidence": 1.0,
    }


if __name__ == "__main__":
    main()
