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
entry_caps = dict(zip(df["symbol"].str.lower(), df["entry_market_cap"]))


# --------------------------------------------------
# Load CoinGecko coin list (ONCE)
# --------------------------------------------------

print("Loading CoinGecko coin list...")
coin_list = safe_get_json(
    "https://api.coingecko.com/api/v3/coins/list"
)


symbol_to_ids = {}
for coin in coin_list:
    symbol_to_ids.setdefault(coin["symbol"].lower(), []).append(coin["id"])

# --------------------------------------------------
# Collect ALL candidate IDs (deduplicated)
# --------------------------------------------------

all_candidate_ids = set()
for sym in symbols:
    ids = symbol_to_ids.get(sym)
    if not ids:
        raise RuntimeError(f"No CoinGecko IDs found for symbol: {sym}")
    all_candidate_ids.update(ids)

print(f"Fetching market data for {len(all_candidate_ids)} candidate IDs...")

# --------------------------------------------------
# Fetch market caps in ONE request
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
    entry_cap = row["entry_market_cap"]

    candidates = symbol_to_ids[sym]

    best_id = None
    best_diff = float("inf")
    best_cap = None

    for cid in candidates:
        cap = id_to_cap.get(cid)
        if cap is None:
            continue
        diff = abs(cap - entry_cap) / entry_cap
        if diff < best_diff:
            best_diff = diff
            best_id = cid
            best_cap = cap

    if best_id is None or best_diff > 0.30:
        raise RuntimeError(
            f"Failed to resolve market cap for {row['symbol']} "
            f"(entry={entry_cap})"
        )

    rows.append({
        "symbol": row["symbol"],
        "rank": row["rank"],
        "weight": row["weight"],
        "entry_market_cap": entry_cap,
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
