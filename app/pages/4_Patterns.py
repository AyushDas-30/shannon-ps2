import pandas as pd
import plotly.express as px
import streamlit as st

from lib.data import current_run, source_banner
from lib.ui import STRETCH, empty_state, page, pretty, style_fig

page("Conflict patterns", "📊", "How candidate events are distributed")
run_id, run = current_run()
if not run_id:
    st.stop()
source_banner(run_id, run)

events = run["events"]
if events.empty:
    empty_state("No candidate events are available for pattern summaries.")
    st.stop()

dimensions = [c for c in ("conflict_type", "class_a", "class_b", "severity_band") if c in events]
cols = st.columns(2, gap="large")
for i, column in enumerate(dimensions):
    counts = events[column].fillna("unknown").map(pretty).value_counts().rename_axis(pretty(column)).reset_index(name="Events")
    fig = px.bar(counts, x="Events", y=pretty(column), orientation="h", title=pretty(column))
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(dtick=1)
    cols[i % 2].plotly_chart(style_fig(fig, 260), **STRETCH)

if "timestamp_s" in events:
    span = events.timestamp_s.max() - events.timestamp_s.min()
    window = 60 if span > 300 else 5
    binned = (events.timestamp_s // window * window).value_counts().sort_index().rename_axis("Window start (s)").reset_index(name="Events")
    fig = px.bar(binned, x="Window start (s)", y="Events", title=f"Events per {window}-second window")
    st.plotly_chart(style_fig(fig, 280), **STRETCH)

st.subheader("Threshold sensitivity")
sens = run.get("validation", {}).get("threshold_sensitivity", {})
if not sens:
    st.caption("No threshold sensitivity was computed for this run.")
else:
    table = pd.DataFrame([
        {"Multiplier": k, "Threshold (s)": round(v.get("threshold_s", float("nan")), 2),
         "Events": v.get("event_count"), "Top review area": (v.get("hotspot_ranking") or ["none"])[0]}
        for k, v in sens.items()])
    rankings = {tuple(v.get("hotspot_ranking", [])) for v in sens.values()}
    if len(rankings) == 1:
        st.success("Review-area ranking is unchanged across all tested thresholds.", icon="✅")
    else:
        st.warning("Review-area ranking changes with the threshold. Treat the order as tentative.", icon="⚠️")
    left, right = st.columns([2, 3], gap="large")
    left.dataframe(table, hide_index=True, **STRETCH)
    fig = px.line(table, x="Threshold (s)", y="Events", markers=True, title="Events vs threshold")
    fig.update_yaxes(rangemode="tozero")
    right.plotly_chart(style_fig(fig, 260), **STRETCH)
