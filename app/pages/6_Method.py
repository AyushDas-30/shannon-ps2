import pandas as pd
import streamlit as st

from lib.data import current_run
from lib.ui import STRETCH, page

page("Method and limitations", "📐", "How to read the results")
run_id, run = current_run()
config = run.get("config", {}) if run_id else {}

st.markdown(
    "The pipeline reads **precomputed** tracks and events. The dashboard never runs detection or simulation.")

with st.expander("Indicators", expanded=True):
    st.markdown(
        "- **TTC** (time to collision): short-horizon, constant-velocity estimate from observed metric "
        "positions and buffered road-user footprints.\n"
        "- **PET** (post-encroachment time): applies only to tracks that traverse a configured shared conflict zone.\n"
        "- **DRAC**: deceleration needed to avoid the encounter, compared with a reference threshold.")

if config.get("thresholds"):
    with st.expander("Thresholds used in this run", expanded=True):
        names = {"ttc_s": "TTC (s)", "pet_s": "PET (s)", "drac_mps2": "DRAC (m/s²)"}
        st.dataframe(pd.DataFrame([{"Indicator": names.get(k, k), "Threshold": v}
                                   for k, v in config["thresholds"].items()]), hide_index=True, **STRETCH)
        for source in config.get("threshold_sources", []):
            st.markdown(f"Source: [{source['name']}]({source['url']}) ({', '.join(source.get('values', []))})")

with st.expander("Reading the results", expanded=True):
    st.markdown(
        "- Metric outputs require a shared, calibrated coordinate system.\n"
        "- Counts need observation coverage and exposure context.\n"
        "- No observed event is not evidence of a safe location.\n"
        "- Results are candidate review areas for road engineering. They do not describe intent or responsibility.")
