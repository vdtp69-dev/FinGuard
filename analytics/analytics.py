import sqlite3
from datetime import datetime

conn = sqlite3.connect('finguard.db') 
cursor = conn.cursor()

query = "SELECT timestamp FROM transactions WHERE user_id =?"

# 3. Run the query
cursor.execute(query,(1,))

results = cursor.fetchall()
print(f"Found {len(results)} transactions.")

print(f"Sample Raw Timestamp: {results[0][0]}")

hours = []
for row in results:
    time_string = row[0]
    
dt_object = datetime.strptime(time_string, "%Y-%m-%d %H:%M:%S.%f")
hours.append(dt_object.hour)
print(f"Extracted Hours: {hours[:10]} ...")
night_txns = [h for h in hours if h < 6 or h > 23]
print(f"Suspicious Late Night Transactions: {len(night_txns)}")




conn.close()
