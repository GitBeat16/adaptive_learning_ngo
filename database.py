import sqlite3

conn = sqlite3.connect("app.db", check_same_thread=False)
cursor = conn.cursor()

def init_db():

    # -------------------------
    # AUTH USERS
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auth_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    # -------------------------
    # PROFILES (MATCHMAKING)
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER UNIQUE,
        role TEXT,
        grade TEXT,
        class INTEGER,
        time TEXT,
        strong_subjects TEXT,
        weak_subjects TEXT,
        teaches TEXT,
        status TEXT DEFAULT 'waiting',
        created_at TEXT DEFAULT (datetime('now')),
        match_id TEXT
    )
    """)

    # -------------------------
    # CHAT MESSAGES
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id TEXT,
        sender TEXT,
        message TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """)

    # -------------------------
    # RATINGS
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ratings (
        mentor TEXT,
        mentee TEXT,
        rating INTEGER,
        session_date DATE
    )
    """)

    # -------------------------
    # SAFE MIGRATION (FOR OLD DBS)
    # -------------------------
    try:
        cursor.execute("ALTER TABLE profiles ADD COLUMN match_id TEXT")
    except:
        pass  # column already exists

    conn.commit()
