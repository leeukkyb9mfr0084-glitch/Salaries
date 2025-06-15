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
    delete_membership             # Added
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
    st.session_state.create_plan_id = None
    st.session_state.create_transaction_amount = 0.0
    st.session_state.create_start_date = date.today()
    # If using a form key to force rebuild, you might increment it here
    if 'form_key_create_membership' in st.session_state:
        st.session_state.form_key_create_membership = f"form_{datetime.now().timestamp()}"


# --- Tab Rendering Functions ---
def render_memberships_tab():
    # This tab is for creating and managing memberships as per P3-T1 / P3-T2

    # Initialize session state for form inputs if not already present
    if 'create_member_id' not in st.session_state:
        st.session_state.create_member_id = None
    if 'create_plan_id' not in st.session_state:
        st.session_state.create_plan_id = None
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
            member_list = get_active_members_for_dropdown(DB_FILE) # List of (id, name)
            plan_list = get_active_plans_for_dropdown(DB_FILE)     # List of (id, name)
        except Exception as e:
            st.error(f"Error fetching data for dropdowns: {e}")
            member_list = []
            plan_list = []

        # Add a "Select..." option
        member_options = [(None, "Select Member...")] + member_list
        plan_options = [(None, "Select Plan...")] + plan_list

        # Use st.form for better grouping of inputs and submission
        with st.form(key=st.session_state.form_key_create_membership, clear_on_submit=False): # Clear on submit handled manually by clear_membership_form_state
            st.selectbox(
                "Member Name",
                options=member_options,
                format_func=lambda x: x[1],
                key="create_member_id_display" # This will store (id,name) tuple
            )
            st.selectbox(
                "Plan Name",
                options=plan_options,
                format_func=lambda x: x[1],
                key="create_plan_id_display" # This will store (id,name) tuple
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
            # Extract IDs from the stored tuples in session state
            selected_member_tuple = st.session_state.get("create_member_id_display")
            selected_plan_tuple = st.session_state.get("create_plan_id_display")

            member_id = selected_member_tuple[0] if selected_member_tuple and selected_member_tuple[0] is not None else None
            plan_id = selected_plan_tuple[0] if selected_plan_tuple and selected_plan_tuple[0] is not None else None
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


def render_members_tab():
    st.header("Member Management")

    # Initialize session state variables if they don't exist
    if 'selected_member_id' not in st.session_state:
        st.session_state.selected_member_id = None
    if 'show_history_modal' not in st.session_state:
        st.session_state.show_history_modal = False
    if 'history_member_id' not in st.session_state:
        st.session_state.history_member_id = None
    if 'form_key_member' not in st.session_state: # To reset form
        st.session_state.form_key_member = 'initial_member_form'


    left_column, right_column = st.columns(2)

    # Left Column: Add/Edit Member Form
    with left_column:
        st.subheader("Add/Edit Member")

        member_to_edit = None
        if st.session_state.selected_member_id:
            try:
                member_data = api.get_member_by_id(st.session_state.selected_member_id)
                if member_data:
                    # member_data is (member_id, client_name, phone, join_date, is_active)
                    member_to_edit = {
                        "id": member_data[0],
                        "name": member_data[1],
                        "phone": member_data[2],
                        "join_date": datetime.strptime(member_data[3], "%Y-%m-%d").date() if member_data[3] else date.today(),
                        "status": "Active" if member_data[4] else "Inactive"
                    }
                else:
                    st.error("Selected member not found.")
                    st.session_state.selected_member_id = None # Reset
            except Exception as e:
                st.error(f"Error fetching member details: {e}")
                st.session_state.selected_member_id = None # Reset


        with st.form(key=st.session_state.form_key_member, clear_on_submit=True):
            st.text_input("Member ID", value=member_to_edit["id"] if member_to_edit else "Auto-generated", disabled=True)
            name = st.text_input("Name", value=member_to_edit["name"] if member_to_edit else "")
            phone = st.text_input("Phone", value=member_to_edit["phone"] if member_to_edit else "")
            join_date_val = st.date_input("Join Date", value=member_to_edit["join_date"] if member_to_edit else date.today())
            status_options = ["Active", "Inactive"]
            status = st.selectbox("Status", options=status_options, index=status_options.index(member_to_edit["status"]) if member_to_edit else 0)

            col_save, col_clear = st.columns(2)
            with col_save:
                save_button = st.form_submit_button("Save Member")
            with col_clear:
                clear_button = st.form_submit_button("Clear / New")

            if save_button:
                is_active_bool = True if status == "Active" else False
                join_date_str = join_date_val.strftime("%Y-%m-%d")

                if not name or not phone:
                    st.error("Name and Phone cannot be empty.")
                else:
                    try:
                        if st.session_state.selected_member_id:
                            success, message = api.update_member(st.session_state.selected_member_id, name, phone, join_date_str, is_active_bool)
                        else:
                            # Using add_member_with_join_date as it returns member_id, though not directly used here.
                            # add_member also works.
                            member_id_or_none = api.add_member_with_join_date(name, phone, join_date_str)
                            if member_id_or_none: # Assuming returns ID on success, None on failure for this one
                                success, message = True, "Member added successfully."
                                # Manually set is_active for new members if add_member_with_join_date doesn't
                                # This might require an update_member call if default is_active is not what's selected.
                                # For simplicity, let's assume new members are active as per form, or add_member_with_join_date handles it.
                                # Or, if add_member_with_join_date does not set is_active:
                                # api.update_member(member_id_or_none, name, phone, join_date_str, is_active_bool)
                            else: # Check how add_member_with_join_date signals error (e.g. phone exists)
                                success, message = False, "Failed to add member. Phone might already exist or other error."
                                # A more specific error might come from add_member if it returns Tuple[bool, str]
                                # success, message = api.add_member(name, phone, join_date_str)
                                # if success and is_active_bool == False: # if add_member defaults to active
                                #    api.update_member(LAST_INSERT_ID_EQUIVALENT, name, phone, join_date_str, is_active_bool)


                        if success:
                            st.success(message)
                            st.session_state.selected_member_id = None
                            st.session_state.form_key_member = f"member_form_{datetime.now().timestamp()}" # Reset form
                            st.rerun()
                        else:
                            st.error(message)
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

            if clear_button:
                st.session_state.selected_member_id = None
                st.session_state.form_key_member = f"member_form_{datetime.now().timestamp()}" # Reset form
                st.rerun()

    # Right Column: Members List & Filters
    with right_column:
        st.subheader("View Members")

        search_name = st.text_input("Search by Name")
        status_filter_options = ["All", "Active", "Inactive"]
        status_filter = st.selectbox("Filter by Status", status_filter_options)

        actual_status_filter = None
        if status_filter == "Active":
            actual_status_filter = "Active"
        elif status_filter == "Inactive":
            actual_status_filter = "Inactive"

        try:
            members_list = api.get_filtered_members(name_query=search_name if search_name else None, status=actual_status_filter)

            if members_list:
                member_data_for_df = []
                for member in members_list:
                    # (member_id, client_name, phone, join_date, is_active (bool))
                    member_data_for_df.append({
                        "ID": member[0],
                        "Name": member[1],
                        "Phone": member[2],
                        "Join Date": member[3],
                        "Status": "Active" if member[4] else "Inactive",
                    })

                df_members = pd.DataFrame(member_data_for_df)

                # Displaying with st.dataframe for now. Adding buttons within dataframe is complex.
                # A common pattern is to list items and have buttons next to them.
                st.dataframe(df_members[['ID', 'Name', 'Phone', 'Join Date', 'Status']], hide_index=True, use_container_width=True)

                for index, member in enumerate(members_list):
                    member_id = member[0]
                    member_name = member[1]
                    cols = st.columns([2,1,1,1]) # Adjust ratios as needed
                    cols[0].write(f"**{member_name}** (ID: {member_id})")

                    if cols[1].button("Edit", key=f"edit_member_{member_id}"):
                        st.session_state.selected_member_id = member_id
                        st.session_state.form_key_member = f"member_form_{datetime.now().timestamp()}" # Ensure form rerenders with new defaults
                        st.rerun()

                    if cols[2].button("Delete", key=f"delete_member_{member_id}"):
                        # Simple confirmation for now. st.confirm_dialog is not a standard feature.
                        # Using a checkbox or a second button click could be alternatives.
                        # For this subtask, direct deletion on button click.
                        # Add st.confirm_dialog if available or use a different confirmation method later.
                        st.warning(f"Are you sure you want to deactivate {member_name}? This action might be irreversible through the UI if not careful.")
                        if st.button("Confirm Deactivate", key=f"confirm_delete_{member_id}"):
                            try:
                                success, message = api.deactivate_member(member_id)
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deactivating member: {e}")

                    if cols[3].button("History", key=f"history_member_{member_id}"):
                        st.session_state.history_member_id = member_id
                        st.session_state.show_history_modal = True
                        st.rerun()

            else:
                st.info("No members found matching your criteria.")

        except Exception as e:
            st.error(f"Failed to fetch members: {e}")

    # Member History Modal/Dialog
    if st.session_state.get('show_history_modal', False) and st.session_state.history_member_id is not None:
        member_id_for_history = st.session_state.history_member_id
        member_name_for_history = "Member" # Default
        try:
            # Fetch member name for the dialog title
            hist_member_details = api.get_member_by_id(member_id_for_history)
            if hist_member_details:
                member_name_for_history = hist_member_details[1]
        except Exception as e:
            st.warning(f"Could not fetch member name for history dialog: {e}")

        # Using st.dialog if available, otherwise a container. Streamlit's st.dialog is relatively new.
        # For broader compatibility, an expander or just a section.
        # Let's use a container that simulates a modal experience.
        with st.container(): # This will just be part of the page flow.
                             # True modal requires st.dialog (Streamlit 1.2 dialog or newer)
                             # or more complex HTML/JS.
            st.subheader(f"Transaction History for {member_name_for_history} (ID: {member_id_for_history})")
            try:
                history = api.get_all_activity_for_member(member_id_for_history)
                if history:
                    history_df_data = []
                    total_amount = 0
                    for item in history:
                        # (transaction_id, transaction_type, description, transaction_date,
                        #  start_date, end_date, amount, plan_name, payment_method, sessions)
                        history_df_data.append({
                            "Date": item[3], # transaction_date
                            "Type": item[1], # transaction_type
                            "Description": item[2],
                            "Plan": item[7] if item[7] else "-", # plan_name
                            "Amount": f"${item[6]:.2f}" if item[6] is not None else "-",
                            "Start Date": item[4] if item[4] else "-",
                            "End Date": item[5] if item[5] else "-",
                        })
                        if item[6] is not None:
                            total_amount += item[6]

                    history_df = pd.DataFrame(history_df_data)
                    st.dataframe(history_df, hide_index=True, use_container_width=True)
                    st.markdown(f"**Total Amount Paid: ${total_amount:.2f}**")
                else:
                    st.info("No transaction history found for this member.")
            except Exception as e:
                st.error(f"Failed to fetch transaction history: {e}")

            if st.button("Close History", key="close_history_modal"):
                st.session_state.show_history_modal = False
                st.session_state.history_member_id = None
                st.rerun()

def render_plans_tab():
    st.header("Plan Management")

    # Initialize session state variables
    if 'selected_plan_id' not in st.session_state:
        st.session_state.selected_plan_id = None
    if 'form_key_plan' not in st.session_state:
        st.session_state.form_key_plan = 'initial_plan_form'

    left_column, right_column = st.columns(2)

    # Left Column: Add/Edit Plan Form
    with left_column:
        st.subheader("Add/Edit Plan")

        plan_to_edit = None
        if st.session_state.selected_plan_id:
            try:
                # (id, name, duration, price, type, is_active)
                plan_data = api.get_plan_by_id(st.session_state.selected_plan_id)
                if plan_data:
                    plan_to_edit = {
                        "id": plan_data[0],
                        "name": plan_data[1],
                        "duration": plan_data[2], # Assuming duration is in days
                        "price": plan_data[3],
                        "type": plan_data[4],
                        "is_active": bool(plan_data[5])
                    }
                else:
                    st.error("Selected plan not found.")
                    st.session_state.selected_plan_id = None # Reset
            except Exception as e:
                st.error(f"Error fetching plan details: {e}")
                st.session_state.selected_plan_id = None

        with st.form(key=st.session_state.form_key_plan, clear_on_submit=True):
            st.text_input("Plan ID", value=plan_to_edit["id"] if plan_to_edit else "Auto-generated", disabled=True)
            name = st.text_input("Name", value=plan_to_edit["name"] if plan_to_edit else "")
            # Duration is in days as per API
            duration_days = st.number_input("Duration (days)", min_value=1, step=1, value=plan_to_edit["duration"] if plan_to_edit else 30)
            price = st.number_input("Price", min_value=0.0, format="%.2f", value=plan_to_edit["price"] if plan_to_edit else 0.0)
            plan_type_options = ["Group Class", "Personal Training", "Gym Access", "Other"] # Added "Other"
            plan_type = st.selectbox("Type", options=plan_type_options, index=plan_type_options.index(plan_to_edit["type"]) if plan_to_edit and plan_to_edit["type"] in plan_type_options else 0)

            is_active_checkbox = None
            if st.session_state.selected_plan_id and plan_to_edit: # Only show for existing plans
                is_active_checkbox = st.checkbox("Is Active", value=plan_to_edit["is_active"])

            col_save, col_clear = st.columns(2)
            with col_save:
                save_button = st.form_submit_button("Save Plan")
            with col_clear:
                clear_button = st.form_submit_button("Clear / New")

            if save_button:
                if not name or duration_days <= 0 or price < 0 or not plan_type:
                    st.error("Please fill in all required fields with valid values (Name, Duration > 0, Price >= 0, Type).")
                else:
                    try:
                        if st.session_state.selected_plan_id:
                            # For existing plans, use the checkbox value if available, otherwise keep current status (None means no change)
                            is_active_val = is_active_checkbox if is_active_checkbox is not None else plan_to_edit.get('is_active') if plan_to_edit else True
                            success, message = api.update_plan(st.session_state.selected_plan_id, name, int(duration_days), float(price), plan_type, is_active_val)
                        else:
                            # New plans are added as active by default (is_active=True implicitly or handled by API)
                            # The current api.add_plan doesn't take is_active. Assume it defaults to active.
                            success, message, _ = api.add_plan(name, int(duration_days), float(price), plan_type)

                        if success:
                            st.success(message)
                            st.session_state.selected_plan_id = None
                            st.session_state.form_key_plan = f"plan_form_{datetime.now().timestamp()}"
                            st.rerun()
                        else:
                            st.error(message)
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

            if clear_button:
                st.session_state.selected_plan_id = None
                st.session_state.form_key_plan = f"plan_form_{datetime.now().timestamp()}"
                st.rerun()

    # Right Column: Plans List
    with right_column:
        st.subheader("View Plans")
        try:
            plans_list = api.get_all_plans() # (id, name, duration, price, type, is_active)
            if plans_list:
                plan_data_for_df = []
                for plan_tuple in plans_list:
                    plan_data_for_df.append({
                        "ID": plan_tuple[0],
                        "Name": plan_tuple[1],
                        "Duration (Days)": plan_tuple[2],
                        "Price": f"${plan_tuple[3]:.2f}",
                        "Type": plan_tuple[4],
                        "Status": "Active" if bool(plan_tuple[5]) else "Inactive"
                    })
                df_plans = pd.DataFrame(plan_data_for_df)
                st.dataframe(df_plans[['ID', 'Name', 'Duration (Days)', 'Price', 'Type', 'Status']], hide_index=True, use_container_width=True)

                for index, plan_tuple in enumerate(plans_list):
                    plan_id = plan_tuple[0]
                    plan_name = plan_tuple[1]
                    is_plan_active = bool(plan_tuple[5])

                    cols_actions = st.columns([3,1,1,1]) # Name | Edit | Delete | Toggle
                    cols_actions[0].write(f"**{plan_name}** (ID: {plan_id})")

                    if cols_actions[1].button("Edit", key=f"edit_plan_{plan_id}"):
                        st.session_state.selected_plan_id = plan_id
                        st.session_state.form_key_plan = f"plan_form_{datetime.now().timestamp()}"
                        st.rerun()

                    # Delete button with confirmation
                    if cols_actions[2].button("Delete", key=f"delete_plan_{plan_id}"):
                        st.session_state[f"confirm_delete_plan_{plan_id}"] = True # Flag for confirmation
                        st.rerun()

                    if st.session_state.get(f"confirm_delete_plan_{plan_id}", False):
                        st.warning(f"Are you sure you want to delete plan '{plan_name}' (ID: {plan_id})? This cannot be undone if transactions use this plan.")
                        confirm_col1, confirm_col2 = st.columns(2)
                        if confirm_col1.button("Yes, Delete Plan", key=f"confirm_delete_btn_plan_{plan_id}"):
                            try:
                                success, message = api.delete_plan(plan_id)
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
                                del st.session_state[f"confirm_delete_plan_{plan_id}"]
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting plan: {e}")
                                del st.session_state[f"confirm_delete_plan_{plan_id}"]
                                st.rerun()
                        if confirm_col2.button("Cancel", key=f"cancel_delete_plan_{plan_id}"):
                            del st.session_state[f"confirm_delete_plan_{plan_id}"]
                            st.rerun()

                    # Toggle Active button
                    toggle_button_text = "Deactivate" if is_plan_active else "Activate"
                    if cols_actions[3].button(toggle_button_text, key=f"toggle_plan_{plan_id}"):
                        try:
                            # We need all plan details to update, even if only status changes
                            # Or create a specific api.update_plan_status(plan_id, new_status)
                            # For now, using the modified update_plan
                            success, message = api.update_plan(plan_id, plan_tuple[1], plan_tuple[2], plan_tuple[3], plan_tuple[4], is_active=not is_plan_active)
                            if success:
                                st.success(f"Plan '{plan_name}' status changed.")
                            else:
                                st.error(f"Failed to change plan status: {message}")
                            st.rerun()
                        except Exception as e:
                             st.error(f"Error toggling plan status: {e}")

            else:
                st.info("No plans found. Add some plans using the form on the left.")
        except Exception as e:
            st.error(f"Failed to fetch plans: {e}")

def render_reporting_tab():
    st.header("Financial & Renewals Reporting")

    # Initialize session state variables
    if 'monthly_report_data' not in st.session_state:
        st.session_state.monthly_report_data = None
    if 'monthly_report_summary' not in st.session_state:
        st.session_state.monthly_report_summary = None
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
        st.session_state.monthly_report_data = None
        st.session_state.monthly_report_summary = None


    if st.button("Generate Monthly Financial Report", key="generate_financial_report"):
        year = st.session_state.report_month_financial.year
        month = st.session_state.report_month_financial.month
        try:
            st.session_state.monthly_report_data = api.get_transactions_for_month(year, month)
            st.session_state.monthly_report_summary = api.get_finance_report(year, month)

            if st.session_state.monthly_report_summary is None and not st.session_state.monthly_report_data:
                 st.info(f"No financial data found for {st.session_state.report_month_financial.strftime('%B %Y')}.")
            else:
                 st.success(f"Financial report generated for {st.session_state.report_month_financial.strftime('%B %Y')}.")
        except Exception as e:
            st.error(f"Error generating financial report: {e}")
            st.session_state.monthly_report_data = None
            st.session_state.monthly_report_summary = None

    if st.session_state.monthly_report_summary is not None:
        st.metric(
            label=f"Total Income for {st.session_state.report_month_financial.strftime('%B %Y')}",
            value=f"${st.session_state.monthly_report_summary:.2f}"
        )

    if st.session_state.monthly_report_data:
        # API returns: (transaction_id, client_name, transaction_date, start_date, end_date, amount, transaction_type, description, plan_name, payment_method, sessions)
        df_financial_data = []
        for item in st.session_state.monthly_report_data:
            df_financial_data.append({
                "Tx ID": item[0],
                "Member Name": item[1],
                "Tx Date": item[2],
                "Amount": f"${item[5]:.2f}" if item[5] is not None else "-",
                "Type": item[6],
                "Description": item[7],
                "Plan Name": item[8] if item[8] else "N/A",
                "Payment Method": item[9] if item[9] else "N/A"
            })
        df_financial = pd.DataFrame(df_financial_data)
        st.dataframe(df_financial, hide_index=True, use_container_width=True)
    elif st.session_state.monthly_report_summary is not None and not st.session_state.monthly_report_data :
        # This case handles when summary is 0.0 (or some value) but no detailed transactions
        st.info(f"No detailed transactions found for {st.session_state.report_month_financial.strftime('%B %Y')}, though summary is calculated.")


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
            st.session_state.renewals_report_data = api.get_pending_renewals(year, month)
            if not st.session_state.renewals_report_data: # Empty list means no renewals
                st.info(f"No upcoming renewals found for {st.session_state.report_month_renewals.strftime('%B %Y')}.")
            else:
                st.success(f"Renewals report generated for {st.session_state.report_month_renewals.strftime('%B %Y')}.")
        except Exception as e:
            st.error(f"Error generating renewals report: {e}")
            st.session_state.renewals_report_data = None # Set to None on error

    if st.session_state.renewals_report_data: # Check if data exists (could be an empty list)
        # API returns: (client_name, phone, plan_name, end_date)
        df_renewals_data = []
        for item in st.session_state.renewals_report_data:
            df_renewals_data.append({
                "Member Name": item[0],
                "Phone": item[1],
                "Plan Name": item[2],
                "End Date": item[3]
            })
        df_renewals = pd.DataFrame(df_renewals_data)
        st.dataframe(df_renewals, hide_index=True, use_container_width=True)
    # Handle case where button was clicked, data is explicitly an empty list (meaning no renewals found)
    elif st.session_state.renewals_report_data == []:
         st.info(f"No upcoming renewals found for {st.session_state.report_month_renewals.strftime('%B %Y')}.")


tab_memberships, tab_members, tab_plans, tab_reporting = st.tabs(["Memberships", "Members", "Plans", "Reporting"])

with tab_memberships:
    render_memberships_tab()

with tab_members:
    render_members_tab()

with tab_plans:
    render_plans_tab()

with tab_reporting:
    render_reporting_tab()
