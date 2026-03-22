# scripts/setup_finguard_database.py — complete rewrite
# Fraud is now realistic: combination of signals not just high amount

import sqlite3
import random
from datetime import datetime, timedelta

conn   = sqlite3.connect("data/finguard.db")
cursor = conn.cursor()

# ── Reset ──
cursor.execute("DROP TABLE IF EXISTS users")
cursor.execute("DROP TABLE IF EXISTS transactions")

cursor.execute("""
CREATE TABLE users (
    user_id  INTEGER PRIMARY KEY,
    name     TEXT,
    persona  TEXT
)""")

cursor.execute("""
CREATE TABLE transactions (
    txn_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER,
    amount    REAL,
    timestamp DATETIME,
    location  TEXT,
    merchant  TEXT,
    is_fraud  INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)""")

# ── Users ──
users = [
    (1, "Aman",  "Student"),
    (2, "Riya",  "NightOwl"),
    (3, "Kabir", "VIP")
]
cursor.executemany("INSERT INTO users VALUES (?, ?, ?)", users)

# ── Persona definitions ──
personas = {
    1: {
        "min_amt":      50,
        "max_amt":      500,
        "active_hours": list(range(8, 23)),
        "cities":       ["Mumbai"],
        "merchants":    ["Swiggy", "Zomato", "Amazon", "BookStore"]
    },
    2: {
        "min_amt":      500,
        "max_amt":      5000,
        "active_hours": [22, 23, 0, 1, 2, 3, 4],
        "cities":       ["Bangalore"],
        "merchants":    ["Steam", "EpicGames", "Amazon", "Zomato"]
    },
    3: {
        "min_amt":      10000,
        "max_amt":      100000,
        "active_hours": list(range(9, 18)),
        "cities":       ["Delhi", "Mumbai", "London", "Dubai"],
        "merchants":    ["LuxuryMall", "Airline", "Hotel", "Amazon"]
    }
}

start_date = datetime.now() - timedelta(days=60)
all_data   = []

for user_id, config in personas.items():
    print(f"Generating data for User {user_id}...")

    num_txns = 800 if user_id != 3 else 600

    for i in range(num_txns):
        roll = random.random()

        # ── 85% Normal ──
        if roll < 0.85:
            hour     = random.choice(config["active_hours"])
            amount   = round(random.uniform(
                           config["min_amt"],
                           config["max_amt"]), 2)
            city     = random.choice(config["cities"])
            merchant = random.choice(config["merchants"])
            is_fraud = 0

        # ── 10% Slightly unusual (not fraud) ──
        elif roll < 0.95:
            hour     = random.randint(0, 23)
            amount   = round(random.uniform(
                           config["min_amt"],
                           config["max_amt"] * 1.5), 2)
            city     = random.choice(config["cities"])
            merchant = random.choice(config["merchants"])
            is_fraud = 0

        # ── 5% REAL FRAUD — realistic combinations ──
        else:
            # Pick a fraud pattern randomly
            fraud_type = random.choice([
                "night_large",      # large amount at night
                "velocity",         # rapid transaction
                "unknown_location", # unknown city + high amount
                "ato",              # account takeover pattern
            ])

            if fraud_type == "night_large":
                hour     = random.randint(1, 4)
                amount   = round(random.uniform(
                               config["max_amt"] * 3,
                               config["max_amt"] * 8), 2)
                city     = random.choice(config["cities"])
                merchant = random.choice(config["merchants"])

            elif fraud_type == "velocity":
                hour     = random.randint(0, 23)
                amount   = round(random.uniform(
                               config["min_amt"],
                               config["max_amt"]), 2)
                city     = random.choice(config["cities"])
                merchant = random.choice(config["merchants"])

            elif fraud_type == "unknown_location":
                hour     = random.randint(0, 23)
                amount   = round(random.uniform(
                               config["max_amt"] * 2,
                               config["max_amt"] * 5), 2)
                city     = "UnknownCity"
                merchant = "UnknownMerchant"

            else:  # ato
                hour     = random.randint(1, 5)
                amount   = round(random.uniform(
                               config["max_amt"] * 4,
                               config["max_amt"] * 10), 2)
                city     = "UnknownCity"
                merchant = "UnknownMerchant"

            is_fraud = 1

        # Timestamp
        day_offset = random.randint(0, 60)
        txn_time   = start_date + timedelta(days=day_offset)
        txn_time   = txn_time.replace(
                         hour=hour,
                         minute=random.randint(0, 59),
                         second=random.randint(0, 59)
                     )

        all_data.append((
            user_id, amount,
            txn_time.isoformat(),
            city, merchant, is_fraud
        ))

all_data.sort(key=lambda x: x[2])

cursor.executemany("""
    INSERT INTO transactions
        (user_id, amount, timestamp, location, merchant, is_fraud)
    VALUES (?, ?, ?, ?, ?, ?)
""", all_data)

conn.commit()
conn.close()

fraud_count = sum(1 for r in all_data if r[5] == 1)
print(f"\n✅ Done. {len(all_data)} transactions inserted.")
print(f"   Fraud: {fraud_count} ({fraud_count/len(all_data)*100:.1f}%)")
print(f"   Normal: {len(all_data)-fraud_count}")