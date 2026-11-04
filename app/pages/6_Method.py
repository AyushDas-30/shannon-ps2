import streamlit as st

st.title("Method and limitations")
st.write("The pipeline reads precomputed tracks and events. It does not run detection or simulation in the dashboard.")
st.write("TTC estimates use short-horizon motion and buffered road-user footprints. PET applies only to tracks that traverse a configured shared conflict zone.")
st.write("Metric outputs require a shared calibrated coordinate system. Counts need observation coverage and exposure context. No observed event is not evidence of a safe location.")
st.write("Results are candidate review areas for road engineering. They do not describe intent or responsibility.")
