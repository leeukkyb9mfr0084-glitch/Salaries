import customtkinter
import os
import sqlite3
from reporter.database import create_database, seed_initial_plans
from reporter.database_manager import DB_FILE
from reporter.gui import App  # Assuming App will be in gui.py

if __name__ == '__main__':
    data_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    create_database(DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    seed_initial_plans(conn)
    conn.close()

    app = App()
    app.mainloop()
