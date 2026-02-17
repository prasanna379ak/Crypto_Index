import subprocess
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone


# --------------------------------------------------
# Paths
# --------------------------------------------------


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "index_data"
DATA_DIR.mkdir(exist_ok=True)

MARKETCAP_FILE = DATA_DIR / "latest_marketcaps.csv"
HISTORY_FILE = DATA_DIR / "index_history.csv"
STATE_FILE = DATA_DIR / "index_state.json"

PY = sys.executable
BASE_INDEX_VALUE = 1000.0


# --------------------------------------------------
# Dashboard output (docs for GitHub Pages)
# --------------------------------------------------

DOCS_DATA_DIR = BASE_DIR / "docs" / "data"
DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)

DASHBOARD_JSON = DOCS_DATA_DIR / "index_timeseries.json"
CONSTITUENTS_JSON = DOCS_DATA_DIR / "constituents.json"



# --------------------------------------------------
# Step 1: Collect latest market caps
# --------------------------------------------------

print("\n▶ Collecting market caps...")
subprocess.run(
    [PY, "scripts/collect_top10_marketcap.py"],
    check=True
)

df = pd.read_csv(MARKETCAP_FILE)

required_cols = {"symbol", "weight", "market_cap"}
if not required_cols.issubset(df.columns):
    raise RuntimeError("Market cap file missing required columns")

# --------------------------------------------------
# Step 2: Calculate RAW index value
# --------------------------------------------------

raw_value = (df["weight"] * df["market_cap"]).sum()

timestamp = datetime.now(timezone.utc).isoformat()

# --------------------------------------------------
# Step 3: Load or initialize divisor
# --------------------------------------------------

if not STATE_FILE.exists():
    # First-ever index launch
    divisor = raw_value / BASE_INDEX_VALUE

    state = {
        "base_value": BASE_INDEX_VALUE,
        "divisor": divisor,
        "created_at": timestamp
    }

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    print("\nIndex initialized at base value 1000")

else:
    with open(STATE_FILE) as f:
        state = json.load(f)

    divisor = state["divisor"]

    # Safety check
    if divisor <= 0:
        raise RuntimeError("Invalid divisor detected")


# --------------------------------------------------
# Step 4: Calculate normalized index value
# --------------------------------------------------

index_value = raw_value / divisor

row = {
    "timestamp_utc": timestamp,
    "raw_value": float(raw_value),
    "index_value": float(index_value)
}

# --------------------------------------------------
# Step 5: Persist history
# --------------------------------------------------

if HISTORY_FILE.exists():
    hist = pd.read_csv(HISTORY_FILE)
    hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
else:
    hist = pd.DataFrame([row])

hist.to_csv(HISTORY_FILE, index=False)



# --------------------------------------------------
# Step 6: Update dashboard JSON (append-only)
# --------------------------------------------------

dashboard_entry = {
    "time": timestamp,
    "value": round(float(index_value), 6)
}

if DASHBOARD_JSON.exists():
    with open(DASHBOARD_JSON, "r") as f:
        dashboard_data = json.load(f)
else:
    dashboard_data = {
        "symbol": "CRYP_INDEX",
        "interval": "30m",
        "last_updated": timestamp,
        "data": []
    }

# Append new point
dashboard_data["data"].append(dashboard_entry)
dashboard_data["last_updated"] = timestamp

# Optional: keep file from growing forever (e.g. last 2000 points)
MAX_POINTS = 2000
if len(dashboard_data["data"]) > MAX_POINTS:
    dashboard_data["data"] = dashboard_data["data"][-MAX_POINTS:]

with open(DASHBOARD_JSON, "w") as f:
    json.dump(dashboard_data, f, indent=2)



# --------------------------------------------------
# Step 6.5: Update constituents JSON (for dashboard)
# --------------------------------------------------

# Normalize weights defensively (in case upstream changes)
weight_sum = df["weight"].sum()
if weight_sum <= 0:
    raise RuntimeError("Invalid weights: sum is zero or negative")

constituents_payload = {
    "as_of": timestamp,
    "method": "free-float market cap",
    "constituents": []
}

for _, row_df in df.iterrows():
    normalized_weight = float(row_df["weight"] / weight_sum)

    constituents_payload["constituents"].append({
        "symbol": row_df["symbol"],
        "weight": round(normalized_weight, 4),
        "market_cap": float(row_df["market_cap"])
    })

# Optional safety check (recommended, silent in production)
total_weight = sum(c["weight"] for c in constituents_payload["constituents"])
if abs(total_weight - 1.0) > 1e-6:
    raise RuntimeError(f"Constituent weights do not sum to 1.0 (sum={total_weight})")

with open(CONSTITUENTS_JSON, "w") as f:
    json.dump(constituents_payload, f, indent=2)



# --------------------------------------------------
# Output
# --------------------------------------------------

print("\n==============================")
print("INDEX VALUE CALCULATED")
print("==============================")
print(f"Timestamp (UTC): {timestamp}")
print(f"Raw value      : {int(raw_value)}")
print(f"Index value    : {round(index_value, 4)}")
print(f"Divisor        : {divisor}")
print(f"Saved to       : {HISTORY_FILE}")