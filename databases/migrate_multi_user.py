import sqlite3
import random
from datetime import datetime, timedelta

# 1. Connect and Clean
conn = sqlite3.connect('finguard.db')
cursor = conn.cursor()
cursor.execute("DELETE FROM transactions") 
print("Old data wiped. Generating Multi-User Ecosystem...")

def generate_user_data(user_id, num_txns, min_amt, max_amt, active_hours, cities):
    data = []
    start_date = datetime.now() - timedelta(days=60)
    
    print(f"Generating User {user_id} ({num_txns} txns)...")
    
    for _ in range(num_txns):
        # 1. Time Logic (Personalized)
        if random.random() < 0.9: # 90% matches their habit
            hour = random.choice(active_hours)
        else:
            hour = random.randint(0, 23) # 10% random
            
        # 2. Amount Logic (Personalized)
        amount = round(random.uniform(min_amt, max_amt), 2)
        
        # 3. Location Logic
        city = random.choice(cities)
        
        # Build Timestamp
        minute = random.randint(0, 59)
        day_offset = random.randint(0, 60)
        txn_time = start_date + timedelta(days=day_offset)
        txn_time = txn_time.replace(hour=hour, minute=minute)
        
        data.append((user_id, amount, txn_time, city, "Merchant_X"))
        
    return data

# --- DEFINING PERSONAS ---

# User 1: The Student (Daytime, Low Budget, Mumbai only)
user1_data = generate_user_data(
    user_id=1, 
    num_txns=1000, 
    min_amt=50, max_amt=500, 
    active_hours=list(range(8, 23)), # 8 AM - 11 PM
    cities=["Mumbai"]
)

# User 2: The Night Owl / Gamer (Late Night, Mid Budget, Bangalore)
user2_data = generate_user_data(
    user_id=2, 
    num_txns=800, 
    min_amt=500, max_amt=5000, 
    active_hours=[22, 23, 0, 1, 2, 3, 4], # 10 PM - 4 AM
    cities=["Bangalore"]
)

# User 3: The Rich Traveler (Daytime, High Budget, Multi-City)
user3_data = generate_user_data(
    user_id=3, 
    num_txns=500, 
    min_amt=10000, max_amt=100000, 
    active_hours=list(range(9, 18)), # 9 AM - 6 PM (Office Hours)
    cities=["Delhi", "Mumbai", "London", "Dubai"]
)

# Combine and Insert
all_data = user1_data + user2_data + user3_data
cursor.executemany("""
    INSERT INTO transactions (user_id, amount, timestamp, location, merchant)
    VALUES (?, ?, ?, ?, ?)
""", all_data)

conn.commit()
conn.close()
print(f"✅ SUCCESS! Generated {len(all_data)} transactions across 3 distinct users.")