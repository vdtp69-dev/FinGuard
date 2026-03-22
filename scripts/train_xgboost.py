# scripts/train_xgboost.py — complete rewrite
# Features: amount, hour, time_since_last_txn,
#           is_unknown_location, is_unknown_merchant,
#           amount_vs_user_avg
# Models: XGBoost + Random Forest
# Evaluation: AUC-ROC, confusion matrix, classification report
# Balancing: SMOTE

import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import json
import matplotlib
matplotlib.use("Agg")   # no display needed
import matplotlib.pyplot as plt

from sklearn.ensemble         import RandomForestClassifier, IsolationForest
from sklearn.model_selection  import train_test_split
from sklearn.metrics          import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
    ConfusionMatrixDisplay
)
from imblearn.over_sampling import SMOTE

print("=" * 50)
print("FinGuard — Model Training Pipeline")
print("=" * 50)

# ─────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────

conn = sqlite3.connect("data/finguard.db")
df   = pd.read_sql_query("SELECT * FROM transactions", conn)
conn.close()

df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)

print(f"\n✅ Loaded {len(df)} transactions")
print(f"   Fraud: {df['is_fraud'].sum()} ({df['is_fraud'].mean()*100:.1f}%)")

# ─────────────────────────────────────────
# 2. FEATURE ENGINEERING
# ─────────────────────────────────────────

# Basic time features
df["hour"] = df["timestamp"].dt.hour

df["time_since_last_txn"] = (
    df.groupby("user_id")["timestamp"]
    .diff()
    .dt.total_seconds()
    .fillna(0)
)

# Per-user average amount — using expanding mean
# (only uses past transactions, no future leakage)
df["user_avg_amount"] = (
    df.groupby("user_id")["amount"]
    .transform(lambda x: x.expanding().mean().shift(1))
    .fillna(df["amount"])
)

# Amount vs user average ratio
df["amount_vs_avg"] = df["amount"] / (df["user_avg_amount"] + 1e-9)

# Location risk — unknown city = 1
known_cities = ["Mumbai", "Delhi", "Bangalore", "London", "Dubai"]
df["is_unknown_location"] = (~df["location"].isin(known_cities)).astype(int)

# Merchant risk — unknown merchant = 1
known_merchants = [
    "Swiggy", "Zomato", "Amazon", "BookStore",
    "Steam", "EpicGames", "LuxuryMall",
    "Airline", "Hotel", "Flipkart"
]
df["is_unknown_merchant"] = (~df["merchant"].isin(known_merchants)).astype(int)

# Night flag
df["is_night"] = df["hour"].apply(
    lambda h: 1 if h < 5 or h >= 23 else 0
)

# Velocity flag
df["is_rapid"] = (df["time_since_last_txn"] < 60).astype(int)

print("\n✅ Features engineered:")
FEATURES = [
    "amount",
    "hour",
    "time_since_last_txn",
    "amount_vs_avg",
    "is_unknown_location",
    "is_unknown_merchant",
    "is_night",
    "is_rapid"
]
for f in FEATURES:
    print(f"   • {f}")

# ─────────────────────────────────────────
# 3. TRAIN / TEST SPLIT
# ─────────────────────────────────────────

X = df[FEATURES]
y = df["is_fraud"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y        # keep fraud ratio same in both splits
)

print(f"\n✅ Split: {len(X_train)} train, {len(X_test)} test")
print(f"   Train fraud: {y_train.sum()} ({y_train.mean()*100:.1f}%)")

# ─────────────────────────────────────────
# 4. SMOTE — fix class imbalance
# ─────────────────────────────────────────

print("\n🔄 Applying SMOTE to balance classes...")
smote             = SMOTE(random_state=42)
X_train_bal, y_train_bal = smote.fit_resample(X_train, y_train)

print(f"✅ After SMOTE:")
print(f"   Normal: {(y_train_bal==0).sum()}")
print(f"   Fraud:  {(y_train_bal==1).sum()}")

# ─────────────────────────────────────────
# 5. TRAIN XGBOOST
# ─────────────────────────────────────────

