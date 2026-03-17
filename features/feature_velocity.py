import sqlite3
import pandas as pd

# 1. Load Data
conn = sqlite3.connect('finguard.db')
df = pd.read_sql("SELECT * FROM transactions WHERE user_id = 1", conn)
conn.close()

# 2. CONVERT TO TIME (The Blank)
# Hint: In the video, Corey used pd.to_......(df['column_name'])
df['timestamp'] = pd.to_datetime(df['timestamp'])

# 3. SORT (Crucial!)
# You must sort by time, or the math will be wrong
df = df.sort_values('timestamp')

# 4. CALCULATE VELOCITY (The Math)
# diff() subtracts the current row from the previous row
df['time_diff'] = df['timestamp'].diff().dt.total_seconds()

# 5. THE TRAP
# Show me transactions that happened less than 10 seconds apart
fast_txns = df[df['time_diff'] < 10]

print(f"Suspicious 'Fast' Transactions Found: {len(fast_txns)}")
print(fast_txns[['timestamp', 'amount', 'time_diff']])