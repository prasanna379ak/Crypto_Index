import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE = Path(__file__).resolve().parent.parent
RUN_ID = (BASE / "CURRENT_RUN.txt").read_text().strip()

TOP10 = BASE / "ares_eval" / RUN_ID / "top10.csv"

OUT_DIR = BASE / "index_data"
OUT_DIR.mkdir(exist_ok=True)

OUT_FILE = OUT_DIR / "latest_marketcaps.csv"


# --------------------------------------------------
# Helper
# --------------------------------------------------

def safe_get_json(url, params=None, timeout=30):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            raise ValueError("Unexpected JSON structure")
        return data
    except Exception as e:
        raise RuntimeError(f"CoinGecko fetch failed: {e}")


# --------------------------------------------------
# Load top10 portfolio
# --------------------------------------------------

df = pd.read_csv(TOP10)

symbols = df["symbol"].str.lower().tolist()

# --------------------------------------------------
# Load CoinGecko coin list
# --------------------------------------------------

print("Loading CoinGecko coin list...")
coin_list = safe_get_json(
    "https://api.coingecko.com/api/v3/coins/list"
)

symbol_to_ids = {}
for coin in coin_list:
    symbol_to_ids.setdefault(coin["symbol"].lower(), []).append(coin["id"])

# --------------------------------------------------
# Collect ALL candidate IDs
# --------------------------------------------------

all_candidate_ids = set()

for sym in symbols:
    ids = symbol_to_ids.get(sym)
    if not ids:
        raise RuntimeError(f"No CoinGecko IDs found for symbol: {sym}")
    all_candidate_ids.update(ids)

print(f"Fetching market data for {len(all_candidate_ids)} candidate IDs...")

# --------------------------------------------------
# Fetch market caps
# --------------------------------------------------

market_data = safe_get_json(
    "https://api.coingecko.com/api/v3/coins/markets",
    params={
        "vs_currency": "usd",
        "ids": ",".join(all_candidate_ids),
        "per_page": 250,
        "page": 1
    }
)

if not market_data:
    raise RuntimeError("No market data returned from CoinGecko")

# Build ID → market_cap map

id_to_cap = {
    c["id"]: c["market_cap"]
    for c in market_data
    if c.get("market_cap") is not None
}

# --------------------------------------------------
# Resolve best ID per symbol
# --------------------------------------------------

rows = []

for _, row in df.iterrows():
    sym = row["symbol"].lower()
    candidates = symbol_to_ids[sym]

    best_id = None
    best_cap = None

    for cid in candidates:
        cap = id_to_cap.get(cid)
        if cap is None:
            continue

        # Choose the candidate with the highest market cap
        if best_cap is None or cap > best_cap:
            best_cap = cap
            best_id = cid

    if best_id is None:
        raise RuntimeError(
            f"Failed to resolve market cap for {row['symbol']}"
        )

    rows.append({
        "symbol": row["symbol"],
        "rank": row["rank"],
        "weight": row["weight"],
        "entry_market_cap": row["entry_market_cap"],
        "market_cap": best_cap
    })

# --------------------------------------------------
# Output
# --------------------------------------------------

out = pd.DataFrame(rows)
out["timestamp_utc"] = datetime.now(timezone.utc).isoformat()

out.to_csv(OUT_FILE, index=False)

print("\nMarket caps collected successfully:")
for _, r in out.iterrows():
    print(f"{r['symbol']}  market_cap={int(r['market_cap'])}")

print(f"\nSaved to: {OUT_FILE}")
