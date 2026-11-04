import streamlit as st

from lib.data import current_run, source_banner
from vision_zero.privacy import require_safe_evidence

st.title("Detection review")
run_id, run = current_run()
if run_id:
    source_banner(run_id, run)
    tracks = run["tracks"]
    if tracks.empty:
        st.info("No track table is available for this run.")
    else:
        st.dataframe(tracks.head(500), use_container_width=True)
        if "class_group" in tracks:
            st.bar_chart(tracks["class_group"].value_counts())
    media = __import__("pathlib").Path(run["root"]) / "evidence_safe"
    if media.exists():
        for image in sorted(media.glob("*.jpg"))[:20]:
            st.image(str(require_safe_evidence(image, safe_root=media)), use_container_width=True)
        for video in sorted(media.glob("*.mp4"))[:2]:
            st.video(str(require_safe_evidence(video, safe_root=media)))
    st.caption("Only pre-rendered non-identifying evidence is displayed.")
