"""Shared look-and-feel helpers for the Vision Zero review dashboard."""
from __future__ import annotations

import streamlit as st

ACCENT = "#0f766e"
CATEGORY_COLORS = ["#0f766e", "#d97706", "#2563eb", "#9333ea", "#dc2626", "#64748b"]

PAGES = [
    ("pages/1_Detection.py", "Detection review", "🎥", "Tracks, class mix and redacted evidence frames"),
    ("pages/2_Event_Explorer.py", "Event explorer", "🔎", "Step through each candidate event and its indicator"),
    ("pages/3_Hotspot_Map.py", "Hotspot review", "🗺️", "Ranked review areas on a map or metric grid"),
    ("pages/4_Patterns.py", "Conflict patterns", "📊", "Pattern mix, timing and threshold sensitivity"),
    ("pages/5_Validation.py", "Validation", "✅", "Seeded-scenario recall and reference comparisons"),
    ("pages/6_Method.py", "Method and limits", "📐", "Indicators, thresholds and how to read results"),
    ("pages/7_Report_Export.py", "Report and export", "📄", "Engineer summary and downloads"),
    ("pages/8_What_If.py", "Scenario comparison", "🔀", "Compare a baseline run with a changed design"),
]

FLAG_LABELS = {
    "constant_velocity_screening_estimate": "Constant-velocity screening estimate",
    "overlap_at_observation_unresolved": "Footprints already overlap at observation, so the indicator is unresolved",
    "low_exposure": "Low exposure: too few observed road users for a stable rate",
}

_CSS = """
<style>
.block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1280px;}
h1 {letter-spacing: -0.02em;}
[data-testid="stMetric"] {
    background: rgba(15,118,110,0.06);
    border: 1px solid rgba(15,118,110,0.18);
    border-radius: 12px;
    padding: 0.85rem 1rem;
}
[data-testid="stMetricLabel"] p {font-size: 0.82rem; opacity: 0.8;}
.vz-chip {
    display: inline-block; padding: 0.15rem 0.6rem; margin: 0 0.35rem 0.35rem 0;
    border-radius: 999px; font-size: 0.78rem; font-weight: 500;
    background: rgba(15,118,110,0.12); color: inherit; border: 1px solid rgba(15,118,110,0.3);
}
.vz-chip.warn {background: rgba(217,119,6,0.14); border-color: rgba(217,119,6,0.4);}
.vz-sub {opacity: 0.75; margin-top: -0.6rem; margin-bottom: 1rem;}
</style>
"""


def stretch() -> dict:
    """Keyword that makes a widget fill its container on current and older Streamlit."""
    major_minor = tuple(int(p) for p in st.__version__.split(".")[:2])
    return {"width": "stretch"} if major_minor >= (1, 50) else {"use_container_width": True}


STRETCH = stretch()


def page(title: str, icon: str, subtitle: str | None = None) -> None:
    """Configure the page and draw a consistent header. Call first on every page."""
    st.set_page_config(page_title=f"{title} · Vision Zero", page_icon=icon, layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    st.title(f"{icon} {title}")
    if subtitle:
        st.markdown(f"<div class='vz-sub'>{subtitle}</div>", unsafe_allow_html=True)


def chips(labels: list[str], warn: bool = False) -> None:
    css = "vz-chip warn" if warn else "vz-chip"
    html = "".join(f"<span class='{css}'>{label}</span>" for label in labels)
    st.markdown(html, unsafe_allow_html=True)


def pretty(name: str) -> str:
    return str(name).replace("_", " ").strip().capitalize()


def split_flags(value) -> list[str]:
    if value is None or (isinstance(value, float) and value != value):
        return []
    return [part for part in str(value).replace(",", ";").split(";") if part.strip()]


def explain_flag(flag: str) -> str:
    return FLAG_LABELS.get(flag.strip(), pretty(flag))


def style_fig(fig, height: int = 360):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        colorway=CATEGORY_COLORS,
    )
    return fig


def empty_state(message: str, hint: str | None = None) -> None:
    with st.container(border=True):
        st.markdown(f"**{message}**")
        if hint:
            st.caption(hint)
