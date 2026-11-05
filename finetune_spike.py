"""Auto-label rendered SUMO frames from ground truth and fine-tune YOLO.

Run from the repo root:
    PYTHONPATH=src python finetune_spike.py                 # export + train
    PYTHONPATH=src python finetune_spike.py --export-only   # just build the dataset
    PYTHONPATH=src python finetune_spike.py --weights yolo11n.pt --epochs 40

Labels come free from SUMO ground truth, using the exact pixel geometry of
vision_zero.vision.render_track_frames (same scale, margin and circle sizes).
"""
import argparse
import shutil
from pathlib import Path

import cv2

from vision_zero.ingest import load_tracks
from vision_zero.vision import render_track_frames

# Fallback classes from the plan (section 4.3). Extend when SUMO adds bikes/buses.
CLASSES = ["pedestrian", "vehicle"]
RADIUS_PX = {"pedestrian": 9, "vehicle": 13}   # must match render_track_frames
WIDTH, HEIGHT, MARGIN = 960, 640, 45


def export(tracks_csv, out_dir, val_fraction=0.2, stride=1):
    points = load_tracks(tracks_csv)
    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    video = render_track_frames(points, out / "render")
    times = sorted({p.timestamp_s for p in points})
    min_x = min(p.x_m for p in points); max_x = max(p.x_m for p in points)
    min_y = min(p.y_m for p in points); max_y = max(p.y_m for p in points)
    scale = min((WIDTH - 2 * MARGIN) / max(max_x - min_x, 1.0),
                (HEIGHT - 2 * MARGIN) / max(max_y - min_y, 1.0))
    by_time = {}
    for p in points:
        by_time.setdefault(p.timestamp_s, []).append(p)

    n_val = max(1, int(len(times) * val_fraction))
    split_at = len(times) - n_val          # contiguous split: last frames = val
    cap = cv2.VideoCapture(str(video))
    counts = {"train": 0, "val": 0}
    for i, t in enumerate(times):
        ok, frame = cap.read()
        if not ok:
            break
        if i % stride:
            continue
        split = "val" if i >= split_at else "train"
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out / "images" / split / f"f{i:05d}.jpg"), frame)
        lines = []
        for p in by_time[t]:
            group = "pedestrian" if p.class_group == "pedestrian" else "vehicle"
            px = MARGIN + (p.x_m - min_x) * scale
            py = HEIGHT - MARGIN - (p.y_m - min_y) * scale
            r = RADIUS_PX[group]
            # clip box to the frame so labels stay valid near edges
            x1, y1 = max(px - r, 0), max(py - r, 0)
            x2, y2 = min(px + r, WIDTH), min(py + r, HEIGHT)
            if x2 - x1 < 2 or y2 - y1 < 2:
                continue
            lines.append(f"{CLASSES.index(group)} {(x1+x2)/2/WIDTH:.6f} {(y1+y2)/2/HEIGHT:.6f} "
                         f"{(x2-x1)/WIDTH:.6f} {(y2-y1)/HEIGHT:.6f}")
        (out / "labels" / split / f"f{i:05d}.txt").write_text("\n".join(lines))
        counts[split] += 1
    cap.release()
    yaml = out / "data.yaml"
    yaml.write_text(f"path: {out.resolve()}\ntrain: images/train\nval: images/val\n"
                    f"names:\n" + "".join(f"  {i}: {c}\n" for i, c in enumerate(CLASSES)))
    print(f"Exported {counts['train']} train / {counts['val']} val frames -> {yaml}")
    return yaml


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracks", default="examples/sample_tracks.csv")
    ap.add_argument("--out", default="finetune_data")
    ap.add_argument("--weights", default="yolo26n.pt")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--export-only", action="store_true")
    a = ap.parse_args()
    yaml = export(a.tracks, a.out)
    if a.export_only:
        return
    from ultralytics import YOLO
    model = YOLO(a.weights)
    model.train(data=str(yaml), epochs=a.epochs, imgsz=a.imgsz, batch=a.batch, device="cpu",
                project=str(Path("finetune_runs").resolve()), name="road_users", exist_ok=True,
                workers=0, patience=15, plots=False, mosaic=0.5, cache=False)
    best = Path(model.trainer.best)
    print(f"\nDone. Weights: {best}")
    # quick re-check on the original video
    video = Path(a.out) / "render" / "sumo_render.mp4"
    cap = cv2.VideoCapture(str(video))
    tuned = YOLO(str(best))
    seen = {}
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        i += 1
        if i % 5:
            continue
        r = tuned.predict(f, conf=0.25, imgsz=a.imgsz, verbose=False)[0]
        for c, p in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist()):
            seen.setdefault(tuned.names[int(c)], []).append(p)
    for n, v in sorted(seen.items(), key=lambda kv: -len(kv[1])):
        print(f"{n:12s} {len(v):3d} boxes  mean conf {sum(v)/len(v):.2f}")


if __name__ == "__main__":
    main()