import sqlite3
import matplotlib.pyplot as plt
import pandas as pd

# 1. Connect
conn = sqlite3.connect('finguard.db')

# 2. Get Data for User 1 (The Student)
df1 = pd.read_sql("SELECT timestamp FROM transactions WHERE user_id = 1", conn)
df1['hour'] = pd.to_datetime(df1['timestamp']).dt.hour

# 3. Get Data for User 2 (The Night Owl)
df2 = pd.read_sql("SELECT timestamp FROM transactions WHERE user_id = 2", conn)
df2['hour'] = pd.to_datetime(df2['timestamp']).dt.hour

conn.close()

# 4. Plot Side-by-Side
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Plot User 1
axes[0].hist(df1['hour'], bins=24, range=(0, 24), color='#4CAF50', edgecolor='black')
axes[0].set_title('User 1: The Student (Daytime Active)')
axes[0].set_xlabel('Hour of Day')
axes[0].set_ylabel('Transactions')
axes[0].grid(axis='y', alpha=0.3)

# Plot User 2
axes[1].hist(df2['hour'], bins=24, range=(0, 24), color='#FF5722', edgecolor='black')
axes[1].set_title('User 2: The Night Owl (Night Active)')
axes[1].set_xlabel('Hour of Day')
axes[1].grid(axis='y', alpha=0.3)

plt.tight_layout()
print("Opening Comparison Graph...")
plt.show()