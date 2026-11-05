import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.data import current_run, source_banner
from lib.ui import CATEGORY_COLORS, STRETCH, chips, empty_state, explain_flag, page, pretty, split_flags, style_fig

page("Event explorer", "🔎", "Select a candidate event to see how its indicator was derived")
run_id, run = current_run()
if not run_id:
    st.stop()
source_banner(run_id, run)

events, tracks = run["events"], run["tracks"]
if events.empty:
    empty_state("No candidate events were observed in this run.",
                "That is not evidence that the location is safe; check coverage and exposure.")
    st.stop()

# --- Filters ---------------------------------------------------------------
f1, f2 = st.columns(2)
if "conflict_type" in events:
    kinds = sorted(events["conflict_type"].dropna().unique())
    picked = f1.multiselect("Conflict pattern", kinds, default=kinds, format_func=pretty)
    events = events[events["conflict_type"].isin(picked)]
if "severity_band" in events:
    bands = sorted(events["severity_band"].dropna().unique())
    picked = f2.multiselect("Severity band", bands, default=bands, format_func=pretty)
    events = events[events["severity_band"].isin(picked)]
events = events.reset_index(drop=True)
if events.empty:
    empty_state("No events match the current filters.")
    st.stop()

# --- Event table with row selection ---------------------------------------
st.caption(f"{len(events)} candidate event(s). Select a row to explain it.")
table_cols = [c for c in ("timestamp_s", "conflict_type", "class_a", "class_b", "indicator_type",
                          "indicator_value_s", "severity_band", "min_separation_m") if c in events]
shown = events[table_cols].copy()
if "conflict_type" in shown:
    shown["conflict_type"] = shown["conflict_type"].map(pretty)
selection = st.dataframe(
    shown, hide_index=True, on_select="rerun", selection_mode="single-row", key="event_table",
    column_config={
        "timestamp_s": st.column_config.NumberColumn("Time (s)", format="%.1f"),
        "conflict_type": "Pattern", "class_a": "Road user A", "class_b": "Road user B",
        "indicator_type": "Indicator",
        "indicator_value_s": st.column_config.NumberColumn("Value (s)", format="%.2f"),
        "severity_band": "Severity", "min_separation_m": st.column_config.NumberColumn("Min gap (m)", format="%.2f"),
    }, **STRETCH)
rows = selection.selection.rows if selection else []
event = events.iloc[rows[0] if rows else 0]

# --- Detail ---------------------------------------------------------------
st.divider()
st.subheader(f"{pretty(event.get('conflict_type', 'Event'))} at {event.get('timestamp_s', 0):.1f} s")
m1, m2, m3, m4 = st.columns(4)
m1.metric(event.get("indicator_type", "TTC"), f"{event.get('indicator_value_s', float('nan')):.2f} s")
m2.metric("Severity band", pretty(event.get("severity_band", "unknown")))
m3.metric("Min gap", f"{event.get('min_separation_m', float('nan')):.2f} m")
m4.metric("Pair", f"{event.get('class_a', '?')} / {event.get('class_b', '?')}")

flags = split_flags(event.get("quality_flags"))
if flags:
    st.markdown("**Quality flags**")
    chips([explain_flag(f) for f in flags], warn=any("unresolved" in f for f in flags))
    if any("unresolved" in f for f in flags):
        st.caption("An unresolved indicator means the buffered footprints already overlap at the "
                   "observed positions. Treat the value as a screening signal, not a measured time gap.")

with st.expander("How the indicator is calculated"):
    st.latex(r"TTC = \min\{t > 0 : d_{12}(t) \leq r_1+r_2\}")
    st.write("A short-horizon constant-velocity estimate from observed metric positions and "
             "buffered road-user footprints.")

# --- Trajectories and separation ------------------------------------------
needed = {"track_id", "x", "y", "timestamp_s"}
if not tracks.empty and needed.issubset(tracks.columns):
    ida, idb = str(event.get("road_user_a", "")), str(event.get("road_user_b", ""))
    t = tracks.assign(track_id=tracks["track_id"].astype(str))
    a, b = t[t.track_id == ida], t[t.track_id == idb]
    if not a.empty and not b.empty:
        left, right = st.columns(2, gap="large")
        fig = go.Figure()
        for i, (label, df) in enumerate(((ida, a), (idb, b))):
            color = CATEGORY_COLORS[i]
            fig.add_trace(go.Scatter(x=df.x, y=df.y, mode="lines+markers", name=label,
                                     line=dict(color=color), marker=dict(size=4),
                                     customdata=df.timestamp_s, hovertemplate="t=%{customdata:.1f}s<extra>" + label + "</extra>"))
            near = df.iloc[(df.timestamp_s - event["timestamp_s"]).abs().argmin()]
            fig.add_trace(go.Scatter(x=[near.x], y=[near.y], mode="markers", showlegend=False,
                                     marker=dict(size=14, color=color, symbol="star", line=dict(width=1, color="white")),
                                     hovertemplate=f"{label} at event time<extra></extra>"))
        fig.update_yaxes(scaleanchor="x", scaleratio=1, title="y (m)")
        fig.update_xaxes(title="x (m)")
        fig.update_layout(title="Paths (stars mark the event time)")
        left.plotly_chart(style_fig(fig, 380), **STRETCH)

        merged = a[["timestamp_s", "x", "y"]].merge(b[["timestamp_s", "x", "y"]], on="timestamp_s", suffixes=("_a", "_b"))
        if not merged.empty:
            merged["gap_m"] = np.hypot(merged.x_a - merged.x_b, merged.y_a - merged.y_b)
            sep = go.Figure(go.Scatter(x=merged.timestamp_s, y=merged.gap_m, mode="lines", line=dict(color=CATEGORY_COLORS[0])))
            sep.add_vline(x=float(event["timestamp_s"]), line_dash="dash", line_color=CATEGORY_COLORS[1])
            sep.update_xaxes(title="Time (s)")
            sep.update_yaxes(title="Centre-to-centre distance (m)", rangemode="tozero")
            sep.update_layout(title="Distance between the two road users")
            right.plotly_chart(style_fig(sep, 380), **STRETCH)
