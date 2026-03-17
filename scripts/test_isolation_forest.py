import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
from risk.risk_engine import calculate_risk

model = joblib.load("models/isolation_forest_user_1.pkl")

txn = [[50000, 2, 30]]

prediction = model.predict(txn)
score = model.decision_function(txn)

status, risk, reasons = calculate_risk(
    amount=50000,
    hour=2,
    time_gap=30,
    anomaly=prediction[0],
    anomaly_score=score[0],
    user_avg=200
)

print("STATUS:", status)
print("RISK SCORE:", risk)
print("REASONS:", reasons)