print("\n🔄 Training XGBoost...")
xgb_model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    use_label_encoder=False,
    eval_metric="logloss",
    random_state=42
)
xgb_model.fit(X_train_bal, y_train_bal)

xgb_preds = xgb_model.predict(X_test)
xgb_proba = xgb_model.predict_proba(X_test)[:, 1]
xgb_auc   = roc_auc_score(y_test, xgb_proba)

print(f"✅ XGBoost AUC-ROC: {xgb_auc:.4f}")
print(classification_report(y_test, xgb_preds))

# ─────────────────────────────────────────
# 6. TRAIN RANDOM FOREST
# ─────────────────────────────────────────

print("\n🔄 Training Random Forest...")
rf_model = RandomForestClassifier(
    n_estimators=200,
    max_depth=8,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)
rf_model.fit(X_train_bal, y_train_bal)

rf_preds = rf_model.predict(X_test)
rf_proba = rf_model.predict_proba(X_test)[:, 1]
rf_auc   = roc_auc_score(y_test, rf_proba)

print(f"✅ Random Forest AUC-ROC: {rf_auc:.4f}")
print(classification_report(y_test, rf_preds))

# ─────────────────────────────────────────
# 7. TRAIN ISOLATION FOREST (all users)
#    also retrain per-user models
# ─────────────────────────────────────────

print("\n🔄 Training Isolation Forest models...")

# Global model
iso_global = IsolationForest(
    n_estimators=100,
    contamination=0.05,
    random_state=42
)
iso_global.fit(X[["amount", "hour", "time_since_last_txn",
                   "amount_vs_avg", "is_unknown_location",
                   "is_unknown_merchant"]])
joblib.dump(iso_global, "models/isolation_forest_global.pkl")
print("✅ Global Isolation Forest saved.")

# Per-user models
iso_features = [
    "amount", "hour", "time_since_last_txn",
    "amount_vs_avg", "is_unknown_location",
    "is_unknown_merchant"
]

for uid in df["user_id"].unique():
    user_df = df[df["user_id"] == uid]
    X_user  = user_df[iso_features]

    iso_user = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42
    )
    iso_user.fit(X_user)
    path = f"models/isolation_forest_user_{uid}.pkl"
    joblib.dump(iso_user, path)
    print(f"✅ User {uid} Isolation Forest saved → {path}")

# ─────────────────────────────────────────
# 8. SAVE MODELS + FEATURE LIST
# ─────────────────────────────────────────

joblib.dump(xgb_model, "models/xgboost_fraud_model.pkl")
joblib.dump(rf_model,  "models/random_forest_fraud_model.pkl")

# Save feature list so API always uses same features
with open("models/feature_list.json", "w") as f:
    json.dump(FEATURES, f)

print("\n✅ Models saved:")
print("   models/xgboost_fraud_model.pkl")
print("   models/random_forest_fraud_model.pkl")
print("   models/isolation_forest_global.pkl")
print("   models/isolation_forest_user_1/2/3.pkl")
print("   models/feature_list.json")

# ─────────────────────────────────────────
# 9. EVALUATION CHARTS — saved as images
#    Dashboard will display these
# ─────────────────────────────────────────

import os
os.makedirs("models/charts", exist_ok=True)

# ── AUC-ROC Curve ──
fig, ax = plt.subplots(figsize=(8, 6))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#161b22")

for name, proba, color in [
    ("XGBoost",       xgb_proba, "#58a6ff"),
    ("Random Forest", rf_proba,  "#3fb950"),
]:
    fpr, tpr, _ = roc_curve(y_test, proba)
    auc_val     = roc_auc_score(y_test, proba)
    ax.plot(fpr, tpr,
            label=f"{name} (AUC = {auc_val:.3f})",
            color=color, linewidth=2)

ax.plot([0,1],[0,1], "--", color="#8b949e", linewidth=1)
ax.set_xlabel("False Positive Rate", color="#8b949e")
ax.set_ylabel("True Positive Rate", color="#8b949e")
ax.set_title("AUC-ROC Curve — Model Comparison",
             color="#ffffff", fontsize=14)
