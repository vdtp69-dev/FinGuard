import sqlite3
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import StandardScaler
from torch.utils.data import TensorDataset, DataLoader
import joblib
import os
import json

print("=" * 50)
print("Training LSTM Sequence Model")
print("=" * 50)

# Connect to DB
conn = sqlite3.connect("data/finguard.db")
df = pd.read_sql_query("SELECT * FROM transactions", conn)
conn.close()

df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
df = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)

# Feature engineering
df["hour"] = df["timestamp"].dt.hour
df["time_since_last_txn"] = df.groupby("user_id")["timestamp"].diff().dt.total_seconds().fillna(0)

known_cities = ["Mumbai", "Delhi", "Bangalore", "London", "Dubai"]
df["is_unknown_location"] = (~df["location"].isin(known_cities)).astype(float)

known_merchants = ["Swiggy", "Zomato", "Amazon", "BookStore", "Steam", "EpicGames", "LuxuryMall", "Airline", "Hotel", "Flipkart"]
df["is_unknown_merchant"] = (~df["merchant"].isin(known_merchants)).astype(float)

df["is_night"] = ((df["hour"] < 5) | (df["hour"] >= 23)).astype(float)
df["is_rapid"] = (df["time_since_last_txn"] < 60).astype(float)
df["is_round_amount"] = ((df["amount"] % 100 == 0) | (df["amount"] % 50 == 0)).astype(float)

np.random.seed(42)
base_trust = 1.0 - (df["is_unknown_location"] * 0.4) - (df["is_night"] * 0.2)
df["device_trust_score"] = (base_trust + np.random.normal(0, 0.1, len(df))).clip(0.1, 1.0).astype(float)

merchant_risks = {
    "Swiggy": 0.2, "Zomato": 0.2, "Amazon": 0.1, "BookStore": 0.1,
    "Steam": 0.5, "EpicGames": 0.5, "LuxuryMall": 0.8,
    "Airline": 0.7, "Hotel": 0.6, "Flipkart": 0.2
}
df["merchant_risk_score"] = df["merchant"].map(merchant_risks).fillna(0.9).astype(float)

# Scale
scaler = StandardScaler()
df[["amount_norm", "hour_norm", "time_gap_norm"]] = scaler.fit_transform(
    df[["amount", "hour", "time_since_last_txn"]]
)
joblib.dump(scaler, "models/lstm_scaler.pkl")

features = [
    "amount_norm", "hour_norm", "time_gap_norm", 
    "is_unknown_location", "is_unknown_merchant",
    "is_night", "is_rapid", "is_round_amount",
    "device_trust_score", "merchant_risk_score"
]
SEQ_LEN = 10

X, y = [], []

for uid, group in df.groupby("user_id"):
    vals = group[features].values
    labels = group["is_fraud"].values
    
    for i in range(len(group)):
        if i < SEQ_LEN - 1:
            pad_len = SEQ_LEN - 1 - i
            pad = np.zeros((pad_len, len(features)))
            seq = np.vstack([pad, vals[:i+1]])
        else:
            seq = vals[i - SEQ_LEN + 1 : i + 1]
            
        X.append(seq)
        y.append(labels[i])

X = np.array(X, dtype=np.float32)
y = np.array(y, dtype=np.float32)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

class FraudLSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(input_size=10, hidden_size=32, num_layers=1, batch_first=True)
        self.fc = nn.Linear(32, 1)

    def forward(self, x):
        _, (hn, _) = self.lstm(x)
        out = self.fc(hn[-1])
        return out.squeeze()

model = FraudLSTM().to(device)

# Weight for class imbalance
num_pos = sum(y)
num_neg = len(y) - num_pos
pos_weight = torch.tensor([num_neg / max(1, num_pos)]).to(device)
criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
optimizer = optim.Adam(model.parameters(), lr=0.005)

X_tensor = torch.tensor(X).to(device)
y_tensor = torch.tensor(y).to(device)
dataset = TensorDataset(X_tensor, y_tensor)
loader = DataLoader(dataset, batch_size=64, shuffle=True)

print("Starting training...")
model.train()
for epoch in range(15):
    epoch_loss = 0
    for batch_X, batch_y in loader:
        optimizer.zero_grad()
        logits = model(batch_X)
        loss = criterion(logits, batch_y)
        loss.backward()
        optimizer.step()
        epoch_loss += loss.item()
    if (epoch + 1) % 5 == 0:
        print(f"Epoch {epoch+1:02d}/15 - Loss: {epoch_loss/len(loader):.4f}")

model.eval()
with torch.no_grad():
    preds = torch.sigmoid(model(X_tensor)).cpu().numpy()

from sklearn.metrics import roc_auc_score
auc = roc_auc_score(y, preds)
print(f"LSTM Train AUC-ROC: {auc:.4f}")

torch.save(model.state_dict(), "models/lstm_model.pt")
print("✅ Saved models/lstm_model.pt and models/lstm_scaler.pkl")

# Update metrics.json
try:
    with open("models/metrics.json", "r") as f:
        metrics = json.load(f)
except:
    metrics = {}

metrics["lstm"] = {
    "auc_roc": round(auc, 4),
    "precision": "-",
    "recall": "-"
}

with open("models/metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)
print("✅ Updated models/metrics.json")
