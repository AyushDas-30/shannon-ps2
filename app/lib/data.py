from __future__ import annotations

import json
from pathlib import Path
from vision_zero.privacy import check_neutral_text, require_safe_evidence

import pandas as pd
import streamlit as st


RUNS_ROOT = Path(__file__).resolve().parents[2] / "outputs" / "runs"


@st.cache_data
def list_runs() -> list[str]:
    return sorted(p.name for p in RUNS_ROOT.iterdir() if p.is_dir()) if RUNS_ROOT.exists() else []


@st.cache_data
def load_run(run_id: str) -> dict:
    root = RUNS_ROOT / run_id
    if not root.exists():
        return {"root": str(root), "tracks": pd.DataFrame(), "events": pd.DataFrame(),
                "hotspots": pd.DataFrame(), "validation": {}, "config": {}}
    def read_frame(stem: str) -> pd.DataFrame:
        parquet = root / f"{stem}.parquet"
        csv_path = root / f"{stem}.csv"
        if parquet.exists():
            return pd.read_parquet(parquet)
        return pd.read_csv(csv_path) if csv_path.exists() else pd.DataFrame()
    def read_json(name: str) -> dict:
        path = root / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return {
        "root": str(root),
        "tracks": read_frame("tracks"),
        "events": read_frame("events"),
        "hotspots": read_frame("hotspots"),
        "validation": read_json("validation.json"),
        "config": read_json("config.json"),
    }


def current_run() -> tuple[str | None, dict]:
    _check_app_copy()
    runs = list_runs()
    if not runs:
        st.info("No precomputed run is available yet. Create one with the offline pipeline.")
        return None, {}
    run_id = st.sidebar.selectbox("Run", runs, index=len(runs) - 1)
    run = load_run(run_id)
    _check_run_text(run)
    source = run.get("config", {}).get("source_type", "unknown source")
    st.sidebar.caption(f"Source: {source} · Run: {run_id}")
    return run_id, run


def _check_app_copy() -> None:
    app_root = Path(__file__).resolve().parents[1]
    violations = []
    for source in app_root.rglob("*.py"):
        violations.extend((str(source), term) for term in check_neutral_text(source.read_text(encoding="utf-8")))
    if violations:
        raise ValueError(f"Restricted wording found in dashboard copy: {violations}")


def _check_run_text(run: dict) -> None:
    for name, frame in run.items():
        if hasattr(frame, "select_dtypes"):
            for value in frame.select_dtypes(include="object").fillna("").to_numpy().ravel():
                if terms := check_neutral_text(str(value)):
                    raise ValueError(f"Restricted wording in run data ({name}): {terms}")
    config_text = str(run.get("config", {}))
    if terms := check_neutral_text(config_text):
        raise ValueError(f"Restricted wording in run configuration: {terms}")


def source_banner(run_id: str, run: dict) -> None:
    source = run.get("config", {}).get("source_type", "unknown source")
    st.caption(f"Data source: {source} · Run ID: {run_id}")
