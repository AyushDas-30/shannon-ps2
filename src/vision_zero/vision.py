"""Synthetic frame rendering and optional Ultralytics detector/tracker adapter."""

from pathlib import Path
import json
import csv

from .ingest import class_group
from .schema import TrackPoint


def render_track_frames(points: list[TrackPoint], out_dir: str | Path, *, fps: int = 5,
                        width: int = 960, height: int = 640, margin: int = 45) -> Path:
    """Render anonymized top-down frames from metric SUMO tracks."""
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Install opencv-python-headless and numpy to render frames") from exc
    if not points:
        raise ValueError("Cannot render an empty track set")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    times = sorted({p.timestamp_s for p in points})
    min_x, max_x = min(p.x_m for p in points), max(p.x_m for p in points)
    min_y, max_y = min(p.y_m for p in points), max(p.y_m for p in points)
    span_x, span_y = max(max_x - min_x, 1.0), max(max_y - min_y, 1.0)
    scale = min((width - 2 * margin) / span_x, (height - 2 * margin) / span_y)
    video_path = out / "sumo_render.mp4"
    homography = [
        [1 / scale, 0, min_x - margin / scale],
        [0, -1 / scale, min_y + (height - margin) / scale],
        [0, 0, 1],
    ]
    (out / "render_calibration.json").write_text(json.dumps(homography, indent=2), encoding="utf-8")
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    try:
        for time_s in times:
            frame = np.full((height, width, 3), 245, dtype=np.uint8)
            for p in points:
                if p.timestamp_s != time_s:
                    continue
                px = int(margin + (p.x_m - min_x) * scale)
                py = int(height - margin - (p.y_m - min_y) * scale)
                color = (60, 150, 220) if p.class_group == "pedestrian" else (70, 90, 190)
                cv2.circle(frame, (px, py), 9 if p.class_group == "pedestrian" else 13, color, -1)
                cv2.putText(frame, p.road_user_class[:12], (px + 8, py - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (35, 35, 35), 1, cv2.LINE_AA)
            cv2.putText(frame, f"SUMO synthetic · {time_s:.1f}s", (20, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (35, 35, 35), 2, cv2.LINE_AA)
            writer.write(frame)
    finally:
        writer.release()
    return video_path


def detect_and_track(video_path: str | Path, weights: str | Path, *, source_id: str,
                     source_type: str = "sumo_detected", confidence: float = 0.25,
                     sample_every: int = 1, homography: list[list[float]] | None = None,
                     synthetic_evidence_output: str | Path | None = None,
                     predictions_csv: str | Path | None = None) -> list[TrackPoint]:
    """Run YOLO tracking. Pixel coordinates remain non-metric without homography."""
    try:
        import cv2
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("Install requirements.txt to use detector/tracker integration") from exc
    model = YOLO(str(weights))
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Unable to open video: {video_path}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        capture.release()
        raise ValueError("Video has invalid frame rate; metric timing is unavailable")
    points: list[TrackPoint] = []
    box_rows = []
    evidence_writer = None
    frame_index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if synthetic_evidence_output and evidence_writer is None:
                evidence_path = Path(synthetic_evidence_output)
                evidence_path.parent.mkdir(parents=True, exist_ok=True)
                evidence_writer = cv2.VideoWriter(str(evidence_path), cv2.VideoWriter_fourcc(*"mp4v"),
                                                   fps, (frame.shape[1], frame.shape[0]))
            if frame_index % sample_every:
                frame_index += 1
                continue
            result = model.track(frame, persist=True, tracker="bytetrack.yaml", conf=confidence, verbose=False)[0]
            boxes = result.boxes
            annotated = frame.copy() if evidence_writer is not None else None
            if boxes is not None and boxes.id is not None:
                for box, track_id in zip(boxes, boxes.id.tolist()):
                    cls_id = int(box.cls.item())
                    name = str(model.names.get(cls_id, "other road user")).lower()
                    x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
                    box_rows.append({"frame_id": frame_index, "class": name, "x1": x1, "y1": y1,
                                     "x2": x2, "y2": y2, "confidence": float(box.conf.item()),
                                     "track_id": int(track_id)})
                    x, y = (x1 + x2) / 2, y2
                    flags = []
                    if x1 <= 0 or y1 <= 0 or x2 >= frame.shape[1] - 1 or y2 >= frame.shape[0] - 1:
                        flags.append("box_clipped_at_frame_edge")
                    coordinate = "pixel"
                    if homography is not None:
                        import numpy as np
                        transformed = cv2.perspectiveTransform(
                            np.array([[[x, y]]], dtype=np.float32), np.array(homography, dtype=np.float32)
                        )[0][0]
                        x, y = float(transformed[0]), float(transformed[1])
                        coordinate = "metric_m"
                    else:
                        flags.append("metric_calibration_missing")
                    points.append(TrackPoint(
                        source_id=source_id, timestamp_s=frame_index / fps,
                        track_id=str(int(track_id)), road_user_class=name,
                        x_m=x, y_m=y, confidence=float(box.conf.item()),
                        radius_m=0.35 if class_group(name) == "pedestrian" else 2.0,
                        quality_flags=tuple(flags), source_type=source_type,
                        class_group=class_group(name), coordinate_system=coordinate,
                    ))
                    if annotated is not None:
                        cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), (40, 180, 70), 2)
                        cv2.putText(annotated, f"Road user {int(track_id)}", (int(x1), max(18, int(y1) - 6)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 100, 30), 2, cv2.LINE_AA)
            if evidence_writer is not None:
                evidence_writer.write(annotated if annotated is not None else frame)
            frame_index += 1
    finally:
        capture.release()
        if evidence_writer is not None:
            evidence_writer.release()
    if predictions_csv:
        target = Path(predictions_csv)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["frame_id", "class", "x1", "y1", "x2", "y2", "confidence", "track_id"])
            writer.writeheader()
            writer.writerows(box_rows)
    return points
