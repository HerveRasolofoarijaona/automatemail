import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False):
        # EXE
        return Path(sys._MEIPASS) / relative_path
    # DEV
    return Path(__file__).parent.parent / relative_path
