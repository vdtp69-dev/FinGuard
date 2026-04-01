import sqlite3
import pandas as pd
import json
import os
from scipy.stats import ks_2samp
from datetime import datetime
import numpy as np

print("=" * 50)
print("Drift Detection (KS Test)")
print("=" * 50)

conn = sqlite3.connect("data/finguard.db")
df = pd.read_sql_query("SELECT * FROM transactions ORDER BY timestamp DESC", conn)
conn.close()

if len(df) < 1000:
    print("Not enough data to detect drift.")
    exit(0)

# Feature engineering
df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
df = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)

df["hour"] = df["timestamp"].dt.hour
df["time_since_last_txn"] = df.groupby("user_id")["timestamp"].diff().dt.total_seconds().fillna(0)

df["user_avg_amount"] = (
    df.groupby("user_id")["amount"]
    .transform(lambda x: x.expanding().mean().shift(1))
    .fillna(df["amount"])
)
df["amount_vs_avg"] = df["amount"] / (df["user_avg_amount"] + 1e-9)

known_cities = ["Mumbai", "Delhi", "Bangalore", "London", "Dubai"]
df["is_unknown_location"] = (~df["location"].isin(known_cities)).astype(int)

known_merchants = [
    "Swiggy", "Zomato", "Amazon", "BookStore",
    "Steam", "EpicGames", "LuxuryMall",
    "Airline", "Hotel", "Flipkart"
]
df["is_unknown_merchant"] = (~df["merchant"].isin(known_merchants)).astype(int)

df["is_night"] = df["hour"].apply(lambda h: 1 if h < 5 or h >= 23 else 0)
df["is_rapid"] = (df["time_since_last_txn"] < 60).astype(int)

FEATURES = [
    "amount", "hour", "time_since_last_txn",
    "amount_vs_avg", "is_unknown_location",
    "is_unknown_merchant", "is_night", "is_rapid"
]

df = df.sort_values("timestamp")
train_df = df.iloc[:-500]
recent_df = df.iloc[-500:]

drift_report = {}
drift_detected = False

for feat in FEATURES:
    train_vals = train_df[feat].values
    recent_vals = recent_df[feat].values
    
    stat, p_value = ks_2samp(train_vals, recent_vals)
    has_drift = bool(p_value < 0.05)
    
    drift_report[feat] = {
        "p_value": float(p_value),
        "statistic": float(stat),
        "has_drift": has_drift,
        "train_mean": float(np.mean(train_vals)),
        "recent_mean": float(np.mean(recent_vals))
    }
    
    if has_drift:
        drift_detected = True
        print(f"⚠️ Drift detected in {feat} (p={p_value:.4f})")
    else:
        print(f"✅ {feat} looks stable (p={p_value:.4f})")

report = {
    "timestamp": datetime.now().isoformat(),
    "features": drift_report,
    "overall_drift": drift_detected
}

os.makedirs("models", exist_ok=True)
with open("models/drift_report.json", "w") as f:
    json.dump(report, f, indent=2)

print("\n✅ Drift report saved to models/drift_report.json")
