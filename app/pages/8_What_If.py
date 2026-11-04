import streamlit as st
import pandas as pd

from lib.data import list_runs, load_run

st.title("Scenario comparison")
runs = list_runs()
if len(runs) < 2:
    st.info("Add a baseline run and a changed-design run to compare results.")
else:
    baseline_id, changed_id = st.columns(2)
    base = baseline_id.selectbox("Baseline run", runs, key="base")
    changed = changed_id.selectbox("Changed run", runs, key="changed")
    left, right = load_run(base), load_run(changed)
    st.metric("Candidate event change", len(right["events"]) - len(left["events"]))
    st.dataframe(pd.DataFrame({"run": [base, changed], "events": [len(left["events"]), len(right["events"])]}))
