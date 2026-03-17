import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime

# 1. Connect and Fetch Data
conn = sqlite3.connect('finguard.db')
cursor = conn.cursor()

# Get all timestamps
cursor.execute("SELECT timestamp FROM transactions WHERE user_id = 1")
results = cursor.fetchall()
conn.close()

# 2. Process Data (Extract Hours)
hours = []
for row in results:
    # Convert string to time object
    # The format matches your output: "2026-01-11 00:27:54.345754"
    dt_object = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f")
    hours.append(dt_object.hour)

# 3. The Visualization (The Magic Part)
plt.figure(figsize=(10, 6))

# Create a Histogram (24 bins = 24 hours in a day)
plt.hist(hours, bins=24, range=(0, 24), color='#4CAF50', edgecolor='black')

# Add Labels (Make it look professional)
plt.title('User 1 Spending Habits (Time of Day)', fontsize=16)
plt.xlabel('Hour of Day (0 = Midnight, 12 = Noon, 23 = 11 PM)', fontsize=12)
plt.ylabel('Number of Transactions', fontsize=12)
plt.grid(axis='y', alpha=0.5)

# 4. Show the Graph
print("Opening Graph...")
plt.show()