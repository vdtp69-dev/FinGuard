import sqlite3
from datetime import datetime, timedelta

# 1. Connect
conn = sqlite3.connect('finguard.db')
cursor = conn.cursor()

print("💉 Injecting 'Machine Gun' Fraud Attack...")

# 2. Create the "Attack" Data
# We will insert 5 transactions, each 2 seconds apart
base_time = datetime.now()
fraud_data = []

for i in range(5):
    # Time increases by just 2 seconds each loop
    txn_time = base_time + timedelta(seconds=(i * 2)) 
    fraud_data.append((1, 5000.00, txn_time, "Mumbai", "Hacker_Store"))

# 3. Insert into Database
cursor.executemany("""
    INSERT INTO transactions (user_id, amount, timestamp, location, merchant)
    VALUES (?, ?, ?, ?, ?)
""", fraud_data)

conn.commit()
conn.close()

print("✅ INJECTED: 5 fast transactions added.")