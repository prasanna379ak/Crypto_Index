import pandas as pd
from pathlib import Path
from paths import snapshot_dir, eval_dir


snap = snapshot_dir()
out = eval_dir()

out.mkdir(parents=True, exist_ok=True)

raw = pd.read_json(snap / "coingecko.json")

df = pd.DataFrame({
    "symbol": raw["symbol"].str.upper(),
    "market_cap": raw["market_cap"]
})

df.dropna(inplace=True)
df.to_csv(out / "coingecko_normalized.csv", index=False)

print("CoinGecko normalization complete")
