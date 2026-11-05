import json
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from lib.data import current_run, rank_hotspots, source_banner
from lib.ui import STRETCH, chips, empty_state, explain_flag, page, split_flags, style_fig

page("Hotspot review", "🗺️", "Ranked candidate review areas")
run_id, run = current_run()
if not run_id:
    st.stop()
source_banner(run_id, run)

hotspots, events = rank_hotspots(run["hotspots"]), run["events"]
cell_size = float(run.get("config", {}).get("cell_size_m", 25))
if hotspots.empty:
    empty_state("No review areas were produced for this run.")
    st.stop()

# --- Map or metric grid -----------------------------------------------------
geojson = Path(run["root"]) / "hotspots.geojson"
data = json.loads(geojson.read_text(encoding="utf-8")) if geojson.exists() else {}
features = data.get("features", [])

if features:
    import folium
    from streamlit_folium import st_folium
    center = features[0]["geometry"]["coordinates"][::-1]
    fmap = folium.Map(location=center, zoom_start=16, tiles="OpenStreetMap")
    folium.GeoJson(data, name="review areas").add_to(fmap)
    st_folium(fmap, height=520, use_container_width=True)
elif {"cell_x", "cell_y"}.issubset(hotspots.columns):
    st.caption("This run has no geographic registration, so review areas are shown on the local metric grid.")
    fig = go.Figure()
    top = hotspots.event_count.max()
    for row in hotspots.itertuples():
        x0, y0 = row.cell_x * cell_size, row.cell_y * cell_size
        opacity = 0.25 + 0.6 * (row.event_count / top if top else 0)
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x0 + cell_size, y1=y0 + cell_size,
                      fillcolor=f"rgba(217,119,6,{opacity:.2f})", line=dict(color="#d97706", width=1))
        fig.add_annotation(x=x0 + cell_size / 2, y=y0 + cell_size / 2, showarrow=False,
                           text=f"<b>{row.event_count}</b> event(s)<br>({row.cell_x}, {row.cell_y})")
    if {"x_m", "y_m"}.issubset(events.columns) and not events.empty:
        fig.add_trace(go.Scatter(x=events.x_m, y=events.y_m, mode="markers", name="Candidate events",
                                 marker=dict(size=9, color="#0f766e", line=dict(width=1, color="white"))))
    xs = [c * cell_size for c in hotspots.cell_x] + [(c + 1) * cell_size for c in hotspots.cell_x]
    ys = [c * cell_size for c in hotspots.cell_y] + [(c + 1) * cell_size for c in hotspots.cell_y]
    pad = cell_size * 0.2
    fig.update_xaxes(range=[min(xs) - pad, max(xs) + pad], title="x (m)")
    fig.update_yaxes(range=[min(ys) - pad, max(ys) + pad], title="y (m)", scaleanchor="x", scaleratio=1)
    st.plotly_chart(style_fig(fig, 460), **STRETCH)

# --- Ranked table ---------------------------------------------------------
st.subheader("Ranked review areas")
cols = [c for c in ("cell_x", "cell_y", "event_count", "min_ttc_s", "min_pet_s", "dominant_conflict_type",
                    "dominant_road_user_pair", "rate_per_1000", "observed_road_users", "coverage_flags") if c in hotspots]
st.dataframe(hotspots[cols], hide_index=True, column_config={
    "cell_x": "Cell x", "cell_y": "Cell y",
    "event_count": st.column_config.ProgressColumn("Events", min_value=0, max_value=int(hotspots.event_count.max()), format="%d"),
    "min_ttc_s": st.column_config.NumberColumn("Min TTC (s)", format="%.2f"),
    "min_pet_s": st.column_config.NumberColumn("Min PET (s)", format="%.2f"),
    "dominant_conflict_type": "Main pattern", "dominant_road_user_pair": "Pair",
    "rate_per_1000": st.column_config.NumberColumn("Rate / 1,000 users", format="%.0f"),
    "observed_road_users": "Road users", "coverage_flags": "Coverage flags",
}, **STRETCH)

# --- Drill-down -----------------------------------------------------------
if {"cell_x", "cell_y"}.issubset(hotspots.columns) and {"x_m", "y_m"}.issubset(events.columns):
    st.subheader("Events in a review area")
    options = {f"Cell ({int(r.cell_x)}, {int(r.cell_y)}) · {int(r.event_count)} event(s)": (int(r.cell_x), int(r.cell_y))
               for r in hotspots.itertuples()}
    label = st.selectbox("Review area", list(options))
    x_cell, y_cell = options[label]
    inside = events[(events.x_m // cell_size == x_cell) & (events.y_m // cell_size == y_cell)]
    row = hotspots[(hotspots.cell_x == x_cell) & (hotspots.cell_y == y_cell)].iloc[0]
    flags = split_flags(row.get("coverage_flags"))
    if flags:
        chips([explain_flag(f) for f in flags], warn=True)
    st.dataframe(inside[[c for c in ("timestamp_s", "conflict_type", "class_a", "class_b", "indicator_type",
                                     "indicator_value_s", "severity_band") if c in inside]],
                 hide_index=True, **STRETCH)
