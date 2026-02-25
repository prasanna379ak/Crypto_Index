import pandas as pd
import yaml
from pathlib import Path
from paths import eval_dir

BASE = Path(__file__).resolve().parent.parent
EVAL = eval_dir()

# -----------------------------
# Load eligible assets
# -----------------------------

df = pd.read_csv(EVAL / "ares_eligible_assets.csv")

# -----------------------------
# Load exclusion rules
# -----------------------------

auto = yaml.safe_load(open(BASE / "ares/exclusions/exclusions.yaml")) or {}
black = yaml.safe_load(open(BASE / "ares/exclusions/human_override.yaml")) or {}

exclude = set(sum(auto.values(), []))
human = (
    set(x["symbol"] for x in black.get("blacklist", []))
    if isinstance(black.get("blacklist"), list)
    else set()
)

# -----------------------------
# Apply exclusions
# -----------------------------

mask = (
    ~df["symbol"].str.lower().isin(exclude)
    & ~df["symbol"].isin(human)
)

filtered = df[mask].copy()

filtered.to_csv(EVAL / "post_exclusion_assets.csv", index=False)
print("Exclusions applied")
print("Eligible assets after exclusions:", len(filtered))

# -----------------------------
# Rank by market cap
# -----------------------------

ranked = (
    filtered
    .sort_values("market_cap", ascending=False)
    .head(10)
    .reset_index(drop=True)
)

ranked["rank"] = ranked.index + 1

# -----------------------------
# Fixed rank-based weights
# -----------------------------

RANK_WEIGHTS = {
    1: 0.30,
    2: 0.22,
    3: 0.06,
    4: 0.06,
    5: 0.06,
    6: 0.06,
    7: 0.06,
    8: 0.06,
    9: 0.06,
    10: 0.06,
}

ranked["weight"] = ranked["rank"].map(RANK_WEIGHTS)

if ranked["weight"].isnull().any():
    raise RuntimeError("Weight mapping failed for one or more ranks")

# -----------------------------
# Final Top 10 portfolio
# -----------------------------

top10 = ranked[["symbol", "market_cap", "rank", "weight"]].rename(
    columns={"market_cap": "entry_market_cap"}
)

weight_sum = round(top10["weight"].sum(), 6)
if weight_sum != 1.0:
    raise RuntimeError(f"Weights do not sum to 1.0 (sum={weight_sum})")

top10.to_csv(EVAL / "top10.csv", index=False)

print("\nTop 10 index portfolio created:")
for _, r in top10.iterrows():
    print(
        f"Rank {r['rank']} | {r['symbol']} | "
        f"weight={r['weight']} | "
        f"entry_market_cap={int(r['entry_market_cap'])}"
    )