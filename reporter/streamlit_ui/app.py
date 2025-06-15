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
tab1, tab2, tab3, tab4 = st.tabs(["Members", "Plans", "Reporting", "Transactions"])

with tab1:
    st.header("Member Management")

    # --- Add Member Form ---
    with st.form("add_member_form"):
        st.subheader("Add New Member")
        new_member_name = st.text_input("Name")
        new_member_phone = st.text_input("Phone")
        submitted = st.form_submit_button("Add Member")
        if submitted:
            if new_member_name and new_member_phone:
                # Call the API to add the member
                # Assuming api.add_member returns a success/error message or status
                response = api.add_member(new_member_name, new_member_phone)
                if "successfully" in response.lower(): # Crude check, improve if API returns structured response
                    st.success(response)
                    # No explicit table refresh needed, Streamlit should rerun and pick up new data.
                else:
                    st.error(response)
            else:
                st.error("Please provide both name and phone number.")

    st.markdown("---") # Separator

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

    # --- Add Plan Form ---
    with st.form("add_plan_form"):
        st.subheader("Add New Plan")
        new_plan_name = st.text_input("Plan Name")
        new_plan_duration = st.number_input("Duration (days)", min_value=1, value=30, step=1)
        new_plan_price = st.number_input("Price (e.g., 1500)", min_value=0, value=1000, step=50, format="%d")
        new_plan_type = st.text_input("Type (e.g., GC, PT, Combo)") # GC for Group Class, PT for Personal Training
        plan_submitted = st.form_submit_button("Save Plan")

        if plan_submitted:
            if new_plan_name and new_plan_duration and new_plan_price >= 0 and new_plan_type:
                # Call the API to add the plan
                # Ensure types are correct, e.g., int(new_plan_duration), int(new_plan_price)
                response_tuple = api.add_plan(
                    new_plan_name,
                    int(new_plan_duration),
                    int(new_plan_price), # Ensure price is passed as int
                    new_plan_type
                )
                # api.add_plan now returns Tuple[bool, str, Optional[int]]
                # We can check the success boolean (first element)
                if response_tuple and response_tuple[0]: # Check if response_tuple is not None and success is True
                    st.success(response_tuple[1]) # Display success message
                    # Streamlit should rerun and refresh the table below automatically
                elif response_tuple:
                    st.error(response_tuple[1]) # Display error message
                else:
                    st.error("Failed to add plan. Received no response from API.")
            else:
                st.error("Please provide Plan Name, Duration, Price, and Type. Duration and Price must be valid numbers.")

    st.markdown("---") # Separator

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

with tab4:
    st.header("Transaction Management")

    # Fetching data for dropdowns
    members_data = api.get_all_members()  # (member_id, client_name, phone, join_date, is_active)
    plans_data = api.get_all_plans()  # (plan_id, plan_name, duration_days, is_active) - Assuming this gets active plans

    member_display_list = ["No members available"]
    member_name_to_id = {}
    if members_data:
        member_display_list = [f"{name} (ID: {mid})" for mid, name, _, _, _ in members_data]
        member_name_to_id = {f"{name} (ID: {mid})": mid for mid, name, _, _, _ in members_data}

    plan_display_list = ["No plans available"]
    plan_name_to_id = {}
    if plans_data:
        # Assuming get_all_plans returns (plan_id, plan_name, duration_days, is_active)
        # And we only want active plans if not already filtered by the API method
        active_plans = [p for p in plans_data if p[3]] # Filter for active plans (is_active == True at index 3)
        # TODO: The above filter p[3] (price) is likely incorrect for determining "active" status
        # as get_all_plans now returns (id, name, duration, price, type).
        # This subtask is only to fix the unpacking, not this filter logic.
        if not active_plans and plans_data: # If all plans are inactive
            plan_display_list = ["No active plans available"]
        elif active_plans:
            # Unpack 5 columns: pid, name, duration, price, type. Using _ for unused ones.
            plan_display_list = [f"{name} (ID: {pid})" for pid, name, _, _, _ in active_plans]
            plan_name_to_id = {f"{name} (ID: {pid})": pid for pid, name, _, _, _ in active_plans}


    with st.form("add_transaction_form"):
        st.subheader("Add New Transaction")

        selected_member_display = st.selectbox(
            "Select Member",
            options=member_display_list,
            disabled=not members_data
        )

        selected_plan_display = st.selectbox(
            "Select Plan",
            options=plan_display_list,
            disabled=not plan_name_to_id # Disable if no active plans to select
        )

        amount = st.number_input("Amount", min_value=0.01, format="%.2f")
        payment_date = st.date_input("Payment Date", value=datetime.date.today())
        start_date = st.date_input("Start Date", value=datetime.date.today())
        payment_method = st.text_input("Payment Method (e.g., Cash, Card)")

        transaction_submitted = st.form_submit_button("Add Transaction")

        if transaction_submitted:
            # Retrieve selected IDs
            selected_member_id = member_name_to_id.get(selected_member_display)
            selected_plan_id = plan_name_to_id.get(selected_plan_display)

            # Client-side validation
            if not selected_member_id or selected_member_display == "No members available":
                st.error("Please select a member.")
            elif not selected_plan_id or selected_plan_display == "No plans available" or selected_plan_display == "No active plans available":
                st.error("Please select an active plan.")
            elif amount <= 0:
                st.error("Amount must be greater than zero.")
            else:
                # Format dates
                payment_date_str = payment_date.strftime("%Y-%m-%d")
                start_date_str = start_date.strftime("%Y-%m-%d")

                # Call API
                success, message = api.add_transaction(
                    transaction_type="Group Class",  # Hardcoded as per instruction
                    member_id=selected_member_id,
                    start_date=start_date_str,
                    amount_paid=float(amount),
                    plan_id=selected_plan_id,
                    payment_date=payment_date_str,
                    payment_method=payment_method if payment_method else None, # Pass None if empty
                    sessions=None,  # Not applicable for Group Class plan enrollment
                    end_date=None  # Will be calculated by backend for Group Class
                )

                if success:
                    st.success(message)
                else:
                    st.error(message)

# To run the new application, execute streamlit run reporter/streamlit_ui/app.py from your terminal.
# Continue building out the UI in this file, using only methods from the api object to interact with the backend.
