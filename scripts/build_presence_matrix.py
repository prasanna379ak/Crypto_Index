import pandas as pd
from paths import eval_dir

EVAL = eval_dir()
files = list(EVAL.glob("*_normalized.csv"))

dfs = []
for f in files:
    provider = f.stem.replace("_normalized", "")
    df = pd.read_csv(f)[["symbol"]].drop_duplicates()
    df[provider] = 1
    dfs.append(df)

out = dfs[0]
for df in dfs[1:]:
    out = out.merge(df, on="symbol", how="outer")

out.fillna(0, inplace=True)
out.to_csv(EVAL / "symbol_presence_matrix.csv", index=False)

print("Presence matrix built")
