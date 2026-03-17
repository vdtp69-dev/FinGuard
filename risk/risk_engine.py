# risk/risk_engine.py — updated to include fraud_probability

def calculate_risk(amount, hour, time_gap, anomaly, 
                   anomaly_score, user_avg, fraud_prob=0.0):

    risk = 0
    reasons = []

    # ── Isolation Forest signal ──
    if anomaly == -1:
        risk += 35
        reasons.append("Isolation Forest flagged unusual behavior")

    if anomaly_score < -0.08:
        risk += 15
        reasons.append("Strong anomaly severity score")

    # ── XGBoost signal (now included!) ──
    if fraud_prob > 0.7:
        risk += 40
        reasons.append(f"XGBoost high fraud probability ({fraud_prob:.0%})")
    elif fraud_prob > 0.4:
        risk += 20
        reasons.append(f"XGBoost moderate fraud probability ({fraud_prob:.0%})")

    # ── Amount deviation ──
    if user_avg > 0:
        if amount > user_avg * 10:
            risk += 30
            reasons.append(f"Amount is 10x above your average (₹{user_avg:,.0f})")
        elif amount > user_avg * 5:
            risk += 20
            reasons.append(f"Amount is 5x above your average (₹{user_avg:,.0f})")

    # ── Velocity ──
    if time_gap < 30:
        risk += 35
        reasons.append(f"Extremely rapid transaction ({time_gap:.0f}s gap)")
    elif time_gap < 60:
        risk += 25
        reasons.append(f"Very fast transaction ({time_gap:.0f}s gap)")
    elif time_gap < 120:
        risk += 10
        reasons.append(f"Quick transaction ({time_gap:.0f}s gap)")

    # ── Unusual hour ──
    if hour < 5:
        risk += 20
        reasons.append(f"Transaction at {hour}:00 AM — unusual hour")
    elif hour < 6:
        risk += 10
        reasons.append("Late night transaction")

    # ── Decision tiers ──
    if risk < 30:
        status = "APPROVE"
    elif risk < 55:
        status = "WARN"
    elif risk < 75:
        status = "DELAY"
    else:
        status = "BLOCK"

    return status, risk, reasons