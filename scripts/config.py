"""
Configuration and constants for the AI Tools Radar
"""
import os
from pathlib import Path
import yaml

# Paths
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
TOOLS_FILE = ROOT_DIR / "tools.yaml"
FRONTEND_DATA_FILE = ROOT_DIR / "frontend" / "public" / "data.json"

# Ensure directories exist
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

# API Configuration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Rate limiting
REQUEST_DELAY = 1.0  # seconds between requests


def load_tools() -> list[dict]:
    """Load seed tools from tools.yaml (optional)."""
    if not TOOLS_FILE.exists():
        return []
    with open(TOOLS_FILE) as f:
        data = yaml.safe_load(f)
    return data.get("tools", [])