ax.legend(facecolor="#161b22", labelcolor="#ffffff")
ax.tick_params(colors="#8b949e")
for spine in ax.spines.values():
    spine.set_edgecolor("#21262d")
ax.grid(True, color="#21262d", alpha=0.5)

plt.tight_layout()
plt.savefig("models/charts/auc_roc.png",
            dpi=150, facecolor="#0d1117")
plt.close()
print("\n✅ AUC-ROC chart saved → models/charts/auc_roc.png")

# ── Confusion Matrix — XGBoost ──
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.patch.set_facecolor("#0d1117")

for ax, (name, preds, color) in zip(axes, [
    ("XGBoost",       xgb_preds, "#58a6ff"),
    ("Random Forest", rf_preds,  "#3fb950"),
]):
    cm = confusion_matrix(y_test, preds)
    ax.set_facecolor("#161b22")
    im = ax.imshow(cm, cmap="Blues")
    ax.set_title(f"{name} — Confusion Matrix",
                 color="#ffffff", pad=12)
    ax.set_xlabel("Predicted", color="#8b949e")
    ax.set_ylabel("Actual", color="#8b949e")
    ax.tick_params(colors="#8b949e")
    ax.set_xticks([0,1])
    ax.set_yticks([0,1])
    ax.set_xticklabels(["Normal","Fraud"], color="#8b949e")
    ax.set_yticklabels(["Normal","Fraud"], color="#8b949e")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i,j]),
                    ha="center", va="center",
                    color="#ffffff", fontsize=16, fontweight="bold")
    for spine in ax.spines.values():
        spine.set_edgecolor("#21262d")

plt.tight_layout()
plt.savefig("models/charts/confusion_matrix.png",
            dpi=150, facecolor="#0d1117")
plt.close()
print("✅ Confusion matrix saved → models/charts/confusion_matrix.png")

# ── Feature Importance ──
fig, ax = plt.subplots(figsize=(8, 6))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#161b22")

importance = pd.Series(
    xgb_model.feature_importances_,
    index=FEATURES
).sort_values()

bars = ax.barh(importance.index, importance.values,
               color="#58a6ff", alpha=0.85)
ax.set_title("XGBoost Feature Importance",
             color="#ffffff", fontsize=14)
ax.set_xlabel("Importance Score", color="#8b949e")
ax.tick_params(colors="#8b949e")
for spine in ax.spines.values():
    spine.set_edgecolor("#21262d")
ax.grid(True, axis="x", color="#21262d", alpha=0.5)

plt.tight_layout()
plt.savefig("models/charts/feature_importance.png",
            dpi=150, facecolor="#0d1117")
plt.close()
print("✅ Feature importance chart saved → models/charts/feature_importance.png")

# ── Save metrics as JSON for dashboard ──
metrics = {
    "xgboost": {
        "auc_roc":   round(xgb_auc, 4),
        "precision": round(float(
            (xgb_preds[y_test==1] == 1).sum() /
            (xgb_preds==1).sum() if (xgb_preds==1).sum() > 0 else 0), 4),
        "recall":    round(float(
            (xgb_preds[y_test==1] == 1).sum() /
            (y_test==1).sum()), 4),
    },
    "random_forest": {
        "auc_roc":   round(rf_auc, 4),
        "precision": round(float(
            (rf_preds[y_test==1] == 1).sum() /
            (rf_preds==1).sum() if (rf_preds==1).sum() > 0 else 0), 4),
        "recall":    round(float(
            (rf_preds[y_test==1] == 1).sum() /
            (y_test==1).sum()), 4),
    },
    "features": FEATURES,
    "train_size": len(X_train_bal),
    "test_size":  len(X_test),
    "fraud_rate": round(float(y.mean()), 4)
}

with open("models/metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

print("✅ Metrics JSON saved → models/metrics.json")

print("\n" + "=" * 50)
print("TRAINING COMPLETE")
print(f"  XGBoost AUC-ROC:       {xgb_auc:.4f}")
print(f"  Random Forest AUC-ROC: {rf_auc:.4f}")
print("=" * 50)