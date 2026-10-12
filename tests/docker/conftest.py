"""Shared setup for the Docker-level regression tests (Codex review R1).

These tests drive real Docker. They run only through the ``verify-docker-isolation`` check
(``scripts/verify.py``), which requires Docker and applies only where the verification stack's
Compose files exist.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
