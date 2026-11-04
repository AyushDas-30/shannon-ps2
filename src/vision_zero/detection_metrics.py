"""Frame-level object detection precision/recall against a hand-checked CSV."""

import csv
from collections import defaultdict
from pathlib import Path


def detection_precision_recall(labels_csv: str | Path, predictions_csv: str | Path,
                              *, iou_threshold: float = 0.5) -> dict:
    """Both CSVs require frame_id,class,x1,y1,x2,y2; predictions may add confidence."""
    labels = _read_boxes(labels_csv)
    predictions = _read_boxes(predictions_csv)
    grouped_truth: dict[str, list[dict]] = defaultdict(list)
    grouped_pred: dict[str, list[dict]] = defaultdict(list)
    for row in labels:
        grouped_truth[row["frame_id"]].append(row)
    for row in predictions:
        grouped_pred[row["frame_id"]].append(row)
    classes = sorted({r["class"] for r in labels} | {r["class"] for r in predictions})
    result = {}
    for category in classes:
        tp = fp = fn = 0
        for frame_id in set(grouped_truth) | set(grouped_pred):
            truth = [r for r in grouped_truth[frame_id] if r["class"] == category]
            pred = [r for r in grouped_pred[frame_id] if r["class"] == category]
            candidates = sorted(
                ((_iou(p, t), pi, ti) for pi, p in enumerate(pred) for ti, t in enumerate(truth)),
                reverse=True,
            )
            used_pred, used_truth = set(), set()
            for overlap, pi, ti in candidates:
                if overlap >= iou_threshold and pi not in used_pred and ti not in used_truth:
                    used_pred.add(pi)
                    used_truth.add(ti)
            tp += len(used_pred)
            fp += len(pred) - len(used_pred)
            fn += len(truth) - len(used_truth)
        result[category] = {
            "true_positive": tp, "false_positive": fp, "false_negative": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
        }
    return {"iou_threshold": iou_threshold, "per_class": result}


def _read_boxes(path):
    required = {"frame_id", "class", "x1", "y1", "x2", "y2"}
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"Missing box CSV fields: {', '.join(sorted(missing))}")
        return [{**row, **{k: float(row[k]) for k in ("x1", "y1", "x2", "y2")}}
                for row in reader]


def _iou(a, b):
    x1, y1 = max(a["x1"], b["x1"]), max(a["y1"], b["y1"])
    x2, y2 = min(a["x2"], b["x2"]), min(a["y2"], b["y2"])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(0, a["x2"] - a["x1"]) * max(0, a["y2"] - a["y1"])
    area_b = max(0, b["x2"] - b["x1"]) * max(0, b["y2"] - b["y1"])
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0
