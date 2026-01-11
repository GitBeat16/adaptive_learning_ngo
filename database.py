import sqlite3

conn = sqlite3.connect("app.db", check_same_thread=False)
cursor = conn.cursor()

def init_db():

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auth_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER,
        role TEXT,
        grade TEXT,
        class INTEGER,
        time TEXT,
        strong_subjects TEXT,
        weak_subjects TEXT,
        teaches TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ratings (
        mentor TEXT,
        rating INTEGER
    )
    """)

    conn.commit()
