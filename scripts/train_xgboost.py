import sqlite3
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

# connect to database
conn = sqlite3.connect("data/finguard.db")

df = pd.read_sql_query("SELECT * FROM transactions", conn)

conn.close()

# convert timestamp
df["timestamp"] = pd.to_datetime(df["timestamp"])

# feature engineering
df["hour"] = df["timestamp"].dt.hour

df = df.sort_values(["user_id", "timestamp"])

df["time_since_last_txn"] = (
    df.groupby("user_id")["timestamp"]
    .diff()
    .dt.total_seconds()
)

df["time_since_last_txn"] = df["time_since_last_txn"].fillna(0)

# -----------------------------
# CREATE FRAUD LABEL
# -----------------------------

df["fraud"] = 0

# simple fraud rule
df.loc[df["amount"] > 20000, "fraud"] = 1

# features
X = df[["amount", "hour", "time_since_last_txn"]]

y = df["fraud"]

# train test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# train model
model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.1,
    subsample=0.8
)

model.fit(X_train, y_train)

# evaluate
preds = model.predict(X_test)

print(classification_report(y_test, preds))

# save model
joblib.dump(model, "models/xgboost_fraud_model.pkl")

print("XGBoost model saved.")