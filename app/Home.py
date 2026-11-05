import plotly.express as px
import streamlit as st

from lib.data import current_run, rank_hotspots, source_banner
from lib.ui import PAGES, STRETCH, chips, explain_flag, page, pretty, split_flags, style_fig

page("Vision Zero · Road risk review", "🚦",
     "Precomputed traffic-conflict screening for engineering review")

run_id, run = current_run()
if not run_id:
    st.write("Place a precomputed run under `outputs/runs/<run_id>/` to begin.")
    st.stop()

source_banner(run_id, run)
tracks, events, hotspots = run["tracks"], run["events"], run["hotspots"]
config, validation = run.get("config", {}), run.get("validation", {})

if validation.get("quality_banner"):
    st.info(validation["quality_banner"], icon="ℹ️")

# --- Key numbers -----------------------------------------------------------
road_users = int(tracks["track_id"].nunique()) if "track_id" in tracks else config.get("track_count", 0)
duration = config.get("observation_duration_s")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Observation window", f"{duration:.0f} s" if duration else "n/a")
c2.metric("Road users", road_users)
c3.metric("Track observations", f"{len(tracks):,}")
c4.metric("Candidate events", len(events))
c5.metric("Review areas", len(hotspots))

# --- Where to look first ---------------------------------------------------
left, right = st.columns([3, 2], gap="large")
with left:
    st.subheader("Where to look first")
    ranked = rank_hotspots(hotspots)
    if ranked.empty:
        st.caption("No review areas were produced for this run.")
    else:
        top = ranked.iloc[0]
        with st.container(border=True):
            st.markdown(f"**Metric grid cell ({int(top.cell_x)}, {int(top.cell_y)})** · "
                        f"{int(top.event_count)} candidate event(s)")
            st.caption(f"Main pattern: {pretty(top.get('dominant_conflict_type', 'unknown'))} · "
                       f"Pair: {top.get('dominant_road_user_pair', 'unknown')}")
            flags = split_flags(top.get("coverage_flags"))
            if flags:
                chips([explain_flag(f) for f in flags], warn=True)
        if len(ranked) > 1:
            st.caption(f"{len(ranked) - 1} further review area(s) on the Hotspot review page.")
    st.page_link("pages/3_Hotspot_Map.py", label="Open hotspot review", icon="🗺️")

with right:
    st.subheader("Pattern mix")
    if events.empty or "conflict_type" not in events:
        st.caption("No candidate events in this run.")
    else:
        mix = events["conflict_type"].map(pretty).value_counts().reset_index()
        mix.columns = ["Pattern", "Events"]
        fig = px.pie(mix, names="Pattern", values="Events", hole=0.55)
        fig.update_traces(textinfo="value")
        fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(style_fig(fig, 300), **STRETCH)

# --- Limitations -----------------------------------------------------------
st.subheader("Coverage and limitations")
with st.container(border=True):
    st.write(config.get("method_note",
                        "Metric interpretation depends on coordinate quality and observation coverage."))
    st.caption("A run with no observed events is not evidence that a location is safe. "
               "Counts need exposure context.")

# --- Navigation ------------------------------------------------------------
st.subheader("Explore")
cols = st.columns(4)
for i, (path, label, icon, blurb) in enumerate(PAGES):
    with cols[i % 4].container(border=True):
        st.page_link(path, label=label, icon=icon)
        st.caption(blurb)
