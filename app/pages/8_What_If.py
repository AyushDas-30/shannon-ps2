import pandas as pd
import plotly.express as px
import streamlit as st

from lib.data import list_runs, load_run
from lib.ui import STRETCH, empty_state, page, pretty, style_fig

page("Scenario comparison", "🔀", "Compare a baseline run with a changed-design run")
runs = list_runs()
if len(runs) < 2:
    empty_state("Add a baseline run and a changed-design run to compare results.",
                "Place a second run under outputs/runs/<run_id>/ using the offline pipeline.")
    st.stop()

c1, c2 = st.columns(2)
base = c1.selectbox("Baseline run", runs, index=0, key="base")
changed = c2.selectbox("Changed run", runs, index=len(runs) - 1, key="changed")
if base == changed:
    st.warning("Choose two different runs to see a difference.", icon="⚠️")
left, right = load_run(base), load_run(changed)


def min_ttc(run):
    h = run["hotspots"]
    return h["min_ttc_s"].min() if "min_ttc_s" in h and not h.empty else float("nan")


m1, m2, m3 = st.columns(3)
m1.metric("Candidate events", len(right["events"]), delta=len(right["events"]) - len(left["events"]), delta_color="inverse")
m2.metric("Review areas", len(right["hotspots"]), delta=len(right["hotspots"]) - len(left["hotspots"]), delta_color="inverse")
d_ttc = min_ttc(right) - min_ttc(left)
m3.metric("Lowest TTC in a review area (s)", f"{min_ttc(right):.2f}" if min_ttc(right) == min_ttc(right) else "n/a",
          delta=f"{d_ttc:.2f}" if d_ttc == d_ttc else None)
st.caption("For event counts, a decrease is shown as favourable. Compare only runs with similar observation time and exposure.")

if "conflict_type" in left["events"] or "conflict_type" in right["events"]:
    frames = []
    for name, run in ((base, left), (changed, right)):
        if "conflict_type" in run["events"]:
            counts = run["events"]["conflict_type"].map(pretty).value_counts().rename_axis("Pattern").reset_index(name="Events")
            frames.append(counts.assign(Run=name))
    if frames:
        fig = px.bar(pd.concat(frames), x="Pattern", y="Events", color="Run", barmode="group", title="Events by pattern")
        st.plotly_chart(style_fig(fig, 340), **STRETCH)
