# PS-02 Vision Zero — Input and Setup Guide

This guide lists where to obtain each external input, where to put it, and how to pass it to the project. The active project specification is [Updated Plan v3](PS-02-Vision-Zero-Updated-Plan-v3.md).

## Start with the included synthetic demo

The first run needs no external traffic dataset, map, or video. It creates repeatable example tracks and runs the analysis/dashboard:

```powershell
cd C:\shannon_proj
.\run_demo.ps1
```

The generated sample inputs are `examples/sample_tracks.csv` and `examples/expected_events.csv`. The analysis bundle is written under `outputs/runs/seeded-demo/`.

## Compute resources: local CPU first

The MVP can run on a local machine without a GPU. SUMO scenarios, track ingestion, TTC/PET analysis, hotspot aggregation, reports, and the Streamlit dashboard are CPU work. Object detection is the step most likely to run slowly on CPU; Ultralytics supports CPU and CUDA inference through its device setting ([prediction docs](https://docs.ultralytics.com/modes/predict)).

Recommended sequence:

1. Run the included synthetic demo locally.
2. Run a short video through the small `yolo26n.pt` model on CPU. Keep the clip short and use the default inference image size for an initial pass.
3. Only move inference to a GPU if CPU processing is too slow for the review timeline. Move the resulting track/prediction CSVs back to the local project; analysis and the dashboard can remain local.
4. Do not fine-tune a model for the first pass. The project plan calls for fine-tuning only if measured detection quality shows a real gap.

| Option | Use it when | Trade-offs |
|---|---|---|
| Local CPU | Synthetic demo, small SUMO runs, short clips, event analysis, reports, and dashboard | No GPU setup or cloud transfer. YOLO inference may take longer. |
| Google Colab GPU | A one-off acceleration for YOLO inference or a small experiment | GPU availability and runtime limits vary; free resources are not guaranteed. See [Colab resource limits](https://research.google.com/colaboratory/faq.html). |
| Kaggle Notebook GPU | A one-off inference run when a notebook workflow is convenient | GPU time has a quota and availability can vary. See [Kaggle GPU usage guidance](https://www.kaggle.com/docs/efficient-gpu-usage). |
| AWS GPU instance | Sustained batch processing or a longer-running deployment with an identified need | Requires cloud setup and is billed while the instance runs. Check [EC2 On-Demand pricing](https://aws.amazon.com/ec2/pricing/on-demand/) before launching one. |

For this MVP, start local and add GPU compute only if inference speed becomes the bottleneck. Keep private footage local unless you have permission to upload it to the chosen service. The dashboard reads precomputed results; it does not need a GPU or a cloud server to display them.

## Input checklist

| Input | Where to get it | Save it as / use it for |
|---|---|---|
| SUMO simulator | [Official SUMO Windows installation guide](https://eclipse.dev/sumo/docs/Installing/) | Install SUMO and put its `bin` directory on `PATH`. The simulator produces vehicle/pedestrian tracks and SSM output. |
| OSM road extract | [OpenStreetMap Export](https://www.openstreetmap.org/export) for a small selected area; [Geofabrik downloads](https://www.geofabrik.de/data/download.html) for a regional extract | Save a small `.osm` or `.osm.pbf` under `inputs/maps/`, such as `inputs/maps/intersection.osm`. |
| Connected road-user paths | Inspect the converted network in SUMO-GUI/NetEdit | Copy `examples/osm_paths.template.json` to `inputs/routes/paths.json`; replace every placeholder with connected SUMO edge IDs from your map. Include vehicle and pedestrian paths. |
| YOLO model weights | The Ultralytics package downloads `yolo26n.pt` on first use; see the [official quickstart](https://docs.ultralytics.com/quickstart). | Use `yolo26n.pt` for the baseline, or provide a compatible local `.pt` weights file. |
| Real traffic clip | Prefer a short clip recorded by the team with permission. Dataset option: [UA-DETRAC project page](https://sites.google.com/view/daweidu/projects/ua-detrac). | Keep raw footage outside the repository, for example `inputs/private/clip.mp4`. Use it to demonstrate detection/tracking. |
| Camera calibration landmarks | Measure visible points in the clip and their corresponding ground-plane positions in metres. | Save JSON with `image_points` and `ground_points_m` arrays under `inputs/calibration/`. Needed for metric video TTC/PET. |
| Detection labels | Hand-check a sample of frames in a spreadsheet or annotation tool, such as CVAT. | Export/convert to CSV fields `frame_id,class,x1,y1,x2,y2` under `inputs/labels/`. Used for precision/recall. |
| Expected seeded events | The sample generator writes an example; for custom scenarios, record the expected pair/time in the same format. | CSV fields: `source_id,road_user_1,road_user_2,indicator_type,expected_time_s`. |

### SUMO and version setup

The official SUMO install page provides Windows installers and portable archives. After installation, open a new PowerShell window and confirm:

```powershell
sumo --version
netconvert --version
```

The project also uses Python `sumolib` to read network projections. The current project dependency is pinned in `pyproject.toml` and `requirements.txt`; keep the Python package version compatible with the SUMO installation.

### Map data and attribution

Use a small bounding box containing one intersection and its approaches. The OpenStreetMap website’s export function works for a small area; Geofabrik is useful for larger regional extracts. Convert it to a SUMO network with:

```powershell
vision-zero build-network inputs\maps\intersection.osm network.net.xml
```

Open `network.net.xml` in SUMO-GUI or NetEdit and inspect the edge IDs. Edit `inputs/routes/paths.json`; example structure:

```json
{
  "vehicle_paths": {
    "vehicle_straight": ["edge_in_1", "edge_junction_1", "edge_out_1"],
    "vehicle_turn": ["edge_in_2", "edge_junction_2", "edge_out_3"]
  },
  "pedestrian_paths": {
    "pedestrian_crossing": ["walk_in_1", "walk_crossing_1", "walk_out_1"]
  }
}
```

Those edge names are illustrative only. Replace them with valid, connected IDs from your converted map. When showing or distributing a map made from OSM data, include attribution such as **© OpenStreetMap contributors** and link to the [ODbL/copyright notice](https://www.openstreetmap.org/copyright).

### Generate seeded SUMO tracks and SSM data

Install this project, generate routes, write a simulation config, and run a scenario:

```powershell
python -m pip install -e .
vision-zero seed-routes inputs\routes\paths.json inputs\routes\crossing.rou.xml --seed 42 --conflict-mode crossing
vision-zero write-config network.net.xml inputs\routes\crossing.rou.xml inputs\routes\crossing.sumocfg --duration 180
vision-zero simulate inputs\routes\crossing.sumocfg --network network.net.xml --render --weights yolo26n.pt --out outputs --run-id crossing-seed-42
```

The route generator supports `crossing`, `turning`, `bike_cut_across`, and `control`. The simulation run creates FCD tracks and requests TTC/PET/DRAC output through SUMO’s SSM device. SUMO documents the output format and its default thresholds on the [SSM Device page](https://sumo.dlr.de/docs/Simulation/Output/SSM_Device.html).

For a control run, repeat the commands using `--conflict-mode control` and a distinct route/config/run ID. Inspect the generated tracks and SSM output; the control schedule is a comparison scenario, not a guarantee that no interactions occur.

### Get model weights

After installing the project dependencies, the Ultralytics loader can download the small baseline weights automatically. The project’s `detect` command accepts a compatible weights path:

```powershell
vision-zero detect inputs\private\clip.mp4 --weights yolo26n.pt --source-id clip-01 --out outputs --run-id clip-01
```

Ultralytics offers AGPL-3.0 and Enterprise licensing options. Review the [official licensing information](https://docs.ultralytics.com/) before redistributing the model or a project that includes it.

### Real clip and calibration

Use a short, fixed-camera clip where vehicle/pedestrian movement is visible. Only use footage the team has permission to analyze. Do not put raw video in the repository; the dashboard only serves media under the run’s `evidence_safe` folder. Redact faces and plates before adding any real footage evidence there. The detector command itself stores tracks and box predictions, not the source clip.

Create `inputs/calibration/landmarks.json` with at least four non-collinear image/ground-plane point pairs:

```json
{
  "image_points": [[120, 410], [850, 405], [180, 720], [790, 715]],
  "ground_points_m": [[0, 0], [12, 0], [0, 18], [12, 18]]
}
```

The values above are examples, not real measurements. Use surveyed/measured distances from your scene. Fit the homography and run calibrated detection:

```powershell
vision-zero calibrate inputs\calibration\landmarks.json inputs\calibration\camera.json --max-rms-m 1.0
vision-zero detect inputs\private\clip.mp4 --weights yolo26n.pt --source-id clip-01 --homography-json inputs\calibration\camera.json --out outputs --run-id clip-01-calibrated
```

Without a valid homography, detections remain in pixel coordinates and metric TTC/PET are suppressed. Do not treat pixel distance as metres.

### Hand-check detection quality

Prepare a CSV of manually reviewed boxes. The column names must be exactly:

```csv
frame_id,class,x1,y1,x2,y2
```

The detector writes predictions to `outputs/runs/<run_id>/detection_predictions.csv`. To include precision/recall in the run’s validation summary, pass the hand-checked labels when analyzing:

```powershell
vision-zero analyze inputs\tracks\tracks.csv --source-type video --detection-labels inputs\labels\clip-labels.csv --detection-predictions outputs\runs\clip-01-calibrated\detection_predictions.csv --out outputs --run-id clip-01-reviewed
```

The standalone scorer is also available:

```powershell
vision-zero detection-metrics inputs\labels\clip-labels.csv outputs\runs\clip-01-calibrated\detection_predictions.csv --iou 0.5
```

### Validate known seeded events

Make a CSV with the expected event pairs and approximate event times, then pass it to `analyze`:

```csv
source_id,road_user_1,road_user_2,indicator_type,expected_time_s
crossing-seed-42,ped_000,veh_000,TTC,22.5
```

```powershell
vision-zero analyze outputs\runs\crossing-seed-42\tracks.csv --expected-events-csv inputs\labels\expected-events.csv --out outputs --run-id crossing-seed-42-validated
```

The sample project includes `examples/expected_events.csv` for its generated `examples/sample_tracks.csv`.

## Dataset choices and limits

- **UA-DETRAC** is a real traffic surveillance benchmark with annotated vehicle detection/tracking. It is useful for vehicle tracking demonstration, but it is not a substitute for pedestrian coverage or metric calibration.
- **BDD100K** provides driving videos and task annotations, but the official download page lists the full video package as 1.8 TB. Review the dataset’s own terms and cite it if used. [Official download details](https://github.com/bdd100k/bdd100k/blob/master/doc/source/download.rst)
- A public dataset clip may not permit redistribution. Keep its license and attribution with the submission and publish only media you are allowed to share.

## Files to prepare

```text
inputs/
  maps/intersection.osm
  routes/paths.json
  private/clip.mp4                 # keep out of Git
  calibration/landmarks.json
  labels/clip-labels.csv
  labels/expected-events.csv
```

Do not commit private source footage, model weights, or unredacted frames. The `.gitignore` excludes common video/model files. OSM-derived public maps should retain visible attribution.
