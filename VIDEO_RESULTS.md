# Video stage results (clip-01, 20 s, 640x360, ~28.5 fps)

**Detector:** YOLOv4 (Darknet, COCO) via OpenCV DNN at 608x352, conf 0.25, every frame, plus a greedy IoU tracker
(`src/vision_zero/opencv_backend.py`). Ultralytics/PyTorch was not installable in the sandbox. Use
`yolo26n.pt` on a machine with PyTorch for the repo's baseline; results here are NOT a YOLO26 result.
Needs OpenCV 4.x (OpenCV 5 removed Darknet support). Weights are not bundled (257 MB):
https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v4_pre/yolov4.weights (+ yolov4.cfg, coco.names, put beside it).

**Output:** 8,654 boxes, 579 frames, 678 track IDs (median track length 4 frames, i.e. heavy fragmentation).
Tracks are in PIXEL coordinates. No calibration exists, so metric TTC/PET are suppressed (0 events by design).

**Hand-checked quality (frames 150 and 420 only, 56 labelled boxes; labels made by visual review, not CVAT):**
scored on near/mid field only (box bottom y >= 180 px), vehicle vs person groups, IoU 0.5
- vehicle: precision 0.84 (21 TP / 4 FP), recall 0.62 (13 FN)
- person: precision 1.0, recall 0.20 (1 of 5)
Excluded from scoring: far field (y < 180), where most small vehicles are missed, and one billboard false positive.
Known false positives: a full-frame "car" box that persists all 579 frames; a billboard labelled truck.
Two frames is a very small sample; treat numbers as indicative.
