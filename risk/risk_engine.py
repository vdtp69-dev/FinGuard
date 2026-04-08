# risk/risk_engine.py — updated to include fraud_probability

def calculate_risk(
    amount,
    hour,
    time_gap,
    anomaly,
    anomaly_score,
    user_avg,
    fraud_prob=0.0,
    # Extra ML-derived context (so the demo trajectory changes with location/merchant).
    is_unknown_location=0,
    is_unknown_merchant=0,
    device_trust_score=1.0,
    merchant_risk_score=0.0,
):

    import math
    if fraud_prob is None or math.isnan(fraud_prob):
        fraud_prob = 0.0

    risk = 0
    reasons = []

    # ── Isolation Forest signal ──
    if anomaly == -1:
        risk += 35
        reasons.append("Isolation Forest flagged unusual behavior")

    if anomaly_score < -0.08:
        risk += 15
        reasons.append("Strong anomaly severity score")

    # ── Ensemble model signal ──
    if fraud_prob > 0.7:
        risk += 40
        reasons.append(f"Ensemble model high fraud probability ({fraud_prob:.0%})")
    elif fraud_prob > 0.4:
        risk += 20
        reasons.append(f"Ensemble model moderate fraud probability ({fraud_prob:.0%})")

    # ── Context signals (explicit) ──
    # These are derived from the same features used by the ML models, but we
    # include them here so the "location" dropdown visibly affects outcomes.
    if is_unknown_location == 1:
        risk += 18
        reasons.append("Unknown / unusual location context")

    if is_unknown_merchant == 1:
        risk += 12
        reasons.append("Unknown / unusual merchant context")

    if device_trust_score is not None:
        try:
            if float(device_trust_score) < 0.5:
                risk += 10
                reasons.append(f"Low device trust score ({float(device_trust_score):.2f})")
        except Exception:
            pass

    if merchant_risk_score is not None:
        try:
            if float(merchant_risk_score) > 0.6:
                risk += 10
                reasons.append(f"High merchant risk score ({float(merchant_risk_score):.2f})")
        except Exception:
            pass

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