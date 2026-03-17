import sqlite3
import random
from datetime import datetime, timedelta

# -----------------------------
# 1️⃣ Connect to Database
# -----------------------------
conn = sqlite3.connect("finguard.db")
cursor = conn.cursor()

# -----------------------------
# 2️⃣ Drop Existing Tables (Clean Start)
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
# 4️⃣ Insert Users (Personas)
# -----------------------------

users = [
    (1, "Aman", "Student"),
    (2, "Riya", "NightOwl"),
    (3, "Kabir", "VIP")
]

cursor.executemany("INSERT INTO users VALUES (?, ?, ?)", users)

# -----------------------------
# 5️⃣ Data Generation Settings
# -----------------------------

start_date = datetime.now() - timedelta(days=60)
num_txns_per_user = 800

locations = ["Mumbai", "Pune", "Delhi", "Bangalore"]
student_merchants = ["Swiggy", "Zomato", "Amazon", "BookStore"]
night_merchants = ["Steam", "EpicGames", "Amazon", "Zomato"]
vip_merchants = ["LuxuryMall", "Airline", "Hotel", "Amazon"]

data = []

# -----------------------------
# 6️⃣ Generate Transactions
# -----------------------------

for user in users:
    user_id = user[0]
    persona = user[2]

    last_txn_time = start_date

    for _ in range(num_txns_per_user):

        # --- Persona-Based Time Logic ---
        if persona == "Student":
            hour = random.randint(8, 22)
            amount = round(random.uniform(100, 1500), 2)
            merchant = random.choice(student_merchants)

        elif persona == "NightOwl":
            hour = random.randint(20, 4) if random.random() < 0.7 else random.randint(8, 18)
            amount = round(random.uniform(300, 3000), 2)
            merchant = random.choice(night_merchants)

        elif persona == "VIP":
            hour = random.randint(6, 23)
            amount = round(random.uniform(5000, 20000), 2)
            merchant = random.choice(vip_merchants)

        minute = random.randint(0, 59)
        second = random.randint(0, 59)

        day_offset = random.randint(0, 60)
        txn_time = start_date + timedelta(days=day_offset)
        txn_time = txn_time.replace(hour=hour, minute=minute, second=second)

        location = random.choice(locations)

        # --- Rare Fraud Simulation (3%) ---
        if random.randint(0, 100) < 3:
            amount = round(random.uniform(20000, 80000), 2)
            hour = random.randint(0, 5)
            merchant = "UnknownMerchant"
            location = "UnknownCity"

        data.append((user_id, amount, txn_time, location, merchant))

# -----------------------------
# 7️⃣ Insert Transactions
# -----------------------------

cursor.executemany("""
INSERT INTO transactions (user_id, amount, timestamp, location, merchant)
VALUES (?, ?, ?, ?, ?)
""", data)

conn.commit()
conn.close()

print("✅ Database created successfully with multi-persona data!")
