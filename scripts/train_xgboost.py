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

df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
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

# ── 3 NEW FEATURES ──
# 1. is_round_amount
df["is_round_amount"] = ((df["amount"] % 100 == 0) | (df["amount"] % 50 == 0)).astype(int)

# 2. device_trust_score (simulated correlation with location/night)
np.random.seed(42)
base_trust = 1.0 - (df["is_unknown_location"] * 0.4) - (df["is_night"] * 0.2)
noise = np.random.normal(0, 0.1, len(df))
df["device_trust_score"] = (base_trust + noise).clip(0.1, 1.0)

# 3. merchant_risk_score
merchant_risks = {
    "Swiggy": 0.2, "Zomato": 0.2, "Amazon": 0.1, "BookStore": 0.1,
    "Steam": 0.5, "EpicGames": 0.5, "LuxuryMall": 0.8,
    "Airline": 0.7, "Hotel": 0.6, "Flipkart": 0.2
}
df["merchant_risk_score"] = df["merchant"].map(merchant_risks).fillna(0.9)

print("\n✅ Features engineered:")
FEATURES = [
    "amount",
    "hour",
    "time_since_last_txn",
    "amount_vs_avg",
    "is_unknown_location",
    "is_unknown_merchant",
    "is_night",
    "is_rapid",
    "is_round_amount",
    "device_trust_score",
    "merchant_risk_score"
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
iso_global.fit(X[FEATURES])
joblib.dump(iso_global, "models/isolation_forest_global.pkl")
print("✅ Global Isolation Forest saved.")

# Per-user models
iso_features = FEATURES

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
from sklearn.metrics import recall_score, precision_score, f1_score
xgb_precision = round(float(precision_score(y_test, xgb_preds, zero_division=0)), 4)
xgb_recall = round(float(recall_score(y_test, xgb_preds, zero_division=0)), 4)
xgb_f1 = round(float(f1_score(y_test, xgb_preds, zero_division=0)), 4)
rf_precision = round(float(precision_score(y_test, rf_preds, zero_division=0)), 4)
rf_recall = round(float(recall_score(y_test, rf_preds, zero_division=0)), 4)

cm = confusion_matrix(y_test, xgb_preds)
tn, fp, fn, tp = cm.ravel()
xgb_fpr = round(float(fp / (fp + tn)), 4)

fpr_xgb_arr, tpr_xgb_arr, _ = roc_curve(y_test, xgb_proba)
fpr_rf_arr, tpr_rf_arr, _ = roc_curve(y_test, rf_proba)

# sample max 50 points to keep json small
def reduce_points(f_arr, t_arr, n=50):
    if len(f_arr) <= n:
        return [{"fpr": round(float(f), 4), "tpr": round(float(t), 4)} for f, t in zip(f_arr, t_arr)]
    idx = np.linspace(0, len(f_arr)-1, n, dtype=int)
    return [{"fpr": round(float(f_arr[i]), 4), "tpr": round(float(t_arr[i]), 4)} for i in idx]

metrics = {
    "xgboost": {
        "auc_roc":   round(xgb_auc, 4),
        "precision": xgb_precision,
        "recall":    xgb_recall,
        "f1_score":  xgb_f1,
    },
    "random_forest": {
        "auc_roc":   round(rf_auc, 4),
        "precision": rf_precision,
        "recall":    rf_recall,
    },
    "confusion_matrix": cm.tolist(),
    "roc_curve_xgboost": reduce_points(fpr_xgb_arr, tpr_xgb_arr),
    "roc_curve_rf": reduce_points(fpr_rf_arr, tpr_rf_arr),
    "fpr": xgb_fpr,
    "f1_score": xgb_f1,
    "features": FEATURES,
    "train_size": len(X_train_bal),
    "test_size":  len(X_test),
    "fraud_rate": round(float(y.mean()), 4)
}

# ── Cost Analysis ──
test_df = df.iloc[y_test.index]
false_positives = (xgb_preds == 1) & (y_test == 0)
false_negatives = (xgb_preds == 0) & (y_test == 1)
true_positives = (xgb_preds == 1) & (y_test == 1)

cost_per_review = 50
fp_cost = false_positives.sum() * cost_per_review
fn_cost = test_df.loc[false_negatives, "amount"].sum()
savings = test_df.loc[true_positives, "amount"].sum()

metrics["cost_analysis"] = {
    "false_positive_cost": float(fp_cost),
    "fraud_loss": float(fn_cost),
    "fraud_prevented": float(savings),
    "roi": float(savings - fp_cost)
}

with open("models/metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)

print("✅ Metrics JSON saved → models/metrics.json")

# ── Compute Global SHAP Cache ──
import shap
explainer = shap.TreeExplainer(xgb_model)
sample_size = min(len(X_train_bal), 1000)
shap_sample = X_train_bal.sample(n=sample_size, random_state=42)
shap_vals = explainer.shap_values(shap_sample)
mean_shap = np.abs(shap_vals).mean(axis=0)
shap_dict = {feat: float(mean_shap[i]) for i, feat in enumerate(FEATURES)}
from datetime import datetime
global_shap_res = {"global_shap": shap_dict, "timestamp": datetime.now().isoformat()}

with open("models/global_shap_cache.json", "w") as f:
    json.dump(global_shap_res, f, indent=2)

print("✅ Real Global SHAP cache saved → models/global_shap_cache.json")

print("\n" + "=" * 50)
print("TRAINING COMPLETE")
print(f"  XGBoost AUC-ROC:       {xgb_auc:.4f}")
print(f"  Random Forest AUC-ROC: {rf_auc:.4f}")
print("=" * 50)