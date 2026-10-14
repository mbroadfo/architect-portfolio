"""LOCAL-ONLY: shared setup for the slice check's unit tests (Codex review R1 and R3).

Nothing here runs Docker, a browser or a network call: the command runner is replaced by a
recorder that answers with canned output.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

for directory in (REPO_ROOT / "local", REPO_ROOT / "scripts"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
