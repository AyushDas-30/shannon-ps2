import streamlit as st

from lib.data import current_run, source_banner


st.set_page_config(page_title="Vision Zero review", page_icon="🚦", layout="wide")
st.title("Vision Zero · Road risk review")
st.caption("Precomputed traffic-conflict analysis for engineering review")
run_id, run = current_run()
if run_id:
    source_banner(run_id, run)
    tracks, events, hotspots = run["tracks"], run["events"], run["hotspots"]
    left, mid, right = st.columns(3)
    left.metric("Track observations", len(tracks))
    mid.metric("Candidate events", len(events))
    right.metric("Review areas", len(hotspots))
    validation = run.get("validation", {})
    if validation.get("quality_banner"):
        st.warning(validation["quality_banner"])
    st.subheader("Coverage and limitations")
    st.write(run.get("config", {}).get("method_note", "Metric interpretation depends on coordinate quality and observation coverage."))
    report = run["root"] + "/engineer_summary.md"
    try:
        st.page_link("pages/7_Report_Export.py", label="Open report and downloads")
    except Exception:
        pass
else:
    st.write("Use the navigation pages after placing a precomputed run under `outputs/runs/<run_id>/`.")
