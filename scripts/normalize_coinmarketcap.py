import json
import pandas as pd
from paths import snapshot_dir, eval_dir

snap = snapshot_dir()
out = eval_dir()


out.mkdir(parents=True, exist_ok=True)

with open(snap / "coinmarketcap.json", "r") as f:
    raw = json.load(f)

data = raw.get("data", [])

rows = []
for x in data:
    try:
        rows.append({
            "symbol": x["symbol"].upper(),
            "market_cap": x["quote"]["USD"]["market_cap"]
        })
    except KeyError:
        continue

df = pd.DataFrame(rows).dropna()
df.to_csv(out / "coinmarketcap_normalized.csv", index=False)

print("CoinMarketCap normalization complete")
print("Assets:", len(df))
