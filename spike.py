import sys, cv2
from vision_zero.ingest import load_tracks
from vision_zero.vision import render_track_frames
from ultralytics import YOLO

weights = sys.argv[1] if len(sys.argv) > 1 else "yolo26n.pt"
points = load_tracks("examples/sample_tracks.csv")
video = render_track_frames(points, "spike_out")   # the project's own renderer
model = YOLO(weights)

cap = cv2.VideoCapture(str(video))
frames = checked = boxes = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    frames += 1
    if frames % 5:
        continue
    result = model.predict(frame, conf=0.25, verbose=False)[0]
    checked += 1
    boxes += len(result.boxes)
    if checked == 10:
        cv2.imwrite("spike_out/frame_detected.jpg", result.plot())
print(f"Checked {checked} frames, found {boxes} boxes "
      f"(about {boxes / max(checked, 1):.1f} per frame; the scene has 4 road users)")