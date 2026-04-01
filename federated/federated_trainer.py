import numpy as np
import json
import time
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from api import get_db
import pandas as pd

class FederatedClient:
    def __init__(self, user_id):
        self.user_id = user_id
        self.model = LogisticRegression(max_iter=100)
        self.coef_ = None
        self.intercept_ = None
        
        # Load local data
        conn = get_db()
        self.df = pd.read_sql_query("SELECT amount, is_fraud FROM transactions WHERE user_id=?", conn, params=(user_id,))
        conn.close()
        
        # Simple encoding for features: just amount and static noise for demo
        # If there are no fraud examples, we inject a synthetic one so LR can fit
        if self.df.empty or len(self.df["is_fraud"].unique()) < 2:
            synthetic = pd.DataFrame([
                {"amount": 50.0, "is_fraud": 0},
                {"amount": 50000.0, "is_fraud": 1}
            ])
            self.df = pd.concat([self.df, synthetic], ignore_index=True)
            
        self.X = self.df[["amount"]].values
        self.y = self.df["is_fraud"].values

    def train_round(self, global_coef, global_intercept):
        if global_coef is not None:
            self.model.coef_ = global_coef
            self.model.intercept_ = global_intercept
            
        self.model.fit(self.X, self.y)
        self.coef_ = self.model.coef_
        self.intercept_ = self.model.intercept_
        return self.coef_, self.intercept_

def run_federated_training(rounds=10):
    clients = [FederatedClient(1), FederatedClient(2), FederatedClient(3)]
    
    global_coef = None
    global_intercept = None
    
    history = []
    
    # We will compute pseudo-AUC for full data
    X_global = np.vstack([c.X for c in clients])
    y_global = np.hstack([c.y for c in clients])
    central_model = LogisticRegression().fit(X_global, y_global)
    baseline_auc = roc_auc_score(y_global, central_model.predict_proba(X_global)[:, 1])
    
    for r in range(1, rounds + 1):
        round_coefs = []
        round_intercepts = []
        
        for client in clients:
            w, b = client.train_round(global_coef, global_intercept)
            round_coefs.append(w)
            round_intercepts.append(b)
            
        # FedAvg
        global_coef = np.mean(round_coefs, axis=0)
        global_intercept = np.mean(round_intercepts, axis=0)
        
        # Compute current global pseudo-AUC
        temp_model = LogisticRegression()
        temp_model.classes_ = np.array([0, 1])
        temp_model.coef_ = global_coef
        temp_model.intercept_ = global_intercept
        
        try:
            preds = temp_model.predict_proba(X_global)[:, 1]
            auc = roc_auc_score(y_global, preds)
        except:
            auc = 0.5
            
        history.append({
            "round": r,
            "auc": round(auc, 4)
        })
        
        yield json.dumps({
            "round": r,
            "auc": round(auc, 4),
            "centralized_auc": round(baseline_auc, 4),
            "status": "training"
        }) + "\n"
        
        time.sleep(0.5) # Simulate training delay
        
    final_res = {
        "status": "complete",
        "final_auc": history[-1]["auc"],
        "centralized_auc": round(baseline_auc, 4),
        "history": history
    }
    
    with open("models/federated_results.json", "w") as f:
        json.dump(final_res, f)
        
    yield json.dumps(final_res) + "\n"
