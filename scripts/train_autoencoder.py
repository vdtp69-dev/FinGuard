# scripts/train_autoencoder.py
# Autoencoder — neural network trained only on NORMAL transactions
# Reconstruction error = fraud signal
# Trains in ~3 minutes on CPU

import sqlite3
import numpy as np
import pandas as pd
import joblib
import json
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # suppress TF warnings

from tensorflow import keras
from tensorflow.keras import layers
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

print("=" * 50)
print("FinGuard — Autoencoder Training")
print("=" * 50)

# ─────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────

conn = sqlite3.connect("data/finguard.db")
df   = pd.read_sql_query("SELECT * FROM transactions", conn)
conn.close()

df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
df = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)

# ─────────────────────────────────────────
# 2. FEATURE ENGINEERING — same as train_xgboost
# ─────────────────────────────────────────

df["hour"] = df["timestamp"].dt.hour

df["time_since_last_txn"] = (
    df.groupby("user_id")["timestamp"]
    .diff()
    .dt.total_seconds()
    .fillna(0)
)

df["user_avg_amount"] = (
    df.groupby("user_id")["amount"]
    .transform(lambda x: x.expanding().mean().shift(1))
    .fillna(df["amount"])
)

df["amount_vs_avg"] = df["amount"] / (df["user_avg_amount"] + 1e-9)

KNOWN_CITIES = ["Mumbai", "Delhi", "Bangalore", "London", "Dubai"]
KNOWN_MERCHANTS = [
    "Swiggy", "Zomato", "Amazon", "BookStore",
    "Steam", "EpicGames", "LuxuryMall",
    "Airline", "Hotel", "Flipkart"
]

df["is_unknown_location"] = (~df["location"].isin(KNOWN_CITIES)).astype(int)
df["is_unknown_merchant"] = (~df["merchant"].isin(KNOWN_MERCHANTS)).astype(int)
df["is_night"]  = df["hour"].apply(lambda h: 1 if h < 5 or h >= 23 else 0)
df["is_rapid"]  = (df["time_since_last_txn"] < 60).astype(int)

FEATURES = [
    "amount", "hour", "time_since_last_txn",
    "amount_vs_avg", "is_unknown_location",
    "is_unknown_merchant", "is_night", "is_rapid"
]

X = df[FEATURES].values
y = df["is_fraud"].values

print(f"\n✅ Data loaded: {len(df)} transactions")
print(f"   Normal: {(y==0).sum()} · Fraud: {(y==1).sum()}")

# ─────────────────────────────────────────
# 3. SPLIT — train autoencoder ONLY on normal
# This is the key idea — it learns what normal looks like
# When it sees fraud, reconstruction error is HIGH
# ─────────────────────────────────────────

X_normal = X[y == 0]   # only normal transactions for training
X_fraud  = X[y == 1]   # kept aside for evaluation only

print(f"\n✅ Training only on {len(X_normal)} normal transactions")
print(f"   Fraud held out for evaluation: {len(X_fraud)}")

# ─────────────────────────────────────────
# 4. SCALE — autoencoder needs normalized input
# ─────────────────────────────────────────

scaler = StandardScaler()
X_normal_scaled = scaler.fit_transform(X_normal)
X_all_scaled    = scaler.transform(X)

print("✅ Features scaled with StandardScaler")

# ─────────────────────────────────────────
# 5. BUILD AUTOENCODER
# Architecture: 8 → 16 → 8 → 4 → 8 → 16 → 8
# Encoder compresses, Decoder reconstructs
# ─────────────────────────────────────────

input_dim = X_normal_scaled.shape[1]  # 8 features

inputs  = keras.Input(shape=(input_dim,))

# Encoder
encoded = layers.Dense(16, activation="relu")(inputs)
encoded = layers.Dense(8,  activation="relu")(encoded)
encoded = layers.Dense(4,  activation="relu")(encoded)  # bottleneck

# Decoder
decoded = layers.Dense(8,  activation="relu")(encoded)
decoded = layers.Dense(16, activation="relu")(decoded)
outputs = layers.Dense(input_dim, activation="linear")(decoded)

autoencoder = keras.Model(inputs, outputs)
autoencoder.compile(optimizer="adam", loss="mse")

print(f"\n✅ Autoencoder built:")
print(f"   Architecture: {input_dim} → 16 → 8 → 4 → 8 → 16 → {input_dim}")
print(f"   Parameters: {autoencoder.count_params():,}")

# ─────────────────────────────────────────
# 6. TRAIN
# ─────────────────────────────────────────

print("\n🔄 Training autoencoder...")

history = autoencoder.fit(
    X_normal_scaled, X_normal_scaled,
    epochs=50,
    batch_size=32,
    validation_split=0.1,
    verbose=1,
    callbacks=[
        keras.callbacks.EarlyStopping(
            patience=5,
            restore_best_weights=True,
            monitor="val_loss"
        )
    ]
)

