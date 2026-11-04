"""Privacy and neutral-language safeguards for generated assets."""

import re
from pathlib import Path


BLAME_TERMS = re.compile(
    r"\b(fault|cause|violation|reckless|jaywalking|illegal|at fault|culprit|victim)\b",
    re.IGNORECASE,
)


def check_neutral_text(text: str) -> list[str]:
    return sorted({match.group(0).lower() for match in BLAME_TERMS.finditer(text)})


def require_neutral_text(text: str, *, context: str = "generated text") -> None:
    found = check_neutral_text(text)
    if found:
        raise ValueError(f"Restricted wording in {context}: {', '.join(found)}")


def require_safe_evidence(path: str | Path, *, safe_root: str | Path) -> Path:
    """Allow only pre-redacted assets stored under the designated evidence folder."""
    asset = Path(path).resolve()
    root = Path(safe_root).resolve()
    if root not in asset.parents:
        raise ValueError("Evidence must come from the approved redacted output folder")
    if not asset.is_file():
        raise FileNotFoundError(asset)
    return asset
