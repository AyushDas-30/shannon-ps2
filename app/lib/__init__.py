"""Make the vision_zero package (under ../src) importable without pip-installing it.

Hosted runtimes (Streamlit Community Cloud) install only requirements.txt, so the
dashboard adds the repo's src/ folder to sys.path before any vision_zero import.
"""
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
