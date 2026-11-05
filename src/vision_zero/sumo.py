"""SUMO execution, FCD track ingestion, and SSM configuration helpers."""

import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from .ingest import class_group
from .schema import TrackPoint


def require_sumo(binary: str = "sumo") -> str:
    found = shutil.which(binary)
    if not found:
        raise RuntimeError(f"SUMO executable '{binary}' was not found on PATH")
    return found


def build_osm_network(osm_path: str | Path, output_net: str | Path) -> None:
    """Build a SUMO network from a locally supplied OSM XML/PBF extract."""
    netconvert = require_sumo("netconvert")
    subprocess.run([netconvert, "--osm-files", str(osm_path), "-o", str(output_net)], check=True)


def write_sumocfg(network: str | Path, routes: str | Path, output_cfg: str | Path,
                  *, begin_s: float = 0.0, end_s: float = 180.0,
                  step_s: float = 0.2) -> Path:
    cfg = Path(output_cfg)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    root = ET.Element("configuration")
    _section(root, "input", {"net-file": str(Path(network).resolve()), "route-files": str(Path(routes).resolve())})
    _section(root, "time", {"begin": str(begin_s), "end": str(end_s), "step-length": str(step_s)})
    _section(root, "processing", {"time-to-teleport": "-1"})
    ET.indent(root)
    ET.ElementTree(root).write(cfg, encoding="utf-8", xml_declaration=True)
    return cfg


def run_sumo(sumocfg: str | Path, out_dir: str | Path, *, gui: bool = False) -> dict[str, str]:
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    exe = require_sumo("sumo-gui" if gui else "sumo")
    fcd, ssm = out / "fcd.xml", out / "ssm.xml"
    command = [exe, "-c", str(Path(sumocfg).resolve()), "--fcd-output", str(fcd),
               "--device.ssm.probability", "1", "--device.ssm.file", str(ssm),
               "--device.ssm.measures", "TTC PET DRAC", "--device.ssm.trajectories", "true",
               "--device.ssm.write-positions", "true",
               "--no-step-log", "true"]
    subprocess.run(command, check=True)
    return {"fcd": str(fcd), "ssm": str(ssm)}


def read_fcd(path: str | Path, *, source_id: str, source_type: str = "sumo_gt",
             network_path: str | Path | None = None) -> list[TrackPoint]:
    converter = None
    if network_path:
        try:
            import sumolib
            network = sumolib.net.readNet(str(network_path))
            converter = network.convertXY2LonLat
        except Exception as exc:
            raise ValueError(f"Could not read SUMO network projection: {exc}") from exc

    points: list[TrackPoint] = []
    for _, timestep in ET.iterparse(path, events=("end",)):
        if timestep.tag != "timestep":
            continue
        time_s = float(timestep.attrib["time"])
        for actor in list(timestep):
            if actor.tag not in {"vehicle", "person"}:
                continue
            actor_id = actor.attrib.get("id", "")
            road_class = "pedestrian" if actor.tag == "person" else actor.attrib.get("type", "vehicle")
            road_class = road_class.lower()
            if class_group(road_class) == "other road user" and class_group(road_class.split("_")[0]) != "other road user":
                road_class = road_class.split("_")[0]  # e.g. car_seeded -> car
            x, y = float(actor.attrib["x"]), float(actor.attrib["y"])
            flags = []
            lat = lon = None
            if converter:
                lon, lat = converter(x, y)
                flags.append("network_projection_available")
            points.append(TrackPoint(
                source_id=source_id, timestamp_s=time_s, track_id=actor_id,
                road_user_class=road_class, x_m=x, y_m=y,
                radius_m=_default_radius(road_class), quality_flags=tuple(flags),
                source_type=source_type, class_group=class_group(road_class),
                coordinate_system="metric_m",
                lat=lat, lon=lon,
            ))
        timestep.clear()
    return points


def read_ssm_values(path: str | Path) -> list[dict]:
    """Read encounter records and their TTC/PET/DRAC time series from SUMO XML."""
    rows = []
    for _, element in ET.iterparse(path, events=("end",)):
        if element.tag.lower() in {"conflict", "encounter"}:
            row = {"element": element.tag, **element.attrib}
            for child in element:
                tag = child.tag.lower().replace("span", "")
                measure = next((name for name in ("ttc", "pet", "drac", "mdrac") if name in tag), "")
                if measure in {"ttc", "pet", "drac", "mdrac"}:
                    try:
                        raw = child.attrib.get("values", "")
                        if not raw and child.attrib.get("value"):
                            raw = child.attrib["value"]
                        values = [float(v) for v in raw.split() if v.upper() != "NA"]
                    except ValueError:
                        values = []
                    row[measure] = values
            rows.append(row)
            element.clear()
    return rows


def _section(root, name: str, values: dict[str, str]) -> None:
    section = ET.SubElement(root, name)
    for key, value in values.items():
        ET.SubElement(section, key, {"value": value})


def _default_radius(road_class: str) -> float:
    if road_class in {"pedestrian", "person"}:
        return 0.35
    if road_class in {"bicycle", "motorcycle", "motorbike"}:
        return 1.0
    return 2.2
