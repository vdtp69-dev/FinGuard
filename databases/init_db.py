import sqlite3

def init_database():
    # 1. Connect to the database (This creates the file 'finguard.db')
    conn = sqlite3.connect('finguard.db')
    cursor = conn.cursor()
    
    # 2. CREATE USERS TABLE
    # This holds your user profiles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. CREATE TRANSACTIONS TABLE
    # This holds the money data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            location TEXT,
            merchant TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # 4. CREATE LOGS TABLE (For your Viva "Explainability")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fraud_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER,
            user_id INTEGER NOT NULL,
            risk_score REAL,
            action_taken TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # 5. Add a Demo User (So your code doesn't crash later)
    try:
        cursor.execute("INSERT INTO users (username, email) VALUES (?, ?)", 
                       ("Student_Demo", "student@example.com"))
    except sqlite3.IntegrityError:
        print("User already exists.")

    conn.commit()
    conn.close()
    print("✅ SUCCESS! Database tables created.")

if __name__ == "__main__":
    init_database()