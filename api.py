# api.py — updated for 8 features + Random Forest + auto user onboarding
import sqlite3
import joblib
import numpy as np
import pandas as pd
import shap
import os
import json
import threading
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import sys
# Add after iso_models loading
from tensorflow import keras as tf_keras
import json as json_module

sys.path.append(os.path.join(os.path.dirname(__file__), "risk"))
from risk.risk_engine import calculate_risk

# Load autoencoder
autoencoder        = tf_keras.models.load_model("models/autoencoder.keras")
autoencoder_scaler = joblib.load("models/autoencoder_scaler.pkl")

with open("models/autoencoder_config.json") as f:
    ae_config = json_module.load(f)

AE_THRESHOLD = ae_config["threshold"]
print(f"✅ Autoencoder loaded — threshold: {AE_THRESHOLD:.4f}")


# ─────────────────────────────────────────
# 1. LOAD FEATURE LIST — single source of truth
# ─────────────────────────────────────────

with open("models/feature_list.json") as f:
    FEATURES = json.load(f)

print(f"✅ Features loaded: {FEATURES}")

# ─────────────────────────────────────────
# 2. LOAD ALL MODELS
# ─────────────────────────────────────────

xgb_model  = joblib.load("models/xgboost_fraud_model.pkl")
rf_model   = joblib.load("models/random_forest_fraud_model.pkl")
iso_global = joblib.load("models/isolation_forest_global.pkl")

def load_all_iso_models() -> dict:
    models = {}
    for filename in os.listdir("models"):
        if filename.startswith("isolation_forest_user_") \
           and filename.endswith(".pkl"):
            uid = int(
                filename
                .replace("isolation_forest_user_", "")
                .replace(".pkl", "")
            )
            models[uid] = joblib.load(f"models/{filename}")
            print(f"  ✅ Isolation Forest loaded — User {uid}")
    return models

iso_models     = load_all_iso_models()
shap_explainer = shap.TreeExplainer(xgb_model)

COLD_START_THRESHOLD = 50

# Known locations and merchants
KNOWN_CITIES = [
    "Mumbai", "Delhi", "Bangalore", "London", "Dubai"
]
KNOWN_MERCHANTS = [
    "Swiggy", "Zomato", "Amazon", "BookStore",
    "Steam", "EpicGames", "LuxuryMall",
    "Airline", "Hotel", "Flipkart"
]

print(f"✅ {len(iso_models)} per-user Isolation Forest models loaded.")
print(f"✅ XGBoost + Random Forest loaded.")
print(f"✅ SHAP explainer ready.")

# ─────────────────────────────────────────
# 3. APP
# ─────────────────────────────────────────

app = FastAPI(
    title="FinGuard API",
    description="Hybrid fraud detection — 8 features, 3 models, SHAP",
    version="4.0.0"
)

# ─────────────────────────────────────────
# 4. REQUEST SCHEMA
# ─────────────────────────────────────────

class Transaction(BaseModel):
    user_id:           int
    amount:            float
    timestamp:         str
    location:          str
    merchant:          str
    time_gap_override: float = -1.0

# ─────────────────────────────────────────
# 5. DATABASE HELPERS
# ─────────────────────────────────────────

def get_db():
    conn = sqlite3.connect("data/finguard.db")
    conn.row_factory = sqlite3.Row
    return conn

def ensure_user_exists(user_id: int):
    conn = get_db()
    cur  = conn.cursor()
    exists = cur.execute(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    if not exists:
        cur.execute(
            "INSERT INTO users VALUES (?, ?, ?)",
            (user_id, f"User_{user_id}", "NewUser")
        )
        conn.commit()
        print(f"  🆕 Auto-created User {user_id}")
    conn.close()

def get_user_stats(user_id: int) -> dict:
    conn = get_db()

    avg_df = pd.read_sql_query(
        "SELECT AVG(amount) as avg_amount FROM transactions WHERE user_id=?",
        conn, params=(user_id,)
    )
    last_df = pd.read_sql_query(
        "SELECT MAX(timestamp) as last_txn FROM transactions WHERE user_id=?",
        conn, params=(user_id,)
    )
    count_df = pd.read_sql_query(
        "SELECT COUNT(*) as cnt FROM transactions WHERE user_id=?",
        conn, params=(user_id,)
    )
    # User's most common city
    city_df = pd.read_sql_query(
        """SELECT location, COUNT(*) as cnt
           FROM transactions WHERE user_id=?
           GROUP BY location ORDER BY cnt DESC LIMIT 1""",
        conn, params=(user_id,)
    )
    conn.close()

    return {
        "avg_amount":    float(avg_df["avg_amount"].iloc[0] or 0.0),
        "last_txn":      last_df["last_txn"].iloc[0],
        "txn_count":     int(count_df["cnt"].iloc[0]),
        "usual_city":    city_df["location"].iloc[0] if len(city_df) else None
    }

def save_transaction(txn):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO transactions
            (user_id, amount, timestamp, location, merchant, is_fraud)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (txn.user_id, txn.amount, txn.timestamp,
          txn.location, txn.merchant))
    conn.commit()
    conn.close()

