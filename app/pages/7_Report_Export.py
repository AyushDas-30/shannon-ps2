from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from lib.data import current_run, source_banner
from lib.ui import STRETCH, empty_state, page

page("Report and export", "📄", "Engineer summary and data downloads")
run_id, run = current_run()
if not run_id:
    st.stop()
source_banner(run_id, run)

root = Path(run["root"])
summary, html_report = root / "engineer_summary.md", root / "engineer_report.html"

downloads = [
    (summary, "Markdown summary", "text/markdown", f"{run_id}-summary.md"),
    (html_report, "HTML report", "text/html", "engineer_report.html"),
    (root / "engineer_report.pdf", "PDF report", "application/pdf", "engineer_report.pdf"),
    (root / "events.csv", "Events (CSV)", "text/csv", "events.csv"),
    (root / "hotspots.csv", "Hotspots (CSV)", "text/csv", "hotspots.csv"),
    (root / "hotspots.geojson", "Hotspots (GeoJSON)", "application/geo+json", "hotspots.geojson"),
]
available = [d for d in downloads if d[0].exists()]

tab_preview, tab_html, tab_files = st.tabs(["Summary", "HTML report", "Downloads"])
with tab_preview:
    if summary.exists():
        st.markdown(summary.read_text(encoding="utf-8"))
    else:
        empty_state("No engineer summary is attached to this run.")
with tab_html:
    if html_report.exists():
        if hasattr(st, "iframe"):
            st.iframe(html_report, height=700)
        else:
            components.html(html_report.read_text(encoding="utf-8"), height=700, scrolling=True)
    else:
        empty_state("No HTML report is attached to this run.")
with tab_files:
    if not available:
        empty_state("No exportable files were found for this run.")
    cols = st.columns(3)
    for i, (path, label, mime, name) in enumerate(available):
        with cols[i % 3].container(border=True):
            st.markdown(f"**{label}**")
            st.caption(f"{path.stat().st_size / 1024:.1f} KB")
            st.download_button("Download", path.read_bytes(), file_name=name, mime=mime,
                               key=f"dl_{name}", **STRETCH)
