# api.py — updated with SHAP
# Changes from previous version are marked with # ← NEW

import sqlite3
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import sys
import os
import shap # ← NEW

sys.path.append(os.path.join(os.path.dirname(__file__), "risk"))
from risk.risk_engine import calculate_risk

# ─────────────────────────────────────────
# 1. LOAD ALL MODELS ONCE AT STARTUP
# ─────────────────────────────────────────

xgb_model = joblib.load("models/xgboost_fraud_model.pkl")

iso_models = {
    1: joblib.load("models/isolation_forest_user_1.pkl"),
    2: joblib.load("models/isolation_forest_user_2.pkl"),
    3: joblib.load("models/isolation_forest_user_3.pkl"),
}

# ← NEW — create SHAP explainer once at startup (fast for XGBoost)
shap_explainer = shap.TreeExplainer(xgb_model)

print("✅ All models loaded.")
print("✅ SHAP explainer ready.")

# ─────────────────────────────────────────
# 2. FASTAPI APP
# ─────────────────────────────────────────

app = FastAPI(
    title="FinGuard Fraud Detection API",
    description="Hybrid fraud detection using Isolation Forest + XGBoost + Risk Engine + SHAP",
    version="2.0.0"
)

# ─────────────────────────────────────────
# 3. REQUEST BODY SCHEMA
# ─────────────────────────────────────────

class Transaction(BaseModel):
    user_id:   int
    amount:    float
    timestamp: str
    location:  str
    merchant:  str
    time_gap_override: float = -1.0 
# ─────────────────────────────────────────
# 4. HELPER: GET USER STATS FROM DB
# ─────────────────────────────────────────

def get_user_stats(user_id: int) -> dict:
    conn = sqlite3.connect("data/finguard.db")

    avg_df = pd.read_sql_query(
        "SELECT AVG(amount) as avg_amount FROM transactions WHERE user_id = ?",
        conn, params=(user_id,)
    )
    last_df = pd.read_sql_query(
        "SELECT MAX(timestamp) as last_txn FROM transactions WHERE user_id = ?",
        conn, params=(user_id,)
    )
    conn.close()

    return {
        "avg_amount": float(avg_df["avg_amount"].iloc[0] or 0.0),
        "last_txn":   last_df["last_txn"].iloc[0]
    }

# ─────────────────────────────────────────
# 5. HELPER: COMPUTE FEATURES
# ─────────────────────────────────────────

def compute_features(txn: Transaction, user_stats: dict) -> dict:
    dt   = datetime.fromisoformat(txn.timestamp)
    hour = dt.hour

    if user_stats["last_txn"]:
        last_dt = datetime.fromisoformat(user_stats["last_txn"])
        time_since_last = max(0.0, (dt - last_dt).total_seconds())
    else:
        time_since_last = 0.0

    return {
        "amount":              txn.amount,
        "hour":                hour,
        "time_since_last_txn": time_since_last
    }

# ─────────────────────────────────────────
# 6. ← NEW — SHAP EXPLANATION HELPER
# ─────────────────────────────────────────

FEATURE_NAMES = ["amount", "hour", "time_since_last_txn"]

def get_shap_explanation(feature_array: pd.DataFrame) -> dict:
    """
    Returns SHAP values for this single transaction.
    Tells you exactly how much each feature pushed
    the fraud score up or down.
    """
    shap_values = shap_explainer.shap_values(feature_array)

    # shap_values shape: (1, 3) — one row, three features
    values = shap_values[0].tolist()

    explanation = {}
    for name, value in zip(FEATURE_NAMES, values):
        explanation[name] = round(value, 6)

    # Sort by absolute impact — biggest driver first
    sorted_explanation = dict(
        sorted(explanation.items(), key=lambda x: abs(x[1]), reverse=True)
    )

    # Human readable sentences
    feature_labels = {
        "amount":              "Transaction amount",
        "hour":                "Transaction hour",
        "time_since_last_txn": "Time since last transaction",
    }

    reasons_shap = []
    for feature, shap_val in sorted_explanation.items():
        label     = feature_labels[feature]
        direction = "increased" if shap_val > 0 else "decreased"
        magnitude = abs(shap_val)

        if magnitude > 0.001:   # ignore near-zero contributions
            reasons_shap.append(
                f"{label} {direction} fraud risk "
                f"({'↑' if shap_val > 0 else '↓'} {magnitude:.4f})"
            )

    return {
        "shap_values":        sorted_explanation,
        "base_value":         round(float(shap_explainer.expected_value), 6),
        "top_reasons":        reasons_shap[:3],   # top 3 drivers only
    }

# ─────────────────────────────────────────
# 7. MAIN ENDPOINT: SCORE A TRANSACTION
# ─────────────────────────────────────────

@app.post("/score")
def score_transaction(txn: Transaction):

    # ── Step 1: User history ──
    user_stats = get_user_stats(txn.user_id)

    # ── Step 2: Features ──
    features = compute_features(txn, user_stats)

    feature_array = pd.DataFrame([{
        "amount":              features["amount"],
        "hour":                features["hour"],
        "time_since_last_txn": features["time_since_last_txn"]
    }])

    # ── Step 3: Isolation Forest ──
    iso = iso_models.get(txn.user_id)
    if iso:
        anomaly_label = int(iso.predict(feature_array)[0])
        anomaly_score = float(iso.score_samples(feature_array)[0])
    else:
        anomaly_label = -1
        anomaly_score = -0.5

    # ── Step 4: XGBoost ──
    fraud_prob = float(xgb_model.predict_proba(feature_array)[0][1])

    # ── Step 5: SHAP explanation ──       ← NEW
    shap_result = get_shap_explanation(feature_array)

   # ── Step 7: Risk Engine — now passes fraud_prob ──
    time_gap_final = (
        txn.time_gap_override 
        if txn.time_gap_override >= 0 
        else features["time_since_last_txn"]
    )
    # ── Step 6: Risk Engine ──
    status, risk_score, reasons = calculate_risk(
        amount        = features["amount"],
        hour          = features["hour"],
        time_gap      = time_gap_final,       # ← uses override if set
        anomaly       = anomaly_label,
        anomaly_score = anomaly_score,
        user_avg      = user_stats["avg_amount"],
        fraud_prob    = fraud_prob            # ← NEW
    )

    # ── Step 7: Return full result ──
    return {
        "user_id":           txn.user_id,
        "amount":            txn.amount,
        "timestamp":         txn.timestamp,
        "location":          txn.location,
        "merchant":          txn.merchant,

        # Core outputs
        "decision":          status,
        "risk_score":        risk_score,
        "fraud_probability": round(fraud_prob, 4),

        # Model outputs
        "anomaly_label":     anomaly_label,
        "anomaly_score":     round(anomaly_score, 4),

        # Risk engine reasons
        "reasons":           reasons,

        # ← NEW — SHAP explanation
        "shap_explanation":  shap_result,

        # Features used
        "features_used": {
            "hour":                features["hour"],
            "time_since_last_txn": round(features["time_since_last_txn"], 1),
            "user_avg_amount":     round(user_stats["avg_amount"], 2)
        }
    }

# ─────────────────────────────────────────
# 8. HEALTH CHECK
# ─────────────────────────────────────────

@app.get("/")
def health_check():
    return {
        "status":        "FinGuard API is running",
        "models_loaded": len(iso_models) + 1,
        "shap":          "enabled"           # ← NEW
    }

@app.get("/user/{user_id}/stats")
def user_stats(user_id: int):
    stats = get_user_stats(user_id)
    return {"user_id": user_id, **stats}