# ─────────────────────────────────────────
# 6. FEATURE ENGINEERING
# ─────────────────────────────────────────

def compute_features(txn: Transaction,
                     user_stats: dict,
                     time_gap_override: float) -> dict:
    dt   = datetime.fromisoformat(txn.timestamp)
    hour = dt.hour

    # Time since last transaction
    if time_gap_override >= 0:
        time_gap = time_gap_override
    elif user_stats["last_txn"]:
        last_dt  = datetime.fromisoformat(user_stats["last_txn"])
        time_gap = max(0.0, (dt - last_dt).total_seconds())
    else:
        time_gap = 0.0

    # Amount vs user average
    user_avg     = user_stats["avg_amount"] or txn.amount
    amount_vs_avg = txn.amount / (user_avg + 1e-9)

    # Location risk
    is_unknown_location = 0 if txn.location in KNOWN_CITIES else 1

    # Check if location changed from usual
    usual_city = user_stats.get("usual_city")
    if usual_city and txn.location != usual_city:
        is_unknown_location = 1

    # Merchant risk
    is_unknown_merchant = 0 if txn.merchant in KNOWN_MERCHANTS else 1

    # Derived flags
    is_night  = 1 if (hour < 5 or hour >= 23) else 0
    is_rapid  = 1 if time_gap < 60 else 0

    return {
        "amount":               txn.amount,
        "hour":                 hour,
        "time_since_last_txn":  time_gap,
        "amount_vs_avg":        round(amount_vs_avg, 4),
        "is_unknown_location":  is_unknown_location,
        "is_unknown_merchant":  is_unknown_merchant,
        "is_night":             is_night,
        "is_rapid":             is_rapid,
        # Extra context (not model features)
        "user_avg_amount":      round(user_avg, 2),
        "txn_count":            user_stats["txn_count"]
    }

# ─────────────────────────────────────────
# 7. SHAP EXPLANATION
# ─────────────────────────────────────────

def get_shap_explanation(feature_df: pd.DataFrame) -> dict:
    shap_values = shap_explainer.shap_values(feature_df)
    values      = shap_values[0].tolist()

    explanation = {
        name: round(val, 6)
        for name, val in zip(FEATURES, values)
    }

    sorted_exp = dict(
        sorted(explanation.items(),
               key=lambda x: abs(x[1]), reverse=True)
    )

    readable = {
        "amount":               "Transaction amount",
        "hour":                 "Hour of transaction",
        "time_since_last_txn":  "Time since last transaction",
        "amount_vs_avg":        "Amount vs your usual spending",
        "is_unknown_location":  "Unknown location",
        "is_unknown_merchant":  "Unknown merchant",
        "is_night":             "Night time transaction",
        "is_rapid":             "Rapid transaction velocity",
    }

    top_reasons = []
    for feat, val in sorted_exp.items():
        if abs(val) > 0.001:
            direction = "increased" if val > 0 else "decreased"
            top_reasons.append(
                f"{readable.get(feat, feat)} "
                f"{direction} fraud risk "
                f"({'↑' if val > 0 else '↓'} {abs(val):.4f})"
            )

    return {
        "shap_values": sorted_exp,
        "base_value":  round(float(shap_explainer.expected_value), 6),
        "top_reasons": top_reasons[:3]
    }

# ─────────────────────────────────────────
# 8. AUTO TRAIN PERSONAL MODEL
# ─────────────────────────────────────────

