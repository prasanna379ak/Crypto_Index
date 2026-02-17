import subprocess
import sys
import json
import os
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta

# --------------------------------------------------
# Runtime
# --------------------------------------------------

PY = sys.executable
BASE = Path(__file__).resolve().parent.parent

# --------------------------------------------------
# Config
# --------------------------------------------------

REBALANCE_START_HOUR = 13     # UTC
REBALANCE_END_HOUR = 16    # UTC
REBALANCE_PERIOD_DAYS = 14  # Days

INDEX_DATA = BASE / "index_data"
INDEX_DATA.mkdir(exist_ok=True)

LOCK_FILE = INDEX_DATA / "rebalance.lock"
STATE_FILE = INDEX_DATA / "index_state.json"
HISTORY_FILE = INDEX_DATA / "index_history.csv"
MARKETCAP_FILE = INDEX_DATA / "latest_marketcaps.csv"

ARES_EXCLUSIONS = BASE / "ares" / "exclusions"
HUMAN_OVERRIDE = ARES_EXCLUSIONS / "human_override.yaml"
EXCLUSIONS = ARES_EXCLUSIONS / "exclusions.yaml"

STEPS = [
    "scripts/snapshot_fetcher.py",
    "scripts/normalize_coingecko.py",
    "scripts/normalize_coinmarketcap.py",
    "scripts/normalize_coinpaprika.py",
    "scripts/build_presence_matrix.py",
    "scripts/apply_quorum.py",
    "scripts/apply_marketcap_tolerance.py",
    "scripts/apply_exclu_weight_rank.py",
]


# --------------------------------------------------

from datetime import datetime, timezone

now = datetime.now(timezone.utc)
if now.minute in (0, 30):
    print("Unsafe minute (:00 or :30). Skipping rebalance.")
    exit(0)

# --------------------------------------------------



# --------------------------------------------------
# Guards
# --------------------------------------------------

def check_time_window():
    if os.environ.get("ALLOW_MANUAL_REBALANCE") == "1":
        print("⚠ Manual rebalance override enabled (time window bypassed)")
        return datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    if not (REBALANCE_START_HOUR <= now.hour < REBALANCE_END_HOUR):
        raise RuntimeError(
            f"Rebalance allowed only between "
            f"{REBALANCE_START_HOUR}:00–{REBALANCE_END_HOUR}:00 UTC"
        )
    return now


def check_lock():
    if not LOCK_FILE.exists():
        return

    with open(LOCK_FILE) as f:
        lock = json.load(f)

    raise RuntimeError(
        "\nRebalance already executed.\n"
        f"Last rebalance : {lock.get('rebalanced_at')}\n"
        f"Next allowed   : {lock.get('next_allowed_at')}\n"
        "Delete rebalance.lock to force a manual override."
    )


def write_lock(run_id, timestamp):
    next_unlock = timestamp + timedelta(days=REBALANCE_PERIOD_DAYS)
    with open(LOCK_FILE, "w") as f:
        json.dump(
            {
                "run_id": run_id,
                "rebalanced_at": timestamp.isoformat(),
                "next_allowed_at": next_unlock.isoformat(),
            },
            f,
            indent=2,
        )

# --------------------------------------------------
# Emergency consolidation (90-day cleanup)
# --------------------------------------------------

def consolidate_emergency_overrides():
    if not HUMAN_OVERRIDE.exists():
        return

    override = yaml.safe_load(HUMAN_OVERRIDE.read_text()) or {}
    blacklist = override.get("blacklist", [])

    if not blacklist:
        return

    print("▶ Consolidating emergency overrides into exclusions.yaml")

    excl = yaml.safe_load(EXCLUSIONS.read_text()) or {}
    non_utility = set(excl.get("non_utility", []))

    moved = []
    for entry in blacklist:
        symbol = entry.get("symbol")
        if symbol:
            non_utility.add(symbol.lower())
            moved.append(symbol.upper())

    excl["non_utility"] = sorted(non_utility)

    with open(EXCLUSIONS, "w") as f:
        yaml.safe_dump(excl, f, sort_keys=False)

    # Clear override (do NOT delete file)
    with open(HUMAN_OVERRIDE, "w") as f:
        yaml.safe_dump({"blacklist": []}, f)

    print(f"✔ Moved to permanent exclusions: {', '.join(moved)}")
    print("✔ human_override.yaml cleared")

# --------------------------------------------------
# Continuity logic
# --------------------------------------------------

def apply_continuity():
    if not STATE_FILE.exists() or not HISTORY_FILE.exists():
        print("No existing index state found — skipping continuity (index launch).")
        return

    import pandas as pd

    old_index_value = (
        pd.read_csv(HISTORY_FILE)
        .iloc[-1]["index_value"]
    )

    caps = pd.read_csv(MARKETCAP_FILE)
    new_raw_value = (caps["weight"] * caps["market_cap"]).sum()

    new_divisor = new_raw_value / old_index_value

    with open(STATE_FILE) as f:
        state = json.load(f)

    state["divisor"] = new_divisor
    state["last_rebalance_at"] = datetime.now(timezone.utc).isoformat()

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    print("\nRebalance continuity applied")
    print(f"Old index value : {old_index_value}")
    print(f"New raw value   : {new_raw_value}")
    print(f"New divisor     : {new_divisor}")

# --------------------------------------------------
# Main
# --------------------------------------------------

def run():
    print("\n==============================")
    print("===== STARTING REBALANCE =====")
    print("==============================\n")

    now = check_time_window()
    check_lock()

    # 🔑 Consolidation happens ONLY if blacklist still exists
    consolidate_emergency_overrides()

    for step in STEPS:
        print(f"▶ Running: {step}")
        subprocess.run([PY, step], check=True)

    print("▶ Collecting market caps for continuity")
    subprocess.run([PY, "scripts/collect_top10_marketcap.py"], check=True)

    apply_continuity()

    run_id = (BASE / "CURRENT_RUN.txt").read_text().strip()
    write_lock(run_id, now)

    print("\n==============================")
    print("===== REBALANCE COMPLETE =====")
    print("==============================")
    print("Top 10 portfolio created (top10.csv)")
    print("Rebalance locked")


if __name__ == "__main__":
    run()
