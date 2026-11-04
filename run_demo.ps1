$ErrorActionPreference = 'Stop'
python -m pip install -e .
python examples/generate_sample.py
python -m vision_zero.cli analyze examples/sample_tracks.csv --expected-events-csv examples/expected_events.csv --out outputs --run-id seeded-demo
streamlit run app/Home.py
