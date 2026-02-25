from paths import snapshot_dir, eval_dir
import json
import requests
import yaml
import os
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load(open(BASE_DIR / "config/providers.yaml"))

RUN_ID = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%MZ")
(BASE_DIR / "CURRENT_RUN.txt").write_text(RUN_ID)

SNAPSHOT_DIR = snapshot_dir(RUN_ID)
eval_dir(RUN_ID)

meta = {"run_id": RUN_ID, "providers": {}}


def fetch_coingecko(p):
    r = requests.get(
        p["api_url"],
        params={
            "vs_currency": p["vs_currency"],
            "order": "market_cap_desc",
            "per_page": p["top_n"],
            "page": 1
        },
        timeout=30
    )
    r.raise_for_status()
    return r.json()

def fetch_coinmarketcap(p):
    key = os.environ.get("CMC_API_KEY")
    if not key:
        raise RuntimeError("CMC_API_KEY missing")
    r = requests.get(
        p["api_url"],
        headers={"X-CMC_PRO_API_KEY": key},
        params={"limit": p["top_n"], "convert": p["vs_currency"]},
        timeout=30
    )
    r.raise_for_status()
    return r.json()

def fetch_coinpaprika(p):
    r = requests.get(p["api_url"], timeout=30)
    r.raise_for_status()
    return r.json()

for p in CFG["providers"]:
    if not p.get("enabled"):
        continue
    try:
        if p["name"] == "coingecko":
            data = fetch_coingecko(p)
        elif p["name"] == "coinmarketcap":
            data = fetch_coinmarketcap(p)
        elif p["name"] == "coinpaprika":
            data = fetch_coinpaprika(p)
        else:
            continue

        with open(SNAPSHOT_DIR / f"{p['name']}.json", "w") as f:
            json.dump(data, f)

        meta["providers"][p["name"]] = "success"
    except Exception as e:
        meta["providers"][p["name"]] = f"error: {e}"

with open(SNAPSHOT_DIR / "snapshot_meta.json", "w") as f:
    json.dump(meta, f, indent=2)

print("Snapshot locked:", RUN_ID)
print("Provider status:", meta["providers"])
