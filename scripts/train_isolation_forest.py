import sqlite3
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

# 1️⃣ Connect to DB
conn = sqlite3.connect("finguard.db")

# 2️⃣ Load transactions
df = pd.read_sql_query("SELECT * FROM transactions", conn)
conn.close()

print("Loaded rows:", len(df))
print(df.head())

# 3️⃣ Convert timestamp to datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# 4️⃣ Extract hour
df['hour'] = df['timestamp'].dt.hour

# 5️⃣ Sort by user and time
df = df.sort_values(by=['user_id', 'timestamp'])

# 6️⃣ Calculate time difference (seconds)
df['time_since_last_txn'] = df.groupby('user_id')['timestamp'].diff().dt.total_seconds()

# First transaction will have NaN — fill with 0
df['time_since_last_txn'] = df['time_since_last_txn'].fillna(0)

print(df[['user_id','amount','hour','time_since_last_txn']].head())

models = {}

for user_id in df['user_id'].unique():
    
    user_data = df[df['user_id'] == user_id]
    
    # Features for model
    X = user_data[['amount', 'hour', 'time_since_last_txn']]
    
    # Create model
    model = IsolationForest(
        n_estimators=100,
        contamination=0.03,
        random_state=42
    )
    
    # Train
    model.fit(X)
    
    # Save model
    joblib.dump(model, f"isolation_forest_user_{user_id}.pkl")
    
    # Predict anomalies
    preds = model.predict(X)
    
    anomaly_count = (preds == -1).sum()
    
    print(f"User {user_id} -> Anomalies detected:", anomaly_count)
    
    models[user_id] = model
    user_data = user_data.copy()
    user_data['anomaly'] = preds

    print(user_data[user_data['anomaly'] == -1][
    ['amount', 'hour', 'time_since_last_txn']
    ].head())
    scores = model.decision_function(X)
    user_data['anomaly_score'] = scores
    print(user_data[user_data['anomaly'] == -1][
    ['amount', 'hour', 'time_since_last_txn', 'anomaly_score']
    ].head())
df['anomaly'] = 0
df['anomaly_score'] = 0.0

for user_id in df['user_id'].unique():
    model = joblib.load(f"isolation_forest_user_{user_id}.pkl")
    user_data = df[df['user_id'] == user_id]
    X = user_data[['amount', 'hour', 'time_since_last_txn']]
    
    preds = model.predict(X)
    scores = model.decision_function(X)
    
    df.loc[df['user_id'] == user_id, 'anomaly'] = preds
    df.loc[df['user_id'] == user_id, 'anomaly_score'] = scores




