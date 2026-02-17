import json
import pandas as pd
from paths import snapshot_dir, eval_dir

snap = snapshot_dir()
out = eval_dir()

out.mkdir(parents=True, exist_ok=True)

with open(snap / "coinpaprika.json", "r") as f:
    raw = json.load(f)

rows = []
for x in raw:
    quotes = x.get("quotes", {})
    usd = quotes.get("USD")
    if not usd:
        continue

    rows.append({
        "symbol": x["symbol"].upper(),
        "market_cap": usd.get("market_cap")
    })

df = pd.DataFrame(rows)
df = df.sort_values("market_cap", ascending=False).head(50)
df.to_csv(out / "coinpaprika_normalized.csv", index=False)
print("CoinPaprika normalization complete")
print("Assets:", len(df))
