import sqlite3


def count_member_rows():
    """Connects to the database and prints the number of rows in the members table."""
    db_path = "reporter/data/kranos_data.db"
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM members")
        count = cursor.fetchone()[0]
        print(f"Number of rows in members table: {count}")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    count_member_rows()
