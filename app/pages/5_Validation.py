import json
import streamlit as st

from lib.data import current_run, source_banner

st.title("Validation")
run_id, run = current_run()
if run_id:
    source_banner(run_id, run)
    st.json(run.get("validation", {}))
    path = __import__("pathlib").Path(run["root"]) / "validation.json"
    if not path.exists():
        st.info("No validation summary is attached to this run yet.")
