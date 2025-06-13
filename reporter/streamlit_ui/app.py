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
api = AppAPI(get_db_connection())

st.set_page_config(layout="wide")
st.title("Kranos MMA Reporter")

# --- UI Tabs ---
tab1, tab2, tab3 = st.tabs(["Members", "Plans", "Reporting"])

with tab1:
    st.header("Member Management")

    # Example: Displaying all members in a table
    st.subheader("All Members")
    all_members = api.get_all_members() # This now uses the AppAPI
    if all_members:
        # Assuming get_all_members returns a list of tuples/rows
        # For Streamlit dataframe, it's often helpful to have column names
        # We'll need to ensure api.get_all_members() returns data in a format
        # suitable for st.dataframe, or we'll process it here.
        # DatabaseManager.get_all_members returns:
        # (member_id, client_name, phone, join_date, is_active)
        # Let's create a list of dictionaries or a Pandas DataFrame for better display

        # If get_all_members returns list of tuples:
        members_data = [{"ID": m[0], "Name": m[1], "Phone": m[2], "Join Date": m[3], "Active": "Yes" if m[4] else "No"} for m in all_members]
        st.dataframe(members_data)
    else:
        st.write("No members found.")

with tab2:
    st.header("Plan Management")

    st.subheader("All Plans")
    all_plans = api.get_all_plans_with_inactive() # Fetches active and inactive
    if all_plans:
        # DatabaseManager.get_all_plans_with_inactive returns:
        # (plan_id, plan_name, duration_days, is_active)
        plans_data = [{"ID": p[0], "Name": p[1], "Duration (days)": p[2], "Active": "Yes" if p[3] else "No"} for p in all_plans]
        st.dataframe(plans_data)
    else:
        st.write("No plans found.")

import datetime # For default year/month

with tab3:
    st.header("Reporting")

    # --- Pending Renewals Section ---
    st.subheader("Pending Renewals")

    # Get current year and month as default values
    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month

    col_renew_year, col_renew_month, col_renew_button = st.columns([1,1,2])
    with col_renew_year:
        renew_year = st.number_input("Year", min_value=2020, max_value=2050, value=current_year, key="renew_year")
    with col_renew_month:
        renew_month = st.number_input("Month", min_value=1, max_value=12, value=current_month, key="renew_month")

    with col_renew_button:
        st.write("") # Spacer
        st.write("") # Spacer for alignment
        if st.button("Fetch Renewals", key="fetch_renewals"):
            renewals_data = api.get_pending_renewals(int(renew_year), int(renew_month))
            if renewals_data:
                # DatabaseManager.get_pending_renewals returns:
                # (m.client_name, m.phone, p.plan_name, t.end_date)
                df_renewals = [{"Name": r[0], "Phone": r[1], "Plan": r[2], "End Date": r[3]} for r in renewals_data]
                st.dataframe(df_renewals)
            else:
                st.write("No pending renewals found for the selected period.")

    st.markdown("---") # Separator

    # --- Monthly Finance Report Section ---
    st.subheader("Monthly Finance Report")
    col_finance_year, col_finance_month, col_finance_button = st.columns([1,1,2])
    with col_finance_year:
        finance_year = st.number_input("Year", min_value=2020, max_value=2050, value=current_year, key="finance_year")
    with col_finance_month:
        finance_month = st.number_input("Month", min_value=1, max_value=12, value=current_month, key="finance_month")

    with col_finance_button:
        st.write("") # Spacer
        st.write("") # Spacer for alignment
        if st.button("Generate Finance Report", key="fetch_finance"):
            total_amount = api.get_finance_report(int(finance_year), int(finance_month))
            if total_amount is not None:
                st.metric(label=f"Total Revenue for {int(finance_month):02d}-{int(finance_year)}", value=f"₹{total_amount:,.2f}")
            else:
                st.error("Could not retrieve finance report for the selected period.")

# To run the new application, execute streamlit run reporter/streamlit_ui/app.py from your terminal.
# Continue building out the UI in this file, using only methods from the api object to interact with the backend.
