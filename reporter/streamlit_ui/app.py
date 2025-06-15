import streamlit as st
from reporter.app_api import AppAPI
import sqlite3 # Added for database connection

# --- Database Connection ---
# It's crucial that the path to the database is correct.
# Assuming 'reporter/data/kranos_data.db' is the intended database.
# This path is relative to the root of the project where streamlit is run.
DB_PATH = 'reporter/data/kranos_data.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    # You might want to configure the connection further, e.g., row_factory
    # conn.row_factory = sqlite3.Row # Example: For dict-like row access
    return conn

# Initialize the API with a database connection
# A new connection will be created for each session/run, which is generally fine for Streamlit.
# For more complex scenarios, connection pooling or caching might be considered.
api = AppAPI(get_db_connection()) # Example if kept

st.set_page_config(layout="wide")
st.title("Kranos MMA Reporter v2.0") # Update title if desired

# New tab structure
tab_memberships, tab_members, tab_plans, tab_reporting = st.tabs([
    "Memberships", "Members", "Plans", "Reporting"
])

with tab_memberships:
    st.header("Memberships Management")
    # Placeholder content
    st.write("Content for memberships management will go here.")

with tab_members:
    st.header("Member Management")
    # Placeholder content
    st.write("Content for member management will go here.")

with tab_plans:
    st.header("Plan Management")
    # Placeholder content
    st.write("Content for plan management will go here.")

with tab_reporting:
    st.header("Reporting")
    # Placeholder content
    st.write("Content for reporting will go here.")
