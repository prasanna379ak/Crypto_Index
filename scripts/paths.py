# scripts/paths.py
from pathlib import Path

# =========================
# EXISTING LOGIC (UNCHANGED)
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

SNAPSHOTS_DIR = BASE_DIR / "snapshots"
EVAL_ROOT = BASE_DIR / "ares_eval"

SNAPSHOTS_DIR.mkdir(exist_ok=True)
EVAL_ROOT.mkdir(exist_ok=True)


def current_run_id():
    run_file = BASE_DIR / "CURRENT_RUN.txt"
    if not run_file.exists():
        raise RuntimeError("CURRENT_RUN.txt not found. Run snapshot_fetcher first.")
    return run_file.read_text().strip()


def snapshot_dir(run_id=None):
    if run_id is None:
        run_id = current_run_id()
    path = SNAPSHOTS_DIR / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def eval_dir(run_id=None):
    if run_id is None:
        run_id = current_run_id()
    path = EVAL_ROOT / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


# Config paths
CONFIG_DIR = BASE_DIR / "config"
STATE_FILE = CONFIG_DIR / "state.json"

# Ares / exclusions
ARES_DIR = BASE_DIR / "ares"
EXCLUSIONS_DIR = ARES_DIR / "exclusions"
OVERRIDE_FILE = EXCLUSIONS_DIR / "human_override.yaml"

# Index data
INDEX_DATA_DIR = BASE_DIR / "index_data"
ACTIVE_COINS_FILE = INDEX_DATA_DIR / "coins_active.csv"
