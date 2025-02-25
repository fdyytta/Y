import sqlite3

DATABASE = 'store.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Buat tabel products
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        name TEXT PRIMARY KEY,
        price INTEGER NOT NULL,
        stock INTEGER NOT NULL,
        description TEXT
    )
    ''')

    # Buat tabel users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        growid TEXT PRIMARY KEY,
        balance INTEGER DEFAULT 0
    )
    ''')

    # Buat tabel user_growid
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_growid (
        user_id INTEGER PRIMARY KEY,
        growid TEXT NOT NULL,
        FOREIGN KEY (growid) REFERENCES users(growid)
    )
    ''')

    # Buat tabel purchases
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product TEXT,
        quantity INTEGER,
        FOREIGN KEY (user_id) REFERENCES user_growid(user_id),
        FOREIGN KEY (product) REFERENCES products(name)
    )
    ''')

    # Buat tabel donations
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS donations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        growid TEXT,
        deposit INTEGER,
        FOREIGN KEY (growid) REFERENCES users(growid)
    )
    ''')

    conn.commit()
    conn.close()