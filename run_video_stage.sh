#!/usr/bin/env bash
# Video stage: detection + tracking in PIXEL coordinates (no calibration available).
# Run on a machine with PyTorch (local CPU is fine for a 20 s clip) or in Colab.
set -e
pip install -e ".[pipeline]"
vision-zero detect inputs/private/clip.mp4 --weights yolo26n.pt --source-id clip-01 --out outputs --run-id clip-01
# After hand-correcting boxes into inputs/labels/clip-labels.csv (frame_id,class,x1,y1,x2,y2):
vision-zero detection-metrics inputs/labels/clip-labels.csv outputs/runs/clip-01/detection_predictions.csv --iou 0.5
