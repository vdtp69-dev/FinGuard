import anthropic
import os

def explain_fraud_decision(scoring_result: dict, transaction: dict, user_history: list) -> str:
    """
    Generates a natural language explanation of a fraud decision using Claude.
    Falls back to a rule-based template if no API key is set.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    amount = transaction.get("amount", 0)
    merchant = transaction.get("merchant", "Unknown")
    timestamp = transaction.get("timestamp", "00:00")
    
    if isinstance(timestamp, str) and "T" in timestamp:
        hour = timestamp.split("T")[1].split(":")[0]
    else:
        hour = "00"
        
    decision = scoring_result.get("decision", "UNKNOWN")
    risk_score = scoring_result.get("risk_score", 0)
    
    models = scoring_result.get("models", {})
    xgb_prob = models.get("xgboost_prob", 0)
    rf_prob = models.get("random_forest_prob", 0)
    lstm_prob = models.get("lstm_prob", 0)
    
    top_features = scoring_result.get("top_shap_features", "amount_vs_avg, is_rapid, location")
    
    user_avg = 0
    if user_history and len(user_history) > 0:
        amounts = [t.get("amount", 0) for t in user_history if isinstance(t, dict)]
        user_avg = sum(amounts) / len(amounts) if amounts else 0
        
    user_avg_str = f"₹{user_avg:.2f}"
    
    if not api_key:
        return _fallback_explanation(decision, amount, merchant, top_features, user_avg_str)
        
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""
You are a fraud detection assistant explaining a transaction decision to a bank customer.
Transaction: ₹{amount} to {merchant} at {hour}:00
Decision: {decision} (Risk score: {risk_score}/130)
Model signals: XGBoost={xgb_prob:.0%}, RF={rf_prob:.0%}, LSTM={lstm_prob:.0%}
Top risk factors: {top_features}
User's normal behaviour: avg amount {user_avg_str}

Write exactly 3 short paragraphs:
1. What happened (1-2 sentences, plain English, no jargon)
2. What the models detected (translate the numbers into human language)
3. What to do next (specific action based on decision level)
Total must be under 150 words.
"""
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            temperature=0.3,
            system="You are a helpful banking assistant.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    except Exception as e:
        print(f"Anthropic API error: {e}")
        return _fallback_explanation(decision, amount, merchant, top_features, user_avg_str)

def _fallback_explanation(decision, amount, merchant, features, user_avg):
    action = "This transaction was safely approved."
    if decision in ["BLOCK", "DELAY"]:
        action = "We temporarily blocked this transaction to secure your account."
    elif decision == "WARN":
        action = "We flagged this as slightly unusual, but it went through."
        
    p1 = f"An attempt was made to spend ₹{amount} at {merchant}. {action}"
    p2 = f"Our AI detected anomalies primarily driven by: {features}. This contrasted with your typical average spend of {user_avg}."
    p3 = "No immediate action is needed if you recognize this." if decision == "APPROVE" else "Please visit the FinGuard app to verify this transaction immediately."
    
    return f"{p1}\n\n{p2}\n\n{p3}"
