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

# --- Tab Rendering Functions ---
def render_memberships_tab():
    st.header("Memberships Management")
    # Placeholder content
    st.write("Content for memberships management will go here.")

def render_members_tab():
    st.header("Member Management")
    # Placeholder content
    # st.write("Content for member management will go here.") # Original placeholder

    col1, col2 = st.columns(2)
    with col1:
        st.header("Add/Edit Member")
        # st.write("Form will go here.") # Original placeholder
        with st.form(key='member_form'):
            st.text_input("Name")
            st.date_input("Join Date") # Consider default value: datetime.date.today()
            st.text_input("Phone")
            st.selectbox("Status", options=["active", "inactive"])

            # Buttons
            # As per subtask: two st.form_submit_button, acknowledging both will submit.
            # Handling distinct "Clear" logic is a future step if required.
            submit_button = st.form_submit_button("Save")
            clear_button = st.form_submit_button("Clear")

            if submit_button:
                # Logic for saving will go here in a future task
                st.success("Save button pressed (logic not implemented).")
            if clear_button:
                # Logic for clearing will go here / or this button might be changed
                st.info("Clear button pressed (logic not implemented).")

    with col2:
        st.header("View Members")
        st.write("Table and filters will go here.")

def render_plans_tab():
    st.header("Plan Management")
    # Placeholder content
    st.write("Content for plan management will go here.")

def render_reporting_tab():
    st.header("Reporting")
    # Placeholder content
    st.write("Content for reporting will go here.")

st.set_page_config(layout="wide")
st.title("Kranos MMA Reporter v2.0") # Update title if desired

# New tab structure
tab_memberships, tab_members, tab_plans, tab_reporting = st.tabs([
    "Memberships", "Members", "Plans", "Reporting"
])

with tab_memberships:
    render_memberships_tab()

with tab_members:
    render_members_tab()

with tab_plans:
    render_plans_tab()

with tab_reporting:
    render_reporting_tab()
