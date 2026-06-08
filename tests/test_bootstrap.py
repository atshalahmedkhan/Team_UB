"""Test the bootstrap runner in a no-network dry mode."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_bootstrap_noop(tmp_path: Path) -> None:
    """Ensure the bootstrap script runs and exits cleanly when skips are set."""
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "bootstrap_historical.py"
    # Run with both skips to avoid network calls
    result = subprocess.run([sys.executable, str(script), "--skip-edgar", "--skip-macro"], capture_output=True, text=True)
    assert result.returncode == 0
    assert (
        "Bootstrap complete" in result.stdout
        or "No pipelines requested" in result.stdout
    )


def test_bootstrap_only_fingerprint_flag() -> None:
    """--only-fingerprint should attempt fingerprint step without macro/EDGAR."""
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "bootstrap_historical.py"
    result = subprocess.run(
        [sys.executable, str(script), "--only-fingerprint", "--skip-macro", "--skip-edgar"],
        capture_output=True,
        text=True,
    )
    # Exits 0 when Mongo available; 1 when MONGO_URI missing — either is acceptable in CI.
    assert result.returncode in (0, 1)
    assert "PCA fingerprint encoder" in result.stdout or "Could not connect to MongoDB" in result.stdout