def train_personal_model_bg(user_id: int):
    global iso_models
    print(f"\n  🔄 Training personal model for User {user_id}...")

    conn = get_db()
    df   = pd.read_sql_query(
        "SELECT * FROM transactions WHERE user_id=?",
        conn, params=(user_id,)
    )
    conn.close()

    df["timestamp"]          = pd.to_datetime(df["timestamp"])
    df["hour"]               = df["timestamp"].dt.hour
    df                       = df.sort_values("timestamp")
    df["time_since_last_txn"] = (
        df["timestamp"].diff().dt.total_seconds().fillna(0)
    )
    user_avg = df["amount"].mean()
    df["amount_vs_avg"]       = df["amount"] / (user_avg + 1e-9)
    df["is_unknown_location"] = (~df["location"].isin(KNOWN_CITIES)).astype(int)
    df["is_unknown_merchant"] = (~df["merchant"].isin(KNOWN_MERCHANTS)).astype(int)

    iso_features = [
        "amount", "hour", "time_since_last_txn",
        "amount_vs_avg", "is_unknown_location",
        "is_unknown_merchant"
    ]

    from sklearn.ensemble import IsolationForest as IF
    model = IF(n_estimators=100, contamination=0.05, random_state=42)
    model.fit(df[iso_features])

    path = f"models/isolation_forest_user_{user_id}.pkl"
    joblib.dump(model, path)
    iso_models[user_id] = model

    print(f"  ✅ Personal model ready for User {user_id} ({len(df)} txns)")

def maybe_train_model(user_id: int, txn_count: int):
    if txn_count == COLD_START_THRESHOLD \
       and user_id not in iso_models:
        t = threading.Thread(
            target=train_personal_model_bg,
            args=(user_id,),
            daemon=True
        )
        t.start()

# ─────────────────────────────────────────
# 9. MAIN SCORING ENDPOINT
# ─────────────────────────────────────────

def get_autoencoder_score(feature_array: pd.DataFrame) -> dict:
    X_scaled  = autoencoder_scaler.transform(feature_array.values)
    X_pred    = autoencoder.predict(X_scaled, verbose=0)
    recon_err = float(np.mean(np.square(X_scaled - X_pred)))
    is_anomaly = recon_err > AE_THRESHOLD

    return {
        "reconstruction_error": round(recon_err, 6),
        "threshold":            round(AE_THRESHOLD, 6),
        "is_anomaly":           is_anomaly,
        "anomaly_score_ratio":  round(recon_err / AE_THRESHOLD, 4)
    }
@app.post("/score")
def score_transaction(txn: Transaction):

    # Auto-create user if new
    ensure_user_exists(txn.user_id)

    # Get user history
    user_stats = get_user_stats(txn.user_id)

    # Compute all 8 features
    features = compute_features(
        txn, user_stats, txn.time_gap_override
    )

    # Build feature DataFrame — must match FEATURES order
    feature_df = pd.DataFrame([{f: features[f] for f in FEATURES}])

    # ── Isolation Forest ──
    iso = iso_models.get(txn.user_id, iso_global)
    iso_features = [
        "amount", "hour", "time_since_last_txn",
        "amount_vs_avg", "is_unknown_location",
        "is_unknown_merchant"
    ]
    iso_df = pd.DataFrame([{f: features[f] for f in iso_features}])

    if txn.user_id in iso_models:
        anomaly_label = int(iso.predict(iso_df)[0])
        anomaly_score = float(iso.score_samples(iso_df)[0])
        user_stage    = "personal_model"
    else:
        # Cold start — use global model
        anomaly_label = int(iso_global.predict(iso_df)[0])
        anomaly_score = float(iso_global.score_samples(iso_df)[0])
        remaining     = COLD_START_THRESHOLD - user_stats["txn_count"]
        user_stage    = f"cold_start ({remaining} txns until personal model)"

    # ── XGBoost ──
    xgb_prob = float(xgb_model.predict_proba(feature_df)[0][1])

    # ── Random Forest ──
    rf_prob  = float(rf_model.predict_proba(feature_df)[0][1])
    # ── Autoencoder ──
    ae_result  = get_autoencoder_score(feature_df)
    ae_anomaly = ae_result["is_anomaly"]

    # Add autoencoder signal to risk score
    # If autoencoder AND isolation forest both flag → very strong signal
    if ae_anomaly and anomaly_label == -1:
        # Both unsupervised models agree → add extra risk
        ae_risk_boost = 20
    elif ae_anomaly:
        # Only autoencoder flags it
        ae_risk_boost = 10
    else:
        ae_risk_boost = 0

    # ── Ensemble fraud probability (weighted average) ──
    fraud_prob = round((xgb_prob * 0.6) + (rf_prob * 0.4), 4)

    # ── SHAP ──
    shap_result = get_shap_explanation(feature_df)

    # ── Risk Engine ──
    status, risk_score, reasons = calculate_risk(
    amount        = features["amount"],
    hour          = features["hour"],
    time_gap      = features["time_since_last_txn"],
    anomaly       = anomaly_label,
    anomaly_score = anomaly_score,
    user_avg      = features["user_avg_amount"],
    fraud_prob    = fraud_prob
)