print("\n✅ Training complete.")

# ─────────────────────────────────────────
# 7. COMPUTE RECONSTRUCTION ERROR
# High error = transaction looks nothing like normal
# Low error  = transaction looks normal
# ─────────────────────────────────────────

X_pred  = autoencoder.predict(X_all_scaled, verbose=0)
recon_errors = np.mean(np.square(X_all_scaled - X_pred), axis=1)

# Threshold = 95th percentile of normal reconstruction error
normal_errors = recon_errors[y == 0]
threshold     = np.percentile(normal_errors, 95)

print(f"\n✅ Reconstruction error stats:")
print(f"   Normal avg error:  {normal_errors.mean():.4f}")
print(f"   Fraud avg error:   {recon_errors[y==1].mean():.4f}")
print(f"   Threshold (95th):  {threshold:.4f}")

# AUC-ROC
auc = roc_auc_score(y, recon_errors)
print(f"   AUC-ROC:           {auc:.4f}")

# ─────────────────────────────────────────
# 8. SAVE EVERYTHING
# ─────────────────────────────────────────

os.makedirs("models", exist_ok=True)
os.makedirs("models/charts", exist_ok=True)

# Save model
autoencoder.save("models/autoencoder.keras")
print("\n✅ Autoencoder saved → models/autoencoder.keras")

# Save scaler — needed for inference
joblib.dump(scaler, "models/autoencoder_scaler.pkl")
print("✅ Scaler saved → models/autoencoder_scaler.pkl")

# Save threshold — needed for inference
threshold_data = {
    "threshold": float(threshold),
    "auc_roc":   float(auc),
    "normal_avg_error": float(normal_errors.mean()),
    "fraud_avg_error":  float(recon_errors[y==1].mean())
}
with open("models/autoencoder_config.json", "w") as f:
    json.dump(threshold_data, f, indent=2)
print("✅ Config saved → models/autoencoder_config.json")

# Update metrics.json with autoencoder AUC
try:
    with open("models/metrics.json") as f:
        metrics = json.load(f)
    metrics["autoencoder"] = {
        "auc_roc":   round(float(auc), 4),
        "threshold": round(float(threshold), 6),
        "type":      "reconstruction_error"
    }
    with open("models/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print("✅ metrics.json updated with autoencoder AUC")
except:
    pass

# ─────────────────────────────────────────
# 9. CHARTS
# ─────────────────────────────────────────

# Training loss curve
fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#161b22")

ax.plot(history.history["loss"],
        color="#58a6ff", linewidth=2, label="Training loss")
ax.plot(history.history["val_loss"],
        color="#3fb950", linewidth=2, label="Validation loss")
ax.set_title("Autoencoder Training Loss",
             color="#ffffff", fontsize=14)
ax.set_xlabel("Epoch", color="#8b949e")
ax.set_ylabel("MSE Loss", color="#8b949e")
ax.tick_params(colors="#8b949e")
ax.legend(facecolor="#161b22", labelcolor="#ffffff")
ax.grid(True, color="#21262d", alpha=0.5)
for spine in ax.spines.values():
    spine.set_edgecolor("#21262d")

plt.tight_layout()
plt.savefig("models/charts/autoencoder_loss.png",
            dpi=150, facecolor="#0d1117")
plt.close()

# Reconstruction error distribution
fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#161b22")

ax.hist(recon_errors[y==0], bins=50,
        alpha=0.7, color="#3fb950",
        label=f"Normal ({(y==0).sum()} txns)")
ax.hist(recon_errors[y==1], bins=20,
        alpha=0.7, color="#f85149",
        label=f"Fraud ({(y==1).sum()} txns)")
ax.axvline(threshold, color="#d29922",
           linewidth=2, linestyle="--",
           label=f"Threshold ({threshold:.3f})")
ax.set_title("Reconstruction Error Distribution",
             color="#ffffff", fontsize=14)
ax.set_xlabel("Reconstruction Error", color="#8b949e")
ax.set_ylabel("Count", color="#8b949e")
ax.tick_params(colors="#8b949e")
ax.legend(facecolor="#161b22", labelcolor="#ffffff")
ax.grid(True, color="#21262d", alpha=0.5)
for spine in ax.spines.values():
    spine.set_edgecolor("#21262d")

plt.tight_layout()
plt.savefig("models/charts/autoencoder_distribution.png",
            dpi=150, facecolor="#0d1117")
plt.close()

print("✅ Training loss chart saved")
print("✅ Error distribution chart saved")

print("\n" + "=" * 50)
print("AUTOENCODER TRAINING COMPLETE")
print(f"  AUC-ROC: {auc:.4f}")
print(f"  Threshold: {threshold:.4f}")
print(f"  Normal avg error: {normal_errors.mean():.4f}")
print(f"  Fraud avg error:  {recon_errors[y==1].mean():.4f}")
print("=" * 50)