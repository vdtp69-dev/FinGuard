
```markdown
# 🛡️ FinGuard — Hybrid Fraud Detection System

A real-time UPI transaction fraud detection system combining multiple ML models, 
deep learning, and explainable AI. Built as a Mini Project for SY Computer Engineering, 
K.J. Somaiya Institute of Technology.

---

## What FinGuard does

Every UPI transaction is scored in real time using 4 models working together:
- Flags unusual behavior specific to each user
- Gives a risk score from 0 to 130+
- Makes a decision — APPROVE, WARN, DELAY, or BLOCK
- Explains exactly WHY in plain English using SHAP

---

## Architecture

```
Transaction (amount, hour, location, merchant)
        ↓
Feature Engineering (8 features)
        ↓
┌─────────────────────────────────────────┐
│  Isolation Forest (per-user)            │  → anomaly label + score
│  XGBoost Classifier                     │  → fraud probability
│  Random Forest Classifier               │  → fraud probability  
│  Autoencoder (neural network)           │  → reconstruction error
└─────────────────────────────────────────┘
        ↓
Ensemble + Risk Engine
        ↓
SHAP Explainability
        ↓
Decision + Reasons
```

---

## Models

| Model | Type | AUC-ROC | Purpose |
|-------|------|---------|---------|
| Isolation Forest (×3) | Unsupervised | — | Per-user anomaly detection |
| XGBoost | Supervised | 0.9370 | Fraud classification |
| Random Forest | Supervised | 0.9605 | Fraud classification |
| Autoencoder | Deep Learning | 0.9258 | Neural anomaly detection |
| **Hybrid** | **Ensemble** | **0.9600+** | **All models combined** |

---

## Features used

| Feature | Description |
|---------|-------------|
| `amount` | Transaction amount in ₹ |
| `hour` | Hour of day (0–23) |
| `time_since_last_txn` | Seconds since previous transaction |
| `amount_vs_avg` | This amount ÷ user's historical average |
| `is_unknown_location` | 1 if city not in user's known cities |
| `is_unknown_merchant` | 1 if merchant is unrecognized |
| `is_night` | 1 if transaction between 11 PM and 5 AM |
| `is_rapid` | 1 if gap from last transaction < 60 seconds |

---

## Dataset

- 2,200 synthetic UPI transactions
- 3 user personas: Student (Aman), Night Gamer (Riya), VIP Traveler (Kabir)
- 5.5% fraud rate with 4 realistic fraud patterns:
  - Night + large amount
  - Unknown location
  - Rapid velocity (bot attack)
  - Account takeover pattern
- SMOTE applied during training to balance classes

---

## Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.12 |
| Database | SQLite |
| ML Models | Scikit-learn, XGBoost |
| Deep Learning | TensorFlow / Keras |
| Explainability | SHAP |
| Class Balancing | imbalanced-learn (SMOTE) |
| API | FastAPI + Uvicorn |
| Dashboard | Streamlit + Plotly |
| Data | Pandas, NumPy |
| Model Storage | Joblib |

---

## Project Structure

```
FinGuard/
├── api.py                          # FastAPI backend — all endpoints
├── dashboard.py                    # Streamlit dashboard — 6 pages
├── risk/
│   └── risk_engine.py              # Risk scoring logic
├── scripts/
│   ├── setup_finguard_database.py  # Generate synthetic dataset
│   ├── train_xgboost.py            # Train XGBoost + RF + Isolation Forest
│   ├── train_autoencoder.py        # Train neural network autoencoder
│   └── inject_fraud.py             # Fraud injection utilities
├── models/
│   ├── xgboost_fraud_model.pkl
│   ├── random_forest_fraud_model.pkl
│   ├── isolation_forest_user_1.pkl
│   ├── isolation_forest_user_2.pkl
│   ├── isolation_forest_user_3.pkl
│   ├── isolation_forest_global.pkl
│   ├── autoencoder.keras
│   ├── autoencoder_scaler.pkl
│   ├── autoencoder_config.json
│   ├── feature_list.json
│   ├── metrics.json
│   └── charts/
│       ├── auc_roc.png
│       ├── confusion_matrix.png
│       ├── feature_importance.png
│       ├── autoencoder_loss.png
│       └── autoencoder_distribution.png
├── data/
│   └── finguard.db                 # SQLite database
├── analytics/
│   ├── analytics.py
│   ├── compare_users.py
│   └── visualize_data.py
├── feature_velocity.py
├── requirements.txt
└── README.md
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/YOURNAME/FinGuard.git
cd FinGuard
```

**2. Create virtual environment**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Generate dataset**
```bash
python scripts/setup_finguard_database.py
```

**5. Train all models**
```bash
python scripts/train_xgboost.py
python scripts/train_autoencoder.py
```

**6. Start the API**
```bash
uvicorn api:app --reload
```

**7. Start the dashboard** (new terminal)
```bash
streamlit run dashboard.py
```

---

## Dashboard Pages

| Page | What it shows |
|------|---------------|
| 🔍 Score a Transaction | Live fraud scoring with SHAP explanation |
| 📋 Transaction Data | Browse all 2,200 transactions per user |
| 👤 User Profiles | Behavioral patterns for each persona |
| 📡 Live Feed | Real-time auto-scoring stream |
| 📊 Model Intelligence | AUC-ROC, confusion matrix, model comparison |
| 💥 Attack Simulation | Simulate fraud attacks, see catch rate |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check — models loaded |
| POST | `/score` | Score a transaction |
| GET | `/user/{id}/status` | User onboarding status |
| GET | `/metrics` | Model evaluation metrics |
| POST | `/reload_models` | Reload models without restart |

---

## Our Unique Contributions

**1. Per-user Isolation Forest** — Most fraud systems use one global model. We train a separate Isolation Forest for each user persona. ₹50,000 is normal for Kabir but extreme for Aman — the same model cannot handle both.

**2. Per-transaction SHAP** — Research papers use SHAP for global feature importance. We run SHAP on every single transaction, giving individual explanations for every decision.

**3. 4-model ensemble** — Isolation Forest (unsupervised) + XGBoost (supervised) + Random Forest (ensemble) + Autoencoder (deep learning). Each catches different fraud types that others miss.

**4. Automatic user onboarding** — New users are handled automatically. XGBoost scores cold-start users. After 50 transactions a personal Isolation Forest trains in the background with no API restart needed.

---

## Research References

- Borketey et al. 2024 — Hybrid ML fraud detection (SSRN)
- Rani et al. 2024 — XGBoost + SMOTE for UPI fraud (IEEE)
- IBM FraudGT 2024 — Graph neural networks for fraud rings (ICAIF)
- Frontiers in AI 2025 — SHAP explainability in financial fraud
- ArXiv 2025 — Deep learning systematic review for fraud detection

---

## Team

- Aarya Baviskar
- Samya Chheda  
- Vihaan Dgli
- Anagh Mundhada

**K.J. Somaiya Institute of Technology**  
Department of Computer Engineering  
Academic Year 2025–2026
