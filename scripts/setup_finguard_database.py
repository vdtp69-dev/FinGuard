import sqlite3
import random
from datetime import datetime, timedelta

# -----------------------------
# 1️⃣ Connect to Database
# -----------------------------
conn = sqlite3.connect("finguard.db")
cursor = conn.cursor()

# -----------------------------
# 2️⃣ Reset Tables
# -----------------------------
cursor.execute("DROP TABLE IF EXISTS users")
cursor.execute("DROP TABLE IF EXISTS transactions")

# -----------------------------
# 3️⃣ Create Tables
# -----------------------------

cursor.execute("""
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    persona TEXT
)
""")

cursor.execute("""
CREATE TABLE transactions (
    txn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    timestamp DATETIME,
    location TEXT,
    merchant TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)
""")

# -----------------------------
# 4️⃣ Insert Users
# -----------------------------

users = [
    (1, "Aman", "Student"),
    (2, "Riya", "NightOwl"),
    (3, "Kabir", "VIP")
]

cursor.executemany("INSERT INTO users VALUES (?, ?, ?)", users)

# -----------------------------
# 5️⃣ Persona Definitions
# -----------------------------

personas = {
    1: {
        "min_amt": 50,
        "max_amt": 500,
        "active_hours": list(range(8, 23)),
        "cities": ["Mumbai"],
        "merchants": ["Swiggy", "Zomato", "Amazon", "BookStore"]
    },
    2: {
        "min_amt": 500,
        "max_amt": 5000,
        "active_hours": [22, 23, 0, 1, 2, 3, 4],
        "cities": ["Bangalore"],
        "merchants": ["Steam", "EpicGames", "Amazon", "Zomato"]
    },
    3: {
        "min_amt": 10000,
        "max_amt": 100000,
        "active_hours": list(range(9, 18)),
        "cities": ["Delhi", "Mumbai", "London", "Dubai"],
        "merchants": ["LuxuryMall", "Airline", "Hotel", "Amazon"]
    }
}

# -----------------------------
# 6️⃣ Generate Transactions
# -----------------------------

start_date = datetime.now() - timedelta(days=60)
all_data = []

for user_id, config in personas.items():
    print(f"Generating data for User {user_id}...")
    
    num_txns = 800 if user_id != 3 else 600
    
    for _ in range(num_txns):
        
        # 90% Normal Behavior
        if random.random() < 0.9:
            hour = random.choice(config["active_hours"])
            amount = round(random.uniform(config["min_amt"], config["max_amt"]), 2)
            city = random.choice(config["cities"])
            merchant = random.choice(config["merchants"])
        
        # 7% Slightly Unusual
        elif random.random() < 0.97:
            hour = random.randint(0, 23)
            amount = round(random.uniform(config["min_amt"], config["max_amt"] * 1.5), 2)
            city = random.choice(config["cities"])
            merchant = random.choice(config["merchants"])
        
        # 3% Extreme Fraud Simulation
        else:
            hour = random.randint(0, 5)
            amount = round(random.uniform(config["max_amt"] * 5, config["max_amt"] * 10), 2)
            city = "UnknownCity"
            merchant = "UnknownMerchant"
        
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        day_offset = random.randint(0, 60)
        
        txn_time = start_date + timedelta(days=day_offset)
        txn_time = txn_time.replace(hour=hour, minute=minute, second=second)
        
        all_data.append((user_id, amount, txn_time.isoformat(), city, merchant))


# Sort chronologically
all_data.sort(key=lambda x: x[2])

# -----------------------------
# 7️⃣ Insert Into DB
# -----------------------------

cursor.executemany("""
INSERT INTO transactions (user_id, amount, timestamp, location, merchant)
VALUES (?, ?, ?, ?, ?)
""", all_data)

conn.commit()
conn.close()

print(f"✅ SUCCESS! Inserted {len(all_data)} transactions.")
