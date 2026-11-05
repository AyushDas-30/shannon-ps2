"""PyTorch-free detector/tracker fallback: Darknet YOLO via OpenCV DNN + IoU tracker.

Used by ``detect_and_track`` when ``weights`` is a Darknet ``.weights`` file (a matching
``.cfg`` and ``coco.names`` must sit beside it). Produces the same box rows as the
Ultralytics path. Tracking is greedy IoU association with a short coast period; it is
simpler than ByteTrack and will fragment tracks more on crowded or tiny targets.
"""

from pathlib import Path

import numpy as np

ROAD_USER_CLASSES = {"person", "bicycle", "car", "motorbike", "bus", "truck"}


def _iou(a, b) -> float:
    ix1, iy1, ix2, iy2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


class DarknetTracker:
    def __init__(self, weights: str | Path, *, conf: float = 0.25, input_size=(608, 352),
                 nms: float = 0.45, iou_min: float = 0.15, max_age: int = 6):
        import cv2
        weights = Path(weights)
        cfg = weights.with_suffix(".cfg")
        names = weights.parent / "coco.names"
        if not cfg.exists() or not names.exists():
            raise FileNotFoundError(f"Need {cfg.name} and coco.names next to {weights.name}")
        self.names = [n.strip() for n in names.read_text().splitlines() if n.strip()]
        net = cv2.dnn.readNetFromDarknet(str(cfg), str(weights))
        self.model = cv2.dnn_DetectionModel(net)
        self.model.setInputParams(scale=1 / 255, size=input_size, swapRB=True)
        self.conf, self.nms, self.iou_min, self.max_age = conf, nms, iou_min, max_age
        self.tracks: dict[int, dict] = {}
        self.next_id = 1

    def update(self, frame) -> list[dict]:
        """Return [{xyxy, name, conf, id}] for the current frame."""
        classes, scores, boxes = self.model.detect(frame, self.conf, self.nms)
        dets = []
        for cid, score, (x, y, w, h) in zip(np.array(classes).flatten(), np.array(scores).flatten(), boxes):
            name = self.names[int(cid)]
            if name in ROAD_USER_CLASSES:
                dets.append({"xyxy": (float(x), float(y), float(x + w), float(y + h)),
                             "name": "motorcycle" if name == "motorbike" else name, "conf": float(score)})
        pairs = sorted(((_iou(t["xyxy"], d["xyxy"]), tid, i)
                        for tid, t in self.tracks.items() for i, d in enumerate(dets)), reverse=True)
        used_t, used_d = set(), set()
        for iou, tid, i in pairs:
            if iou < self.iou_min:
                break
            if tid in used_t or i in used_d:
                continue
            used_t.add(tid); used_d.add(i)
            self.tracks[tid].update(xyxy=dets[i]["xyxy"], age=0, name=dets[i]["name"])
            dets[i]["id"] = tid
        for i, d in enumerate(dets):
            if i not in used_d:
                d["id"] = self.next_id
                self.tracks[self.next_id] = {"xyxy": d["xyxy"], "age": 0, "name": d["name"]}
                self.next_id += 1
        for tid in list(self.tracks):
            if tid not in used_t and tid not in {d["id"] for d in dets}:
                self.tracks[tid]["age"] += 1
                if self.tracks[tid]["age"] > self.max_age:
                    del self.tracks[tid]
        return dets
