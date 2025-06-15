import streamlit as st
import pandas as pd
from datetime import date, datetime # Added datetime
import sqlite3
# Import AppAPI class if needed by other parts, and specific functions that are standalone
from reporter.app_api import AppAPI
# Standalone API functions for memberships tab (assuming they handle their own DB connection)
from reporter.app_api import (
    create_membership,
    get_active_members_for_dropdown,
    get_active_plans_for_dropdown,
    get_all_memberships_for_view, # Added
    update_membership,            # Added
    delete_membership,             # Added
    # Added new reporting functions
    get_financial_summary_report,
    get_renewal_forecast_report
)
from reporter.database import DB_FILE # Use this for DB_PATH

# --- Database Connection & API Initialization (for AppAPI class if used elsewhere) ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    return conn

api = AppAPI(get_db_connection()) # This instance is for other tabs/features potentially

# --- Helper function to clear form state ---
def clear_membership_form_state():
    st.session_state.create_member_id = None
    # st.session_state.create_plan_id = None # This will be derived from create_plan_id_display
    st.session_state.create_plan_id_display = None # Will store (id, name, duration)
    st.session_state.create_transaction_amount = 0.0
    st.session_state.create_start_date = date.today()
    st.session_state.selected_plan_duration_display = "" # For displaying duration

    # If using a form key to force rebuild, you might increment it here
    if 'form_key_create_membership' in st.session_state:
        st.session_state.form_key_create_membership = f"form_{datetime.now().timestamp()}"


