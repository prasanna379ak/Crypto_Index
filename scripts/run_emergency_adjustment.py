import subprocess
import sys
import json
import hashlib
import os
import yaml
from pathlib import Path
from datetime import datetime, timezone

PY = sys.executable
BASE = Path(__file__).resolve().parent.parent

INDEX_DATA = BASE / "index_data"
INDEX_DATA.mkdir(exist_ok=True)

EMERGENCY_LOCK = INDEX_DATA / "emergency.lock"
EMERGENCY_LOG = INDEX_DATA / "emergency_events.jsonl"

STATE_FILE = INDEX_DATA / "index_state.json"
HISTORY_FILE = INDEX_DATA / "index_history.csv"
MARKETCAP_FILE = INDEX_DATA / "latest_marketcaps.csv"

HUMAN_OVERRIDE = BASE / "ares/exclusions/human_override.yaml"

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
# Helpers
# --------------------------------------------------

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_env_override():
    if os.environ.get("ALLOW_EMERGENCY_ADJUSTMENT") != "1":
        raise RuntimeError(
            "Emergency adjustment requires explicit approval.\n"
            "Set ALLOW_EMERGENCY_ADJUSTMENT=1 to proceed."
        )


def load_last_override_hash():
    if not EMERGENCY_LOCK.exists():
        return None
    with open(EMERGENCY_LOCK) as f:
        return json.load(f).get("override_hash")


def validate_human_override():
    if not HUMAN_OVERRIDE.exists():
        raise RuntimeError("human_override.yaml not found")

    data = yaml.safe_load(HUMAN_OVERRIDE.read_text()) or {}
    blacklist = data.get("blacklist")

    if not blacklist or not isinstance(blacklist, list):
        raise RuntimeError("Emergency adjustment requires at least one blacklist entry")

    symbols = []
    for entry in blacklist:
        if not all(k in entry for k in ("symbol", "reason", "timestamp")):
            raise RuntimeError(
                "Each blacklist entry must include symbol, reason, timestamp"
            )
        symbols.append(entry["symbol"])

    return symbols


# --------------------------------------------------
# Main
# --------------------------------------------------

def run():
    print("\n====================================")
    print("== EMERGENCY ADJUSTMENT INITIATED ==")
    print("====================================\n")

    require_env_override()

    affected_symbols = validate_human_override()

    current_hash = sha256(HUMAN_OVERRIDE)
    last_hash = load_last_override_hash()

    if current_hash == last_hash:
        raise RuntimeError(
            "No change detected in human_override.yaml.\n"
            "Emergency adjustment aborted."
        )

    print("Human override change detected")
    print("Affected symbols:", ", ".join(affected_symbols))

    # --------------------------------------------------
    # Full rebalance pipeline (no time window, no lock)
    # --------------------------------------------------

    for step in STEPS:
        print(f"▶ Running: {step}")
        subprocess.run([PY, step], check=True)

    # --------------------------------------------------
    # Collect market caps for continuity
    # --------------------------------------------------

    subprocess.run(
        [PY, "scripts/collect_top10_marketcap.py"],
        check=True
    )

    # --------------------------------------------------
    # Apply continuity
    # --------------------------------------------------

    from run_rebalance import apply_continuity
    apply_continuity()

    # --------------------------------------------------
    # Audit log
    # --------------------------------------------------

    event = {
        "type": "emergency_adjustment",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "affected_symbols": affected_symbols,
        "override_hash": current_hash
    }

    with open(EMERGENCY_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")

    # --------------------------------------------------
    # Lock emergency state
    # --------------------------------------------------

    with open(EMERGENCY_LOCK, "w") as f:
        json.dump(
            {
                "override_hash": current_hash,
                "timestamp": event["timestamp"]
            },
            f,
            indent=2
        )

    print("\n====================================")
    print("EMERGENCY ADJUSTMENT COMPLETE")
    print("Index continuity preserved")
    print("Next scheduled rebalance unchanged")
    print("====================================")


if __name__ == "__main__":
    run()
