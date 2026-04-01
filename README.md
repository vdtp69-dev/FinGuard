# FinGuard
**Real-Time UPI Fraud Detection Platform**

FinGuard is a hybrid, multi-model fraud detection system combining traditional gradient boosting arrays (XGBoost & Random Forest) with advanced Sequence Models (LSTMs for time-series memory) and Unsupervised anomaly detection manifolds (Autoencoders & Isolation Forests) for high-scale, ultra-low-latency financial environments.

---

## Architecture Diagram
```ascii
[ User Transaction ] 
        |
        v
[ Feature Engine ] -> [ Amount vs Avg, Rapid Flags, Geolocation, Time Gaps ... ]
        |
        +-- (Static Rules / Known Bad Entities)
        |
        +-----------------------------------+
        |                                   |
[ Dense ML Layer ]                  [ Sparse & Unknown Layer ]
 - XGBoost: Primary Classifier        - Recurrent LSTM: Behavioral Sequences
 - Random Forest: Ensemble Backup     - Autoencoder: Structural Anomalies
                                      - User-Specific Isolation Forests (per ID)
        |                                   |
        +-----------------------------------+
        |
[ Risk Aggregation Engine (FedAvg Server) ] -> [ Financial Impact Assessor ]
        |
[ Claude LLM Explicator ]
        |
    [ React UI ]

```

---

## 🚀 Quick Start (Docker)
Ensure Docker and Docker Compose are installed.
```bash
ANTHROPIC_API_KEY="sk-..." docker-compose up --build
```
*API available at `http://localhost:8000`*


## 🛠 Manual Dev Setup

**1. Start the Machine Learning Backend FastAPI Service:**
```bash
# In FinGuard root
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

**2. Start the React Dashboards:**
```bash
# In new terminal window
cd finguard-ui
npm install
npm run dev
```

---

## 📡 Core API Integration Points

#### Block or Approve Transactions (Main Payload Hook)
```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "amount": 5400,
    "timestamp": "2026-03-24T03:15:00",
    "location": "Russia",
    "merchant": "LuxuryMall"
  }'
```

#### Fetch SHAP Logic Explainability
```bash
curl http://localhost:8000/explain/12  # returns generative NL from Claude
```

#### Data Pipeline & Topologies
```bash
# Realtime socket connections
ws://localhost:8000/ws/live_feed

# Full AI topology mapping (D3.js integration)
curl http://localhost:8000/graph_data

# Performance Matrices
curl http://localhost:8000/model_metrics
```


---

## 📊 Evaluation Matrix

| Sub-Engine Blueprint | Primary Mission Vector | Operating Baseline |
|----------------------|------------------------|--------------------|
| **XGBoost Classifier** | Main classification layer | AUC-ROC: ~0.999 |
| **Random Forest** | Anti-overfitting validation | AUC-ROC: ~0.998 |
| **Recurrent LSTM** | Memory series vectoring | High Context Awareness |
| **Autoencoders** | High-dimensional clustering | -0.585 Recon. Error Bound |
| **Isolation Forest** | Unknown structural density | User-Specific Bounds |

---

## 🖼 Dashboard Screenshots

> *[Placeholders for UI Screenshots]*

- Command Center & WebSocket Sink Array
- Transaction Profiler & Vector Tuning Sliders
- AI Neural Network Visualizer (NetworkGraph mapping)
- Federated Learning Deployment Sync Module

---
*(c) FinGuard Defensive Arrays*
