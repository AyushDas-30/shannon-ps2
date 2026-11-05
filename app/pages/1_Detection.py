from pathlib import Path

import plotly.express as px
import streamlit as st

from lib.data import current_run, source_banner
from lib.ui import STRETCH, empty_state, page, pretty, style_fig
from vision_zero.privacy import require_safe_evidence

page("Detection review", "🎥", "What was observed: road-user tracks and redacted evidence")
run_id, run = current_run()
if not run_id:
    st.stop()
source_banner(run_id, run)

tracks = run["tracks"]
if tracks.empty:
    empty_state("No track table is available for this run.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Observations", f"{len(tracks):,}")
c2.metric("Road users", tracks["track_id"].nunique() if "track_id" in tracks else "n/a")
c3.metric("Classes", tracks["class"].nunique() if "class" in tracks else "n/a")
c4.metric("Mean confidence", f"{tracks['confidence'].mean():.2f}" if "confidence" in tracks else "n/a")

tab_paths, tab_table, tab_evidence = st.tabs(["Trajectories", "Track table", "Evidence frames"])

with tab_paths:
    if {"x", "y", "track_id"}.issubset(tracks.columns):
        color = "class_group" if "class_group" in tracks else "track_id"
        fig = px.line(tracks.assign(track_id=tracks.track_id.astype(str)), x="x", y="y",
                      line_group="track_id", color=color,
                      hover_data=[c for c in ("track_id", "timestamp_s", "class") if c in tracks])
        fig.update_yaxes(scaleanchor="x", scaleratio=1, title="y (m)")
        fig.update_xaxes(title="x (m)")
        st.plotly_chart(style_fig(fig, 480), **STRETCH)
        st.caption("Paths are drawn in a shared metric coordinate system.")
    else:
        empty_state("Trajectory columns (x, y, track_id) are not available.")

with tab_table:
    view = tracks
    if "class_group" in tracks:
        groups = sorted(tracks["class_group"].dropna().unique())
        chosen = st.multiselect("Class group", groups, default=groups)
        view = tracks[tracks["class_group"].isin(chosen)]
        counts = view["class_group"].map(pretty).value_counts().rename_axis("Class group").reset_index(name="Observations")
        st.bar_chart(counts, x="Class group", y="Observations", height=200)
    st.dataframe(view.head(500), hide_index=True, **STRETCH)
    st.caption(f"Showing up to 500 of {len(view):,} rows.")

with tab_evidence:
    media = Path(run["root"]) / "evidence_safe"
    images = sorted(media.glob("*.jpg"))[:20] if media.exists() else []
    videos = sorted(media.glob("*.mp4"))[:2] if media.exists() else []
    if not images and not videos:
        empty_state("No redacted evidence is attached to this run.")
    for video in videos:
        st.video(str(require_safe_evidence(video, safe_root=media)))
    grid = st.columns(3)
    for i, image in enumerate(images):
        grid[i % 3].image(str(require_safe_evidence(image, safe_root=media)),
                          caption=image.stem.replace("_", " "), **STRETCH)
    st.caption("Only pre-rendered, non-identifying evidence is displayed.")
