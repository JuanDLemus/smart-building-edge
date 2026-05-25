import sqlite3
import sys

def init_db_file(db_path="building.db"):
    """Initialize the SQLite database schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lab_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lab TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            co2_index REAL,
            mq135 INTEGER,
            mq8 INTEGER,
            estado TEXT
        )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    db_name = sys.argv[1] if len(sys.argv) > 1 else "building.db"
    init_db_file(db_name)
    print(f"Database {db_name} creada")
