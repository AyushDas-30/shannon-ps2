import streamlit as st

from lib.data import current_run, source_banner

st.title("Conflict patterns")
run_id, run = current_run()
if run_id:
    source_banner(run_id, run)
    events = run["events"]
    if events.empty:
        st.info("No candidate events are available for pattern summaries.")
    else:
        for column in ("conflict_type", "class_a", "class_b", "severity_band"):
            if column in events:
                st.subheader(column.replace("_", " ").title())
                st.bar_chart(events[column].fillna("unknown").value_counts())
        if "timestamp_s" in events:
            events = events.copy()
            events["time_window_s"] = (events.timestamp_s // 60).astype(int) * 60
            st.subheader("Events by minute")
            st.line_chart(events.groupby("time_window_s").size())
        st.subheader("Threshold sensitivity")
        st.json(run.get("validation", {}).get("threshold_sensitivity", {}))
