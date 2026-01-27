import pandas as pd
import yaml
from paths import eval_dir

EVAL = eval_dir()
CFG = yaml.safe_load(open("config/engine.yaml"))
TOL = CFG["ares"]["tolerance_percent"] / 100

presence = pd.read_csv(EVAL / "quorum_results.csv")
presence = presence[presence["passes_quorum"] == True]

# Load all normalized providers dynamically
provider_caps = {}
for f in EVAL.glob("*_normalized.csv"):
    provider = f.stem.replace("_normalized", "")
    df = pd.read_csv(f)
    provider_caps[provider] = dict(zip(df["symbol"], df["market_cap"]))

rows = []

for sym in presence["symbol"]:
    caps = [
        cap
        for caps in provider_caps.values()
        if sym in caps
        for cap in [caps[sym]]
    ]

    if len(caps) < 2:
        continue

    base = sorted(caps)[len(caps)//2]  # median
    ok = [
        abs(c - base) / base <= TOL
        for c in caps
    ]

    if sum(ok) >= CFG["ares"]["quorum"]:
        rows.append({
            "symbol": sym,
            "market_cap": base
        })

df = pd.DataFrame(rows)
df = df.sort_values("market_cap", ascending=False)

df.to_csv(EVAL / "ares_eligible_assets.csv", index=False)

print("Market-cap tolerance applied")
print("Validated assets:", len(df))
