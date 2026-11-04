from pathlib import Path

import streamlit as st

from lib.data import current_run, source_banner

st.title("Report and export")
run_id, run = current_run()
if run_id:
    source_banner(run_id, run)
    root = Path(run["root"])
    summary = root / "engineer_summary.md"
    if summary.exists():
        content = summary.read_text(encoding="utf-8")
        st.markdown(content)
        st.download_button("Download Markdown report", content, file_name=f"{run_id}-summary.md")
    for filename, label, mime in (("engineer_report.html", "HTML report", "text/html"),
                                  ("engineer_report.pdf", "PDF report", "application/pdf")):
        target = root / filename
        if target.exists():
            st.download_button(f"Download {label}", target.read_bytes(), file_name=filename, mime=mime)
    for filename, label, mime in (("events.csv", "Event CSV", "text/csv"),
                                  ("hotspots.geojson", "Hotspots GeoJSON", "application/geo+json")):
        target = root / filename
        if target.exists():
            st.download_button(f"Download {label}", target.read_bytes(), file_name=filename, mime=mime)
