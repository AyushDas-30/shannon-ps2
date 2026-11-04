import streamlit as st

from lib.data import current_run, source_banner

st.title("Event explorer and indicator explainer")
run_id, run = current_run()
if run_id:
    source_banner(run_id, run)
    events = run["events"]
    if events.empty:
        st.info("No candidate events were observed in this run.")
    else:
        if "conflict_type" in events:
            kinds = sorted(events.conflict_type.dropna().unique())
            selected = st.multiselect("Conflict pattern", kinds, default=kinds)
            events = events[events.conflict_type.isin(selected)]
        st.dataframe(events, use_container_width=True)
        event_id = st.selectbox("Explain event", events.event_id.astype(str).tolist()) if "event_id" in events else None
        if event_id:
            event = events[events.event_id.astype(str) == event_id].iloc[0]
            st.subheader("Indicator steps")
            st.write(f"Indicator: {event.get('indicator_type', 'TTC')}")
            st.write(f"Observed value: {event.get('indicator_value_s', 'unavailable')} seconds")
            st.latex(r"TTC = \min\{t > 0 : d_{12}(t) \leq r_1+r_2\}")
            st.write("Method: short-horizon constant-velocity estimate from observed metric positions and buffered road-user footprints.")
            st.write(f"Quality flags: {event.get('quality_flags', 'none recorded')}")
            tracks = run["tracks"]
            if not tracks.empty and {"track_id", "x", "y", "timestamp_s"}.issubset(tracks.columns):
                ids = {str(event.get("road_user_a", "")), str(event.get("road_user_b", ""))}
                subset = tracks[tracks.track_id.astype(str).isin(ids)]
                if not subset.empty:
                    import plotly.express as px
                    hover = ["timestamp_s"] + (["class"] if "class" in subset else [])
                    figure = px.line(subset, x="x", y="y", color="track_id", markers=True, hover_data=hover)
                    st.plotly_chart(figure, use_container_width=True)
