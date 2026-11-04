"""Seeded SUMO route generation for user-supplied intersection edge paths."""

import random
import xml.etree.ElementTree as ET
from pathlib import Path


def generate_seeded_routes(
    output_path: str | Path,
    *,
    vehicle_paths: dict[str, list[str]],
    pedestrian_paths: dict[str, list[str]],
    seed: int = 42,
    demand: int = 18,
    duration_s: float = 90.0,
    conflict_mode: str = "crossing",
) -> Path:
    """Generate repeatable vehicle/pedestrian routes from valid SUMO edge paths.

    Supply paths for a local OSM-derived SUMO network. The paths should cover a
    crossing, a turn/through movement, and a two-wheeler interaction when those
    edges exist. SUMO validates route connectivity at execution time.
    """
    if not vehicle_paths or not pedestrian_paths:
        raise ValueError("Provide at least one vehicle path and one pedestrian path")
    if demand < 1 or duration_s <= 0:
        raise ValueError("demand and duration must be positive")
    rng = random.Random(seed)
    root = ET.Element("routes")
    ET.SubElement(root, "vType", {
        "id": "car", "vClass": "passenger", "length": "4.5", "width": "1.8",
        "maxSpeed": "13.9", "accel": "2.6", "decel": "4.5",
    })
    ET.SubElement(root, "vType", {
        "id": "bike", "vClass": "bicycle", "length": "1.8", "width": "0.6",
        "maxSpeed": "7.0", "accel": "1.5", "decel": "3.0",
    })
    for path_id, edges in {**vehicle_paths, **pedestrian_paths}.items():
        ET.SubElement(root, "route", {"id": path_id, "edges": " ".join(edges)})
    all_vehicles = list(vehicle_paths)
    vehicle_count = demand
    for index in range(vehicle_count):
        route_id = rng.choice(all_vehicles)
        if conflict_mode == "control":
            depart = rng.uniform(0, duration_s * 0.2)
        else:
            depart = max(0.0, rng.gauss(duration_s * 0.45, duration_s * 0.18))
        if conflict_mode in {"crossing", "turning", "bike_cut_across"} and index == 0:
            depart = duration_s * 0.47
        vehicle_type = "bike" if conflict_mode == "bike_cut_across" and index % 4 == 0 else "car"
        ET.SubElement(root, "vehicle", {
            "id": f"veh_{index:03d}", "type": vehicle_type, "route": route_id,
            "depart": f"{min(depart, duration_s - 1):.2f}", "departLane": "best",
            "departSpeed": "max",
        })
    ped_paths = list(pedestrian_paths)
    ped_count = max(3, demand // 4)
    for index in range(ped_count):
        if conflict_mode == "control":
            depart = rng.uniform(duration_s * 0.75, duration_s * 0.85)
        else:
            depart = duration_s * 0.47 if index == 0 else rng.uniform(0, duration_s * 0.8)
        person = ET.SubElement(root, "person", {
            "id": f"ped_{index:03d}", "depart": f"{depart:.2f}", "type": "DEFAULT_PEDTYPE"
        })
        ET.SubElement(person, "walk", {"route": rng.choice(ped_paths), "duration": "20"})
    ET.indent(root)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return path