# ── Autoencoder boost on top of risk engine ──
    if ae_anomaly and anomaly_label == -1:
        # Both unsupervised models agree — very strong signal
        risk_score += 20
        reasons.append(
            f"Autoencoder + Isolation Forest both flagged "
            f"(error ratio: {ae_result['anomaly_score_ratio']:.2f}x threshold)"
        )
    elif ae_anomaly:
        # Only autoencoder flags it
        risk_score += 10
        reasons.append(
            f"Autoencoder flagged unusual pattern "
            f"(error: {ae_result['reconstruction_error']:.4f} "
            f"vs threshold {AE_THRESHOLD:.4f})"
        )

    # Recalculate decision after boost
    if risk_score >= 75:
        status = "BLOCK"
    elif risk_score >= 55:
        status = "DELAY"
    elif risk_score >= 30:
        status = "WARN"
    else:
        status = "APPROVE"

    # ── Save to DB ──
    save_transaction(txn)

    # ── Check if personal model should train ──
    maybe_train_model(txn.user_id, user_stats["txn_count"] + 1)

    return {
        "user_id":           txn.user_id,
        "amount":            txn.amount,
        "timestamp":         txn.timestamp,
        "location":          txn.location,
        "merchant":          txn.merchant,

        # Decisions
        "decision":          status,
        "risk_score":        risk_score,
        "fraud_probability": fraud_prob,

        # Individual model outputs
        "models": {
            "xgboost_prob":        round(xgb_prob, 4),
            "random_forest_prob":  round(rf_prob, 4),
            "ensemble_prob":       fraud_prob,
            "anomaly_label":       anomaly_label,
            "anomaly_score":       round(anomaly_score, 4),
        },

        # Explainability
        "reasons":          reasons,
        "shap_explanation": shap_result,

        # Context
        "user_stage":       user_stage,
        "features_used":    {
            f: features[f] for f in FEATURES
        },
        "user_context": {
            "avg_amount": features["user_avg_amount"],
            "txn_count":  features["txn_count"]
        }
    }

# ─────────────────────────────────────────
# 10. UTILITY ENDPOINTS
# ─────────────────────────────────────────

@app.get("/")
def health():
    return {
        "status":        "FinGuard API v4.0 running",
        "models_loaded": 1 + 1 + 1 + len(iso_models) + 1,
        "models": [
            "XGBoost",
            "RandomForest", 
            "IsolationForest (global)",
            f"IsolationForest (per-user x{len(iso_models)})",
            "Autoencoder"
        ],
        "features":      FEATURES,
        "shap":          "enabled",
        "autoencoder":   "enabled",
        "ae_threshold":  round(AE_THRESHOLD, 4),
        "cold_start_at": COLD_START_THRESHOLD
    }

@app.get("/user/{user_id}/status")
def user_status(user_id: int):
    stats     = get_user_stats(user_id)
    has_model = user_id in iso_models
    return {
        "user_id":              user_id,
        "txn_count":            stats["txn_count"],
        "has_personal_model":   has_model,
        "cold_start_remaining": max(0, COLD_START_THRESHOLD - stats["txn_count"]),
        "avg_amount":           round(stats["avg_amount"], 2),
        "usual_city":           stats["usual_city"]
    }

@app.get("/metrics")
def get_metrics():
    """Returns model evaluation metrics for dashboard."""
    try:
        with open("models/metrics.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "Run train_xgboost.py first"}

@app.post("/reload_models")
def reload_models():
    global iso_models
    iso_models = load_all_iso_models()
    return {
        "status":  "reloaded",
        "users":   list(iso_models.keys()),
        "count":   len(iso_models)
    }
