import pandas as pd
import streamlit as st

from lib.data import current_run, source_banner
from lib.ui import STRETCH, page, pretty

page("Validation", "✅", "How well do screening results agree with references?")
run_id, run = current_run()
if not run_id:
    st.stop()
source_banner(run_id, run)

validation = run.get("validation", {})
if not validation:
    st.info("No validation summary is attached to this run yet.")
    st.stop()

if validation.get("quality_banner"):
    st.info(validation["quality_banner"], icon="ℹ️")

# --- Seeded scenarios -------------------------------------------------------
st.subheader("Seeded scenarios")
seeded = validation.get("seeded_scenarios", {})
if seeded:
    a, b, c, d = st.columns(4)
    a.metric("Expected events", seeded.get("seeded_expected_events", "n/a"))
    b.metric("Matched", seeded.get("matched_events", "n/a"))
    recall = seeded.get("event_recall")
    c.metric("Event recall", f"{recall:.0%}" if isinstance(recall, (int, float)) else "n/a")
    d.metric("Extra candidates", seeded.get("extra_candidate_events", "n/a"))
    tol = seeded.get("time_tolerance_s")
    if tol is not None:
        st.caption(f"An event counts as matched when it falls within {tol:g} s of an expected one. "
                   "Extra candidates are screening output with no seeded counterpart; review them rather than discard them.")
else:
    st.caption("This run has no seeded scenarios.")

# --- SUMO SSM -------------------------------------------------------------
st.subheader("Reference comparison (SUMO SSM)")
ssm = validation.get("ssm_comparison", {})
if not ssm or not ssm.get("ssm_encounters"):
    st.caption("No SUMO surrogate-safety encounters are available, so no TTC/PET agreement can be reported.")
else:
    a, b, c = st.columns(3)
    a.metric("SSM encounters", ssm["ssm_encounters"])
    matched = ssm.get("matched_events", {})
    b.metric("Matched TTC", matched.get("TTC", 0))
    c.metric("Matched PET", matched.get("PET", 0))
    mae = {k: v for k, v in ssm.get("mean_absolute_error_s", {}).items() if v is not None}
    if mae:
        st.dataframe(pd.DataFrame({"Indicator": list(mae), "Mean absolute error (s)": list(mae.values())}),
                     hide_index=True, **STRETCH)

# --- Detection ------------------------------------------------------------
st.subheader("Detector metrics")
det = validation.get("detection_metrics", {})
if det:
    st.dataframe(pd.DataFrame([det]).rename(columns=pretty), hide_index=True, **STRETCH)
else:
    st.caption("No detector comparison is attached. Ground-truth tracks were used for this run.")

src = validation.get("source_comparison", {})
if src and src.get("comparisons"):
    st.subheader("Source comparison")
    st.json(src["comparisons"], expanded=False)

with st.expander("Raw validation JSON"):
    st.json(validation)
