import streamlit as st

from lib.data import current_run, source_banner

st.title("Hotspot review")
run_id, run = current_run()
if run_id:
    source_banner(run_id, run)
    hotspots = run["hotspots"]
    geojson = __import__("pathlib").Path(run["root"]) / "hotspots.geojson"
    if geojson.exists():
        import folium
        from streamlit_folium import st_folium
        data = __import__("json").loads(geojson.read_text(encoding="utf-8"))
        locations = [f["geometry"]["coordinates"][::-1] for f in data.get("features", [])]
        center = locations[0] if locations else [0, 0]
        fmap = folium.Map(location=center, zoom_start=14, tiles="OpenStreetMap")
        folium.GeoJson(data, name="candidate events").add_to(fmap)
        st_folium(fmap, use_container_width=True, height=520)
    else:
        st.info("This run has no geographic registration. Showing metric grid cells instead.")
    st.dataframe(hotspots, use_container_width=True)
    events = run["events"]
    if not hotspots.empty and {"cell_x", "cell_y"}.issubset(hotspots.columns):
        cells = [f"{row.cell_x},{row.cell_y}" for row in hotspots.itertuples()]
        selected = st.selectbox("Open review area", cells)
        x_cell, y_cell = map(int, selected.split(","))
        if not events.empty and {"x_m", "y_m"}.issubset(events.columns):
            st.subheader("Events in selected area")
            cell_size = run.get("config", {}).get("cell_size_m", 25)
            st.dataframe(events[(events.x_m // cell_size == x_cell) & (events.y_m // cell_size == y_cell)], use_container_width=True)