# --- Tab Rendering Functions ---
def render_memberships_tab():
    # This tab is for creating and managing memberships as per P3-T1 / P3-T2

    # Initialize session state for form inputs if not already present
    if 'create_member_id' not in st.session_state: # Stores the selected member_id for submission
        st.session_state.create_member_id = None
    if 'create_member_id_display' not in st.session_state: # Stores (id, name) for member selectbox
        st.session_state.create_member_id_display = None

    # For plan selection
    if 'create_plan_id_display' not in st.session_state: # Stores (id, name, duration) for plan selectbox
        st.session_state.create_plan_id_display = None
    if 'selected_plan_duration_display' not in st.session_state: # For displaying duration
        st.session_state.selected_plan_duration_display = ""

    if 'create_transaction_amount' not in st.session_state:
        st.session_state.create_transaction_amount = 0.0
    if 'create_start_date' not in st.session_state:
        st.session_state.create_start_date = date.today()
    if 'form_key_create_membership' not in st.session_state:
        st.session_state.form_key_create_membership = 'initial_form_key'

    # Session state for View/Manage Memberships panel
    if 'filter_membership_name' not in st.session_state:
        st.session_state.filter_membership_name = ""
    if 'filter_membership_phone' not in st.session_state:
        st.session_state.filter_membership_phone = ""
    if 'filter_membership_status' not in st.session_state:
        st.session_state.filter_membership_status = "All" # Default to "All"
    if 'manage_selected_membership_id' not in st.session_state:
        st.session_state.manage_selected_membership_id = None
    if 'memberships_view_data' not in st.session_state: # To store data for selectbox
        st.session_state.memberships_view_data = []
    if 'edit_form_key' not in st.session_state:
        st.session_state.edit_form_key = 'initial_edit_form'

    # Edit form field states
    if 'edit_start_date' not in st.session_state:
        st.session_state.edit_start_date = date.today()
    if 'edit_end_date' not in st.session_state:
        st.session_state.edit_end_date = date.today()
    if 'edit_is_active' not in st.session_state:
        st.session_state.edit_is_active = True


    left_column, right_column = st.columns(2)

    # Left Column: Create Membership Form
    with left_column:
        st.header("Create Membership")

        # Fetch data for dropdowns
        try:
            member_list_tuples = get_active_members_for_dropdown(DB_FILE) # List of (id, name)
            # Assuming get_active_plans_for_dropdown returns list of (id, name, duration_days)
            # If not, this is a point of failure or needs adjustment.
            plan_list_tuples = get_active_plans_for_dropdown(DB_FILE)
        except Exception as e:
            st.error(f"Error fetching data for dropdowns: {e}")
            member_list_tuples = []
            plan_list_tuples = []

        # Prepare options for selectboxes
        # Member options: store (id, name) tuple, display name
        member_options = {None: "Select Member..."}
        for mid, mname in member_list_tuples:
            member_options[(mid, mname)] = mname

        # Plan options: store (id, name, duration) tuple, display name
        plan_options = {None: "Select Plan..."}
        for pid, pname, pduration in plan_list_tuples: # Assumes (id, name, duration)
            plan_options[(pid, pname, pduration)] = pname


        # Callback to update displayed duration when plan selection changes
        def update_plan_duration_display():
            selected_plan_data = st.session_state.get("create_plan_id_display_widget")
            if selected_plan_data and selected_plan_data[0] is not None: # selected_plan_data is (id, name, duration)
                st.session_state.selected_plan_duration_display = f"{selected_plan_data[2]} days"
                st.session_state.create_plan_id_display = selected_plan_data # Store the full tuple for form submission logic
            else:
                st.session_state.selected_plan_duration_display = ""
                st.session_state.create_plan_id_display = None

        # Use st.form for better grouping of inputs and submission
        with st.form(key=st.session_state.form_key_create_membership, clear_on_submit=False):
            st.selectbox(
                "Member Name",
                options=list(member_options.keys()),
                format_func=lambda key: member_options[key],
                key="create_member_id_display" # Stores (id,name)
            )
            st.selectbox(
                "Plan Name",
                options=list(plan_options.keys()),
                format_func=lambda key: plan_options[key],
                key="create_plan_id_display_widget", # Temp key for widget, stores (id,name,duration)
                on_change=update_plan_duration_display
            )
            # Display Plan Duration (read-only)
            st.text_input(
                "Plan Duration",
                value=st.session_state.selected_plan_duration_display,
                disabled=True,
                key="displayed_plan_duration_readonly" # Unique key
            )
            st.number_input(
                "Transaction Amount",
                min_value=0.0,
                key="create_transaction_amount",
                format="%.2f"
            )
            st.date_input(
                "Start Date",
                key="create_start_date"
            )

            col1, col2 = st.columns(2)
            with col1:
                save_button = st.form_submit_button("SAVE")
            with col2:
                clear_button = st.form_submit_button("CLEAR")

        if save_button:
            # Extract data from session state
            selected_member_data = st.session_state.get("create_member_id_display") # This is (id, name)
            selected_plan_data = st.session_state.get("create_plan_id_display")   # This is (id, name, duration)

            member_id = selected_member_data[0] if selected_member_data and selected_member_data[0] is not None else None
            plan_id = selected_plan_data[0] if selected_plan_data and selected_plan_data[0] is not None else None
            # plan_duration = selected_plan_data[2] if selected_plan_data and selected_plan_data[0] is not None else None # Duration is available if needed

            amount = st.session_state.create_transaction_amount
            start_date_val = st.session_state.create_start_date

            if not member_id or not plan_id:
                st.error("Please select a member and a plan.")
            elif amount <= 0:
                st.error("Transaction amount must be greater than zero.")
            else:
                try:
                    success, message = create_membership(
                        DB_FILE,
                        member_id,
                        plan_id,
                        amount,
                        start_date_val.strftime('%Y-%m-%d')
                    )
                    if success:
                        st.success(message)
                        clear_membership_form_state() # Clear form on success
                        # To see the form clear, we might need to rerun if not using clear_on_submit=True on st.form
                        # or by changing the form key which is done in clear_membership_form_state
                        st.rerun()
                    else:
                        st.error(message)
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")

        if clear_button:
            clear_membership_form_state()
            st.rerun() # Rerun to reflect cleared state

    # Right Column: View/Manage Memberships Panel
    with right_column:
        st.header("View/Manage Memberships")

        # Filters
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            st.text_input("Filter by Name", key="filter_membership_name")
        with col_filter2:
            st.text_input("Filter by Phone", key="filter_membership_phone")
        with col_filter3:
            st.selectbox(
                "Filter by Status",
                options=["All", "Active", "Inactive"],
                key="filter_membership_status"
            )

        # Apply filters button (or trigger on change)
        if st.button("Apply Filters / Refresh List", key="apply_membership_filters"):
            st.session_state.manage_selected_membership_id = None # Reset selection on new filter application

        # Fetch and display data
        try:
            status_query = st.session_state.filter_membership_status if st.session_state.filter_membership_status != "All" else None

            # Store data in session state to populate the selection dropdown
            st.session_state.memberships_view_data = get_all_memberships_for_view(
                DB_FILE,
                name_filter=st.session_state.filter_membership_name if st.session_state.filter_membership_name else None,
                phone_filter=st.session_state.filter_membership_phone if st.session_state.filter_membership_phone else None,
                status_filter=status_query
            )

            if st.session_state.memberships_view_data:
                # Prepare for display (e.g., client_name, plan_name, start_date, end_date, status string)
                display_df = pd.DataFrame(st.session_state.memberships_view_data)
                # Ensure correct columns for display if needed, API returns dicts with correct keys
                st.dataframe(display_df[['client_name', 'phone', 'plan_name', 'start_date', 'end_date', 'status', 'membership_id']], hide_index=True, use_container_width=True)
            else:
                st.info("No memberships found matching your criteria.")

        except Exception as e:
            st.error(f"Error fetching memberships: {e}")
            st.session_state.memberships_view_data = [] # Ensure it's an empty list on error
            st.dataframe(pd.DataFrame(), use_container_width=True) # Display empty dataframe

        # Select Membership to Manage
        # Create options for the selectbox from the fetched data
        manage_options = [(None, "Select Membership...")] + \
                         [(item['membership_id'], f"{item['client_name']} - {item['plan_name']} ({item['start_date']} to {item['end_date']})")
                          for item in st.session_state.memberships_view_data]

        if not st.session_state.memberships_view_data and st.session_state.manage_selected_membership_id:
             st.session_state.manage_selected_membership_id = None # Clear selection if list is empty

        def on_select_membership_for_management():
            selected_id = st.session_state.get('_manage_selected_membership_id_display') # temp key from widget
            if selected_id is None:
                 st.session_state.manage_selected_membership_id = None
                 return

            st.session_state.manage_selected_membership_id = selected_id
            # Populate edit form fields
            selected_details = next((m for m in st.session_state.memberships_view_data if m['membership_id'] == selected_id), None)
            if selected_details:
                st.session_state.edit_start_date = datetime.strptime(selected_details['start_date'], "%Y-%m-%d").date()
                st.session_state.edit_end_date = datetime.strptime(selected_details['end_date'], "%Y-%m-%d").date()
                st.session_state.edit_is_active = True if selected_details['status'].lower() == 'active' else False
                st.session_state.edit_form_key = f"edit_form_{datetime.now().timestamp()}" # Change key to force re-render of form defaults


        st.selectbox(
            "Select Membership to Manage",
            options=manage_options,
            format_func=lambda x: x[1],
            key="_manage_selected_membership_id_display", # Temporary key to capture selection
            on_change=on_select_membership_for_management,
            index = manage_options.index(next((opt for opt in manage_options if opt[0] == st.session_state.manage_selected_membership_id), (None, "Select Membership...")))

        )

        # Edit/Delete Form (conditional)
        if st.session_state.manage_selected_membership_id is not None:
            st.subheader(f"Edit Membership ID: {st.session_state.manage_selected_membership_id}")

            # Find details again (or ensure they are robustly passed if selectbox changes)
            current_selection_details = next((m for m in st.session_state.memberships_view_data if m['membership_id'] == st.session_state.manage_selected_membership_id), None)

            if current_selection_details:
                # If selection changes, ensure form defaults are updated. on_change callback handles this.
                with st.form(key=st.session_state.edit_form_key, clear_on_submit=False):
                    st.date_input("Start Date", key="edit_start_date")
                    st.date_input("End Date", key="edit_end_date")
                    st.checkbox("Is Active", key="edit_is_active")

                    edit_col, delete_col,_ = st.columns([1,1,3]) # Make buttons smaller
                    with edit_col:
                        edit_button = st.form_submit_button("SAVE Changes")
                    with delete_col:
                        delete_button = st.form_submit_button("DELETE")

                if edit_button:
                    try:
                        success, message = update_membership(
                            DB_FILE,
                            st.session_state.manage_selected_membership_id,
                            st.session_state.edit_start_date.strftime('%Y-%m-%d'),
                            st.session_state.edit_end_date.strftime('%Y-%m-%d'),
                            st.session_state.edit_is_active
                        )
                        if success:
                            st.success(message)
                            st.session_state.manage_selected_membership_id = None # Clear selection
                            st.rerun() # Refresh list
                        else:
                            st.error(message)
                    except Exception as e:
                        st.error(f"Error updating membership: {e}")

                if delete_button:
                    # Confirmation for delete
                    if 'confirm_delete_membership_id' not in st.session_state or \
                       st.session_state.confirm_delete_membership_id != st.session_state.manage_selected_membership_id:
                        st.session_state.confirm_delete_membership_id = st.session_state.manage_selected_membership_id
                        st.warning(f"Are you sure you want to DEACTIVATE membership ID {st.session_state.manage_selected_membership_id}? This will mark it as inactive.")
                        # Rerun to show confirmation buttons
                        st.rerun()

                    if st.session_state.get('confirm_delete_membership_id') == st.session_state.manage_selected_membership_id:
                        confirm_yes, confirm_no = st.columns(2)
                        with confirm_yes:
                            if st.button("Yes, Deactivate", key=f"confirm_del_ms_{st.session_state.manage_selected_membership_id}"):
                                try:
                                    success, message = delete_membership(DB_FILE, st.session_state.manage_selected_membership_id)
                                    if success:
                                        st.success(message)
                                    else:
                                        st.error(message)
                                    st.session_state.manage_selected_membership_id = None # Clear selection
                                    del st.session_state.confirm_delete_membership_id # Clear confirmation state
                                    st.rerun() # Refresh list
                                except Exception as e:
                                    st.error(f"Error deactivating membership: {e}")
                                    del st.session_state.confirm_delete_membership_id
                                    st.rerun()
                        with confirm_no:
                             if st.button("Cancel Deactivation", key=f"cancel_del_ms_{st.session_state.manage_selected_membership_id}"):
                                del st.session_state.confirm_delete_membership_id
                                st.rerun()
            else:
                 # This case might occur if the list was refreshed and the selected ID is no longer valid
                 st.session_state.manage_selected_membership_id = None
                 # Optionally show a message e.g. st.info("Selected membership details not found. Please re-select.")
                 # Rerun can help clear the state if it's stuck
                 st.rerun()

