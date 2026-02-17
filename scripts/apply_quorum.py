import pandas as pd
import yaml
from paths import eval_dir

EVAL = eval_dir()
CFG = yaml.safe_load(open("config/engine.yaml"))

df = pd.read_csv(EVAL / "symbol_presence_matrix.csv")

providers = [c for c in df.columns if c != "symbol"]
active = len(providers)
required = min(CFG["ares"]["quorum"], active)

df["providers_present"] = df[providers].sum(axis=1)
df["passes_quorum"] = df["providers_present"] >= required

df.to_csv(EVAL / "quorum_results.csv", index=False)
print(f"Quorum applied: {required}/{active}")