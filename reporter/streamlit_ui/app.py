import streamlit as st
import pandas as pd
from datetime import date, datetime # Added datetime
import sqlite3
from reporter.app_api import AppAPI
from reporter.database_manager import DB_FILE # To get the database path

# --- Database Connection & API Initialization ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    # conn.row_factory = sqlite3.Row # Optional: for dict-like row access if you prefer
    return conn

api = AppAPI(get_db_connection())

# --- Tab Rendering Functions ---
def render_memberships_tab():
    st.header("Membership & Financials")

    # Initialize session state variables
    if 'memberships_form_key' not in st.session_state:
        st.session_state.memberships_form_key = 'initial_memberships_form'
    if 'close_books_month_key' not in st.session_state: # Used for the date input widget itself
        st.session_state.close_books_month_key = date.today().replace(day=1)
    if 'current_book_month_str' not in st.session_state: # Stores YYYY-MM for display
         st.session_state.current_book_month_str = st.session_state.close_books_month_key.strftime("%Y-%m")
    if 'book_status_message' not in st.session_state:
        st.session_state.book_status_message = ""
    # transactions_data is not explicitly pre-initialized here; fetched on demand by filters.

    # --- Data fetching for selectboxes ---
    try:
        all_members = api.get_all_members() # Assuming this returns (id, name, ...)
        member_options = {member[0]: member[1] for member in all_members} if all_members else {}
    except Exception as e:
        st.error(f"Error fetching members: {e}")
        member_options = {}
        all_members = [] # Ensure it's an iterable

    try:
        all_plans = api.get_all_plans() # Assuming (id, name, ..., is_active)
        # Filter for active plans for new memberships
        active_plan_options = {plan[0]: plan[1] for plan in all_plans if bool(plan[5])} if all_plans else {}
    except Exception as e:
        st.error(f"Error fetching plans: {e}")
        active_plan_options = {}
        all_plans = [] # Ensure it's an iterable


    left_column, right_column = st.columns(2)

    # Left Column: Add Membership Form
    with left_column:
        st.subheader("Add New Membership/Transaction")
        with st.form(key=st.session_state.memberships_form_key, clear_on_submit=True):
            selected_member_id = st.selectbox("Select Member", options=list(member_options.keys()), format_func=lambda x: member_options.get(x, "Unknown Member"))
            selected_plan_id = st.selectbox("Select Plan", options=list(active_plan_options.keys()), format_func=lambda x: active_plan_options.get(x, "Unknown Plan"))

            transaction_date = st.date_input("Transaction Date", value=date.today())
            amount_paid = st.number_input("Amount Paid", min_value=0.0, format="%.2f")
            payment_method_options = ["Cash", "Card", "Bank Transfer", "Other"]
            payment_method = st.selectbox("Payment Method", options=payment_method_options)

            submit_button = st.form_submit_button("Save Transaction")

            if submit_button:
                if not selected_member_id or not selected_plan_id or amount_paid <= 0:
                    st.error("Please select a member, a plan, and enter a valid amount.")
                else:
                    try:
                        # For simplicity, using 'new_subscription'. Could be 'renewal' or 'payment' based on context.
                        # Using transaction_date for both start_date and payment_date.
                        success, message = api.add_transaction(
                            transaction_type='new_subscription',
                            member_id=selected_member_id,
                            plan_id=selected_plan_id,
                            start_date=transaction_date.strftime("%Y-%m-%d"),
                            amount_paid=float(amount_paid),
                            payment_method=payment_method,
                            payment_date=transaction_date.strftime("%Y-%m-%d")
                        )
                        if success:
                            st.success(message)
                            st.session_state.memberships_form_key = f"memberships_form_{datetime.now().timestamp()}"
                            # Trigger refresh of transactions list - simple way is rerun, or manage data in session_state
                            st.rerun()
                        else:
                            st.error(message)
                    except Exception as e:
                        st.error(f"Failed to save transaction: {e}")

    # Right Column: Recent Transactions List & Filters
    with right_column:
        st.subheader("Recent Transactions")

        filter_member_id = st.selectbox("Filter by Member", options=["All Members"] + list(member_options.keys()), format_func=lambda x: member_options.get(x, "All Members"))
        filter_plan_id = st.selectbox("Filter by Plan", options=["All Plans"] + list(active_plan_options.keys()), format_func=lambda x: active_plan_options.get(x, "All Plans")) # Using active_plan_options for consistency

        col_start_date, col_end_date = st.columns(2)
        filter_start_date = col_start_date.date_input("From Date", value=None)
        filter_end_date = col_end_date.date_input("To Date", value=None)

        if st.button("Refresh Transactions", key="refresh_transactions"):
            try:
                api_member_id = filter_member_id if filter_member_id != "All Members" else None
                api_plan_id = filter_plan_id if filter_plan_id != "All Plans" else None
                api_start_date = filter_start_date.strftime("%Y-%m-%d") if filter_start_date else None
                api_end_date = filter_end_date.strftime("%Y-%m-%d") if filter_end_date else None

                # Store fetched data in session state to persist unless filters change and refresh is hit
                st.session_state.transactions_data = api.get_transactions_filtered(
                    member_id=api_member_id,
                    plan_id=api_plan_id,
                    start_date_filter=api_start_date,
                    end_date_filter=api_end_date,
                    limit=100 # Increased limit
                )
            except Exception as e:
                st.error(f"Error fetching transactions: {e}")
                st.session_state.transactions_data = []

        # Display transactions from session state
        if 'transactions_data' in st.session_state and st.session_state.transactions_data:
            transactions_to_display = []
            for tx in st.session_state.transactions_data:
                # (transaction_id, transaction_date, member_name, plan_name, amount, payment_method, description, start_date, end_date)
                transactions_to_display.append({
                    "ID": tx[0],
                    "Date": tx[1],
                    "Member": tx[2] if tx[2] else "N/A",
                    "Plan": tx[3] if tx[3] else "N/A",
                    "Amount": f"${tx[4]:.2f}" if tx[4] is not None else "-",
                    "Method": tx[5] if tx[5] else "N/A",
                    "Description": tx[6] if tx[6] else "-"
                })
            df_transactions = pd.DataFrame(transactions_to_display)
            st.dataframe(df_transactions, hide_index=True, use_container_width=True)

            for tx_original_data in st.session_state.transactions_data:
                tx_id = tx_original_data[0]
                tx_desc = tx_original_data[6] or tx_original_data[1] # Use description or date as fallback display

                action_cols = st.columns([4,1])
                action_cols[0].write(f"Tx ID: {tx_id} - {tx_desc[:30]}...")
                if action_cols[1].button("Delete", key=f"delete_tx_{tx_id}"):
                    st.session_state[f"confirm_delete_tx_{tx_id}"] = True
                    st.rerun() # Rerun to show confirmation

                if st.session_state.get(f"confirm_delete_tx_{tx_id}", False):
                    st.warning(f"Are you sure you want to delete transaction ID {tx_id}?")
                    confirm_del_col1, confirm_del_col2 = st.columns(2)
                    if confirm_del_col1.button("Yes, Delete Transaction", key=f"confirm_delete_btn_tx_{tx_id}"):
                        try:
                            success, message = api.delete_transaction(tx_id)
                            if success:
                                st.success(message)
                                # Invalidate transactions_data so it's refreshed if "Refresh" is hit next
                                if 'transactions_data' in st.session_state: del st.session_state.transactions_data
                            else:
                                st.error(message)
                            del st.session_state[f"confirm_delete_tx_{tx_id}"]
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting transaction: {e}")
                            del st.session_state[f"confirm_delete_tx_{tx_id}"]
                            st.rerun()
                    if confirm_del_col2.button("Cancel", key=f"cancel_delete_tx_{tx_id}"):
                        del st.session_state[f"confirm_delete_tx_{tx_id}"]
                        st.rerun()
        elif 'transactions_data' in st.session_state and not st.session_state.transactions_data:
            st.info("No transactions found for the selected filters.")
        else:
            st.info("Click 'Refresh Transactions' to load data.")


    # Bottom Section: Close Books
    st.divider()
    st.subheader("Close Books for Month")

    selected_month_for_books = st.date_input("Select Month to Manage", value=st.session_state.close_books_month_key, key="close_books_date_selector")

    # Update current_book_month_str whenever the date input changes
    st.session_state.current_book_month_str = selected_month_for_books.strftime("%Y-%m")

    if st.button("Check/Refresh Book Status", key="refresh_book_status"):
        try:
            status = api.get_book_status(st.session_state.current_book_month_str)
            st.session_state.book_status_message = f"Books for {st.session_state.current_book_month_str} are: **{status.upper()}**"
        except Exception as e:
            st.session_state.book_status_message = f"Error fetching book status: {e}"

    if st.session_state.book_status_message:
        st.markdown(st.session_state.book_status_message)

    current_status = ""
    if "are: **CLOSED**" in st.session_state.book_status_message:
        current_status = "closed"
    elif "are: **OPEN**" in st.session_state.book_status_message:
        current_status = "open"

    if current_status:
        action_button_label = f"Reopen Books for {st.session_state.current_book_month_str}" if current_status == "closed" else f"Close Books for {st.session_state.current_book_month_str}"
        new_status_on_action = "open" if current_status == "closed" else "closed"

        if st.button(action_button_label, key="toggle_book_status_action"):
            try:
                success = api.set_book_status(st.session_state.current_book_month_str, new_status_on_action)
                if success:
                    st.success(f"Books for {st.session_state.current_book_month_str} are now {new_status_on_action.upper()}.")
                    # Refresh status message
                    status = api.get_book_status(st.session_state.current_book_month_str)
                    st.session_state.book_status_message = f"Books for {st.session_state.current_book_month_str} are: **{status.upper()}**"
                else:
                    st.error(f"Failed to {new_status_on_action} books for {st.session_state.current_book_month_str}.")
                st.rerun()
            except Exception as e:
                st.error(f"Error setting book status: {e}")

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