# render_members_tab and render_plans_tab have been removed.

def render_reporting_tab():
    st.header("Financial & Renewals Reporting")

    # Initialize session state variables
    if 'financial_report_output' not in st.session_state: # Updated state variable
        st.session_state.financial_report_output = None
    if 'renewals_report_data' not in st.session_state:
        st.session_state.renewals_report_data = None
    # Default to current month for date inputs
    if 'report_month_financial' not in st.session_state:
        st.session_state.report_month_financial = date.today().replace(day=1)
    if 'report_month_renewals' not in st.session_state:
        st.session_state.report_month_renewals = date.today().replace(day=1)

    # --- Monthly Financial Report Section ---
    st.subheader("Monthly Financial Report")

    # Use the value from session state for the date input, and update it if changed
    report_month_financial_val = st.date_input(
        "Select Month for Financial Report",
        value=st.session_state.report_month_financial,
        key="financial_report_month_selector" # Unique key for the widget
    )
    # If the date input changes, update the session state
    if report_month_financial_val != st.session_state.report_month_financial:
        st.session_state.report_month_financial = report_month_financial_val
        # Clear old report data when month changes before generating new one
        st.session_state.financial_report_output = None # Clear combined state


    if st.button("Generate Monthly Financial Report", key="generate_financial_report"):
        year = st.session_state.report_month_financial.year
        month = st.session_state.report_month_financial.month
        try:
            # Call the new unified financial report function
            report_output = get_financial_summary_report(DB_FILE, year, month)
            st.session_state.financial_report_output = report_output

            if not report_output or (report_output.get('summary', {}).get('total_income', 0) == 0 and not report_output.get('transactions')):
                 st.info(f"No financial data found for {st.session_state.report_month_financial.strftime('%B %Y')}.")
            else:
                 st.success(f"Financial report generated for {st.session_state.report_month_financial.strftime('%B %Y')}.")
        except Exception as e:
            st.error(f"Error generating financial report: {e}")
            st.session_state.financial_report_output = None

    if st.session_state.financial_report_output:
        summary_data = st.session_state.financial_report_output.get('summary', {})
        transactions_data = st.session_state.financial_report_output.get('transactions', [])

        st.metric(
            label=f"Total Income for {st.session_state.report_month_financial.strftime('%B %Y')}",
            value=f"${summary_data.get('total_income', 0.0):.2f}"
        )
        # Optionally, display other summary points like total transactions, new members etc.
        # For example:
        # st.metric(label="Total Transactions", value=summary_data.get('total_transactions', 0))

        if transactions_data:
            # Assuming transactions_data is a list of dicts with keys like
            # 'transaction_id', 'client_name', 'transaction_date', 'amount', 'transaction_type', etc.
            df_financial = pd.DataFrame(transactions_data)
            # Adjust columns based on actual keys in transactions_data
            # Example:
            st.dataframe(df_financial[['transaction_id', 'client_name', 'transaction_date', 'amount', 'transaction_type', 'description', 'plan_name', 'payment_method']], hide_index=True, use_container_width=True)
        elif summary_data.get('total_income', 0) > 0 :
             st.info(f"Summary available, but no detailed transactions found for {st.session_state.report_month_financial.strftime('%B %Y')}.")
        # If both summary and transactions are empty, the initial "No financial data found" message covers it.


    st.divider()

    # --- Upcoming Renewals Section ---
    st.subheader("Upcoming Membership Renewals")

    report_month_renewals_val = st.date_input(
        "Select Month for Renewals Report",
        value=st.session_state.report_month_renewals,
        key="renewals_report_month_selector" # Unique key
    )
    if report_month_renewals_val != st.session_state.report_month_renewals:
        st.session_state.report_month_renewals = report_month_renewals_val
        # Clear old report data
        st.session_state.renewals_report_data = None


    if st.button("Generate Renewals Report", key="generate_renewals_report"):
        year = st.session_state.report_month_renewals.year
        month = st.session_state.report_month_renewals.month
        try:
            # Call the new renewal forecast function
            st.session_state.renewals_report_data = get_renewal_forecast_report(DB_FILE, year, month)
            if not st.session_state.renewals_report_data: # Empty list means no renewals
                st.info(f"No upcoming renewals found for {st.session_state.report_month_renewals.strftime('%B %Y')}.")
            else:
                st.success(f"Renewals report generated for {st.session_state.report_month_renewals.strftime('%B %Y')}.")
        except Exception as e:
            st.error(f"Error generating renewals report: {e}")
            st.session_state.renewals_report_data = None # Set to None on error

    if st.session_state.renewals_report_data: # Check if data exists (could be an empty list)
        # Assuming get_renewal_forecast_report returns a list of dicts with keys like
        # 'client_name', 'phone', 'plan_name', 'end_date', 'renewal_status' (example new field)
        df_renewals = pd.DataFrame(st.session_state.renewals_report_data)
        # Adjust columns based on actual keys in the returned data
        # Example:
        st.dataframe(df_renewals[['client_name', 'phone', 'plan_name', 'end_date']], hide_index=True, use_container_width=True)
    # Handle case where button was clicked, data is explicitly an empty list (meaning no renewals found)
    elif st.session_state.renewals_report_data == []: # Explicitly check for empty list
         st.info(f"No upcoming renewals found for {st.session_state.report_month_renewals.strftime('%B %Y')}.")


tab_memberships, tab_reporting = st.tabs(["Memberships", "Reporting"])

with tab_memberships:
    render_memberships_tab()

# Removed tab_members and tab_plans sections

with tab_reporting:
    render_reporting_tab()
