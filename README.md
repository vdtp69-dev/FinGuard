# FinGuard — Hybrid Fraud Detection System

## Project Structure
```
FinGuard/
├── data/
│   └── finguard.db          # SQLite database with 2200 transactions
├── models/
│   ├── isolation_forest_user_1.pkl
│   ├── isolation_forest_user_2.pkl
│   ├── isolation_forest_user_3.pkl
│   └── xgboost_fraud_model.pkl
├── scripts/
│   ├── setup_finguard_database.py   # generates data
│   ├── train_isolation_forest.py    # trains IF models
│   ├── train_xgboost.py             # trains XGBoost
│   └── inject_fraud.py              # injects fraud samples
├── risk/
│   └── risk_engine.py       # scoring logic
├── analytics/
│   └── analytics.py
├── feature_velocity.py
└── requirements.txt
```

## What is already done
- 2200 synthetic UPI transactions across 3 user personas
  - User 1: Aman (Student) — ₹50 to ₹500, daytime
  - User 2: Riya (Night Gamer) — ₹500 to ₹5000, night hours
  - User 3: Kabir (VIP Traveler) — ₹10k to ₹100k, multi-city
- Isolation Forest trained separately per user (3 models)
- XGBoost fraud classifier trained on labeled data
- Risk Engine with 5 signals → APPROVE / WARN / DELAY / BLOCK

## Features used by models
- `amount` — transaction amount
- `hour` — hour of transaction
- `time_since_last_txn` — seconds since last transaction

## For the FastAPI person
- Load models from `models/` using `joblib.load()`
- Database is at `data/finguard.db`
- Risk engine is at `risk/risk_engine.py`
- Call `calculate_risk(amount, hour, time_gap, anomaly, anomaly_score, user_avg)`
- It returns `(status, risk_score, reasons)`

## For the Streamlit person
- API will run at `http://127.0.0.1:8000`
- Main endpoint: `POST /score`
- Response includes: decision, risk_score, fraud_probability, anomaly_label, reasons

## Setup — run this first
```bash
pip install -r requirements.txt
python scripts/setup_finguard_database.py
python scripts/train_isolation_forest.py
python scripts/train_xgboost.py
```

## Models
All 4 models are pre-trained and saved as `.pkl` files.
No need to retrain unless you change the data.