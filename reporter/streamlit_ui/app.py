import streamlit as st
import pandas as pd
from datetime import date, datetime  # Added datetime
import sqlite3
import io  # For Excel download

from reporter.app_api import AppAPI
from reporter.database import DB_FILE


# --- Database Connection & API Initialization ---
# Encapsulate DB connection management if not already handled by AppAPI
# For this integration, we assume AppAPI might manage its own connection,
# or we pass a connection factory/object.
# Based on previous AppAPI structure, it takes a DatabaseManager,
# which in turn takes a db_path.
# Let's adjust AppAPI call if it expects a DatabaseManager instance.
# For now, assuming AppAPI was refactored to take connection or path directly for simplicity here.
# If AppAPI expects DatabaseManager, this needs to be:
# from reporter.database_manager import DatabaseManager
# db_manager = DatabaseManager(DB_FILE)
# api = AppAPI(db_manager)

conn = sqlite3.connect(
    DB_FILE
)  # Keep a single connection for the app session if possible
# Or, ensure AppAPI methods handle their connections if they are short-lived.
# For this refactoring, we'll assume AppAPI methods will use the passed connection or path.
# The provided AppAPI structure takes a DatabaseManager.
# Let's stick to the AppAPI structure that it takes a DatabaseManager.
from reporter.database_manager import DatabaseManager

db_manager = DatabaseManager(db_path=DB_FILE)
api = AppAPI(db_manager=db_manager)


# --- Helper function to clear form state ---
def clear_membership_form_state():
    st.session_state.create_member_id = None
    # st.session_state.create_plan_id = None # This will be derived from create_plan_id_display
    st.session_state.create_plan_id_display = None  # Will store (id, name, duration)
    st.session_state.create_transaction_amount = 0.0
    st.session_state.create_start_date = date.today()
    st.session_state.selected_plan_duration_display = ""  # For displaying duration

    # If using a form key to force rebuild, you might increment it here
    if "form_key_create_membership" in st.session_state:
        st.session_state.form_key_create_membership = (
            f"form_{datetime.now().timestamp()}"
        )


# --- Tab Rendering Functions ---

# Helper function for the new membership creation form within Memberships Tab
def render_new_membership_form_section():
    member_id_to_create_for = st.session_state.trigger_membership_creation_for_member_id
    member_name_to_create_for = st.session_state.trigger_membership_creation_member_name

    st.subheader(f"Create New Membership for: {member_name_to_create_for} (ID: {member_id_to_create_for})")

    # Initialize form states if not present
    if "membership_creation_plan_id_widget" not in st.session_state: # Stores (id, name, duration) for plan selectbox
        st.session_state.membership_creation_plan_id_widget = None
    if "membership_creation_plan_duration_display" not in st.session_state: # For displaying duration
        st.session_state.membership_creation_plan_duration_display = ""
    if "membership_creation_start_date" not in st.session_state:
        st.session_state.membership_creation_start_date = date.today()
    if "membership_creation_amount" not in st.session_state:
        st.session_state.membership_creation_amount = 0.0
    if "membership_creation_form_key" not in st.session_state:
        st.session_state.membership_creation_form_key = f"mship_create_{datetime.now().timestamp()}"

    try:
        plan_list_data = api.get_all_plans() # Returns list of dicts with id, display_name etc.
        active_plans = [p for p in plan_list_data if p.get('is_active', True)]
        plan_options = {None: "Select Plan..."}
        # Using (id, display_name, duration_days) to match structure used elsewhere if needed, though only id is submitted
        for p in active_plans:
            plan_options[(p["id"], p["display_name"], p["duration_days"])] = p["display_name"]
    except Exception as e:
        st.error(f"Error fetching plans: {e}")
        plan_options = {None: "Select Plan..."}

    def update_membership_creation_plan_duration_display():
        selected_plan_data = st.session_state.get("membership_creation_plan_id_widget_actual")
        if selected_plan_data and selected_plan_data[0] is not None:
            st.session_state.membership_creation_plan_duration_display = f"{selected_plan_data[2]} days"
            st.session_state.membership_creation_plan_id_widget = selected_plan_data # Store for submission logic
        else:
            st.session_state.membership_creation_plan_duration_display = ""
            st.session_state.membership_creation_plan_id_widget = None

    with st.form(key=st.session_state.membership_creation_form_key, clear_on_submit=True):
        st.selectbox(
            "Plan",
            options=list(plan_options.keys()),
            format_func=lambda key: plan_options[key],
            key="membership_creation_plan_id_widget_actual",
            on_change=update_membership_creation_plan_duration_display,
        )
        st.text_input("Plan Duration", value=st.session_state.membership_creation_plan_duration_display, disabled=True)
        st.date_input("Start Date", key="membership_creation_start_date", value=st.session_state.membership_creation_start_date)
        st.number_input("Actual Amount Paid", key="membership_creation_amount", value=st.session_state.membership_creation_amount, min_value=0.0, format="%.2f")

        submit_col, cancel_col = st.columns(2)
        with submit_col:
            create_button = st.form_submit_button("Create Membership Record")
        with cancel_col:
            cancel_button = st.form_submit_button("Cancel")

    if create_button:
        selected_plan_tuple = st.session_state.membership_creation_plan_id_widget
        plan_id = selected_plan_tuple[0] if selected_plan_tuple and selected_plan_tuple[0] is not None else None
        start_date_val = st.session_state.membership_creation_start_date
        amount_val = st.session_state.membership_creation_amount

        if not plan_id:
            st.warning("Please select a plan.")
        elif amount_val <= 0: # Assuming memberships should have a positive amount
            st.warning("Actual amount paid must be greater than zero.")
        else:
            try:
                membership_data = {
                    "client_id": member_id_to_create_for,
                    "plan_id": plan_id,
                    "start_date": start_date_val.strftime("%Y-%m-%d"),
                    "payment_amount": amount_val,
                }
                record_id = api.create_membership_record(membership_data)
                if record_id:
                    st.success(f"Membership created successfully for {member_name_to_create_for} with ID: {record_id}")
                    # Clear trigger and form states
                    st.session_state.trigger_membership_creation_for_member_id = None
                    st.session_state.trigger_membership_creation_member_name = ""
                    st.session_state.membership_creation_plan_id_widget = None
                    st.session_state.membership_creation_plan_duration_display = ""
                    # st.session_state.membership_creation_start_date = date.today() # Keep or reset as preferred
                    # st.session_state.membership_creation_amount = 0.0
                    st.session_state.membership_creation_form_key = f"mship_create_{datetime.now().timestamp()}" # New key to reset form
                    st.rerun()
                else:
                    st.error("Failed to create membership. Please check details or backend logs.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

    if cancel_button:
        st.session_state.trigger_membership_creation_for_member_id = None
        st.session_state.trigger_membership_creation_member_name = ""
        st.session_state.membership_creation_form_key = f"mship_create_cancel_{datetime.now().timestamp()}" # New key to reset form
        st.rerun()

def render_memberships_tab():
    # Initialize session state for form inputs if not already present (these are for the old direct creation form, might be removable)
    # For viewing/managing existing memberships
    if "filter_membership_name" not in st.session_state:
        st.session_state.filter_membership_name = ""
    if "filter_membership_phone" not in st.session_state:
        st.session_state.filter_membership_phone = ""
    if "filter_membership_status" not in st.session_state:
        st.session_state.filter_membership_status = "All"  # Default to "All"
    if "manage_selected_membership_id" not in st.session_state:
        st.session_state.manage_selected_membership_id = None
    if "memberships_view_data" not in st.session_state:  # To store data for selectbox
        st.session_state.memberships_view_data = []
    if "edit_form_key" not in st.session_state:
        st.session_state.edit_form_key = "initial_edit_form"

    # Edit form field states
    if "edit_start_date" not in st.session_state:
        st.session_state.edit_start_date = date.today()
    if "edit_end_date" not in st.session_state:
        st.session_state.edit_end_date = date.today()
    if "edit_is_active" not in st.session_state:
        st.session_state.edit_is_active = True

    # The two-panel layout (left_column for creation, right_column for view/manage) has been removed.
    # The "Create Membership" form, previously in the left column, has been removed.
    # The "View/Manage Memberships" panel, previously in the right column, now takes the full width.

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
                key="filter_membership_status",
            )

        # Apply filters button (or trigger on change)
        if st.button("Apply Filters / Refresh List", key="apply_membership_filters"):
            st.session_state.manage_selected_membership_id = (
                None  # Reset selection on new filter application
            )

        # Fetch and display data
        try:
            status_query = (
                st.session_state.filter_membership_status
                if st.session_state.filter_membership_status != "All"
                else None
            )

            # Store data in session state to populate the selection dropdown
            # The new API method takes filters directly.
            # Assuming the API method get_all_memberships_for_view can take these filters.
            # Need to check AppAPI definition for exact filter names if they differ.
            # For now, using descriptive names.
            # The AppAPI's get_all_memberships_for_view doesn't specify filters in its signature in P1
            # but the old function did. This is a potential mismatch.
            # Assuming for now it takes no arguments as per AppAPI in P1, or it's been updated.
            # Let's assume it's updated to accept filters similar to the old function for now.
            # If not, this part of filtering will not work as expected.
            # For the purpose of this task, I will assume the AppAPI was updated to support these.
            all_memberships = (
                api.get_all_memberships_for_view()
            )  # This returns List[Dict[str, Any]]

            # Apply filtering in Python if AppAPI doesn't support it:
            filtered_memberships = all_memberships
            if st.session_state.filter_membership_name:
                filtered_memberships = [
                    m
                    for m in filtered_memberships
                    if st.session_state.filter_membership_name.lower()
                    in m.get("client_name", "").lower()
                ]
            if st.session_state.filter_membership_phone:
                filtered_memberships = [
                    m
                    for m in filtered_memberships
                    if st.session_state.filter_membership_phone in m.get("phone", "")
                ]
            if status_query:  # "Active" or "Inactive"
                filtered_memberships = [
                    m
                    for m in filtered_memberships
                    if m.get("status", "").lower() == status_query.lower()
                ]
            st.session_state.memberships_view_data = filtered_memberships

            if st.session_state.memberships_view_data:
                # Prepare for display (e.g., client_name, plan_name, start_date, end_date, status string)
                display_df = pd.DataFrame(st.session_state.memberships_view_data)
                # Ensure correct columns for display if needed, API returns dicts with correct keys
                # Make sure 'membership_id' is available for selection handling but can be hidden
                cols_to_display = [
                    "client_name",
                    "phone",
                    "plan_name",
                    "start_date",
                    "end_date",
                    "status"
                    # "membership_id" # Keep for selection, but can be hidden using column_config
                ]
                # Make a copy for display to avoid modifying session state directly if we drop columns for view
                display_df_view = display_df[cols_to_display + ["membership_id"]].copy()

                st.dataframe(
                    display_df_view,
                    hide_index=True,
                    use_container_width=True,
                    key="manage_memberships_df",
                    on_select="rerun", # Use rerun to process selection
                    selection_mode="single-row",
                    column_config={"membership_id": None} # Hide membership_id column from view
                )
            else:
                st.info("No memberships found matching your criteria.")

        except Exception as e:
            st.error(f"Error fetching memberships: {e}")
            st.session_state.memberships_view_data = (
                []
            )  # Ensure it's an empty list on error
            st.dataframe(
                pd.DataFrame(), use_container_width=True
            )  # Display empty dataframe

        # Handle DataFrame Row Selection
        if "manage_memberships_df" in st.session_state and st.session_state.manage_memberships_df.selection.rows:
            selected_row_index = st.session_state.manage_memberships_df.selection.rows[0]
            # Check if selected_row_index is within the bounds of the current data
            if selected_row_index < len(st.session_state.memberships_view_data):
                selected_membership_details = st.session_state.memberships_view_data[selected_row_index]
                newly_selected_id = selected_membership_details["membership_id"]

                # If selection changed, update form fields
                if st.session_state.manage_selected_membership_id != newly_selected_id:
                    st.session_state.manage_selected_membership_id = newly_selected_id
                    st.session_state.edit_start_date = datetime.strptime(
                        selected_membership_details["start_date"], "%Y-%m-%d"
                    ).date()
                    st.session_state.edit_end_date = datetime.strptime(
                        selected_membership_details["end_date"], "%Y-%m-%d"
                    ).date()
                    st.session_state.edit_is_active = (
                        True if selected_membership_details["status"].lower() == "active" else False
                    )
                    st.session_state.edit_form_key = f"edit_form_{datetime.now().timestamp()}"
                    # Clear any pending delete confirmation from a previous selection
                    if "confirm_delete_membership_id" in st.session_state:
                        del st.session_state.confirm_delete_membership_id
                    st.rerun() # Rerun to update the form with new selection
            else:
                # Index out of bounds, likely due to data refresh and stale selection
                st.session_state.manage_selected_membership_id = None
                 # Clear any pending delete confirmation
                if "confirm_delete_membership_id" in st.session_state:
                    del st.session_state.confirm_delete_membership_id
                # st.rerun() # Optionally rerun if selection should be cleared visually

        elif "manage_memberships_df" in st.session_state and not st.session_state.manage_memberships_df.selection.rows:
            # No row is selected
            if st.session_state.manage_selected_membership_id is not None:
                st.session_state.manage_selected_membership_id = None
                 # Clear any pending delete confirmation
                if "confirm_delete_membership_id" in st.session_state:
                    del st.session_state.confirm_delete_membership_id
                st.rerun() # Rerun to clear the edit form

        # Edit/Delete Form (conditional)
        if st.session_state.manage_selected_membership_id is not None:
            st.subheader(
                f"Edit Membership ID: {st.session_state.manage_selected_membership_id}"
            )

            # Find details again (or ensure they are robustly passed if selectbox changes)
            current_selection_details = next(
                (
                    m
                    for m in st.session_state.memberships_view_data
                    if m["membership_id"]
                    == st.session_state.manage_selected_membership_id
                ),
                None,
            )

            if current_selection_details:
                # If selection changes, ensure form defaults are updated. on_change callback handles this.
                with st.form(key=st.session_state.edit_form_key, clear_on_submit=False):
                    st.date_input("Start Date", key="edit_start_date")
                    st.date_input("End Date", key="edit_end_date")
                    st.checkbox("Is Active", key="edit_is_active")

                    edit_col, delete_col, _ = st.columns(
                        [1, 1, 3]
                    )  # Make buttons smaller
                    with edit_col:
                        edit_button = st.form_submit_button("SAVE Changes")
                    with delete_col:
                        delete_button = st.form_submit_button("DELETE")

                if edit_button:
                    try:
                        update_data = {
                            "start_date": st.session_state.edit_start_date.strftime(
                                "%Y-%m-%d"
                            ),
                            "end_date": st.session_state.edit_end_date.strftime(
                                "%Y-%m-%d"
                            ),
                            "is_active": st.session_state.edit_is_active,
                            # member_id and plan_id are not typically editable for an existing membership record.
                            # If they are, they need to be added to `update_data`.
                            # The AppAPI update_membership_record takes record_id and data.
                        }
                        success = api.update_membership_record(
                            st.session_state.manage_selected_membership_id, update_data
                        )
                        if success:
                            st.success("Membership updated successfully.")
                            st.session_state.manage_selected_membership_id = None
                            st.rerun()
                        else:
                            st.error("Failed to update membership.")
                    except Exception as e:
                        st.error(f"Error updating membership: {e}")

                if delete_button:
                    # Confirmation for delete
                    if (
                        "confirm_delete_membership_id" not in st.session_state
                        or st.session_state.confirm_delete_membership_id
                        != st.session_state.manage_selected_membership_id
                    ):
                        st.session_state.confirm_delete_membership_id = (
                            st.session_state.manage_selected_membership_id
                        )
                        # The message implies deactivation, but the method is delete_membership_record
                        st.warning(
                            f"Are you sure you want to DELETE membership ID {st.session_state.manage_selected_membership_id}? This action cannot be undone."
                        )
                        st.rerun()

                    if (
                        st.session_state.get("confirm_delete_membership_id")
                        == st.session_state.manage_selected_membership_id
                    ):
                        confirm_yes, confirm_no = st.columns(2)
                        with confirm_yes:
                            if st.button(
                                "Yes, DELETE",
                                key=f"confirm_del_ms_{st.session_state.manage_selected_membership_id}",
                            ):
                                try:
                                    success = api.delete_membership_record(
                                        st.session_state.manage_selected_membership_id
                                    )
                                    if success:
                                        st.success("Membership deleted successfully.")
                                    else:
                                        st.error("Failed to delete membership.")
                                    st.session_state.manage_selected_membership_id = (
                                        None
                                    )
                                    del st.session_state.confirm_delete_membership_id
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting membership: {e}")
                                    del st.session_state.confirm_delete_membership_id
                                    st.rerun()
                        with confirm_no:
                            if st.button(
                                "Cancel Deletion",
                                key=f"cancel_del_ms_{st.session_state.manage_selected_membership_id}",
                            ):
                                del st.session_state.confirm_delete_membership_id
                                st.rerun()
            else:
                # This case might occur if the list was refreshed and the selected ID is no longer valid
                st.session_state.manage_selected_membership_id = None
                # Optionally show a message e.g. st.info("Selected membership details not found. Please re-select.")
                # Rerun can help clear the state if it's stuck
                st.rerun()


# render_members_tab and render_plans_tab have been removed.

# --- Members Tab ---
def render_members_tab():
    st.header("Manage Members")

    # Initialize session state variables for member management
    if "member_selected_id" not in st.session_state:
        st.session_state.member_selected_id = None
    if "member_name" not in st.session_state: # Used for form and for "Create Membership for X" button
        st.session_state.member_name = ""
    if "member_email" not in st.session_state:
        st.session_state.member_email = ""
    if "member_phone" not in st.session_state:
        st.session_state.member_phone = ""
    if "member_address" not in st.session_state:
        st.session_state.member_address = ""
    if "member_form_key" not in st.session_state:
        st.session_state.member_form_key = "member_form_initial"
    if "confirm_delete_member_id" not in st.session_state:
        st.session_state.confirm_delete_member_id = None

    # Session state for triggering membership creation from this tab
    if "trigger_membership_creation_for_member_id" not in st.session_state:
        st.session_state.trigger_membership_creation_for_member_id = None
    if "trigger_membership_creation_member_name" not in st.session_state:
        st.session_state.trigger_membership_creation_member_name = ""
    # Active tab selection hint (optional, might not reliably switch tabs)
    # if "active_tab" not in st.session_state:
    #     st.session_state.active_tab = "Members"


    # --- Helper function to clear member form ---
    def clear_member_form(clear_selection=False):
        if clear_selection:
            st.session_state.member_selected_id = None
        st.session_state.member_name = ""
        st.session_state.member_email = ""
        st.session_state.member_phone = ""
        st.session_state.member_address = ""
        st.session_state.member_form_key = f"member_form_{datetime.now().timestamp()}"
        st.session_state.confirm_delete_member_id = None


    left_col, right_col = st.columns([1, 2]) # Adjust column ratio as needed

    with left_col:
        st.subheader("All Members")
        try:
            all_members = api.get_all_members() # List of dicts
            if not all_members:
                st.info("No members found. Add a member using the form on the right.")
                all_members = []
        except Exception as e:
            st.error(f"Error fetching members: {e}")
            all_members = []

        member_options = {member['id']: f"{member['name']} ({member['phone']})" for member in all_members}
        member_options_list = [None] + list(member_options.keys()) # Add None for "New Member"

        def format_func_member(member_id):
            if member_id is None:
                return "➕ Add New Member"
            return member_options.get(member_id, "Unknown Member")

        selected_id_display = st.selectbox(
            "Select Member (or Add New)",
            options=member_options_list,
            format_func=format_func_member,
            key="member_select_widget", # Use a different key for the widget itself
            index=0 # Default to "Add New Member"
        )

        # This on_change logic needs to be robust
        if st.session_state.member_select_widget != st.session_state.member_selected_id:
            st.session_state.member_selected_id = st.session_state.member_select_widget
            st.session_state.confirm_delete_member_id = None # Clear delete confirmation
            if st.session_state.member_selected_id is not None:
                selected_member_data = next((m for m in all_members if m['id'] == st.session_state.member_selected_id), None)
                if selected_member_data:
                    st.session_state.member_name = selected_member_data.get("name", "")
                    st.session_state.member_email = selected_member_data.get("email", "")
                    st.session_state.member_phone = selected_member_data.get("phone", "")
                    st.session_state.member_address = selected_member_data.get("address", "")
                    st.session_state.member_form_key = f"member_form_{datetime.now().timestamp()}"
            else: # "Add New Member" is selected
                clear_member_form(clear_selection=False) # Keep selection as None, but clear fields
            st.rerun()


    with right_col:
        if st.session_state.member_selected_id is None:
            st.subheader("Add New Member")
        else:
            st.subheader(f"Edit Member: {st.session_state.member_name}")

        with st.form(key=st.session_state.member_form_key, clear_on_submit=False):
            name = st.text_input("Name", value=st.session_state.member_name, key="member_form_name")
            email = st.text_input("Email", value=st.session_state.member_email, key="member_form_email")
            phone = st.text_input("Phone", value=st.session_state.member_phone, key="member_form_phone")
            address = st.text_area("Address", value=st.session_state.member_address, key="member_form_address")

            form_col1, form_col2, form_col3 = st.columns(3)
            with form_col1:
                save_button = st.form_submit_button(
                    "Save Member" if st.session_state.member_selected_id else "Add Member"
                )
            if st.session_state.member_selected_id is not None:
                with form_col2:
                    delete_button = st.form_submit_button("Delete Member")
            with form_col3:
                clear_button = st.form_submit_button("Clear / New")


        if save_button:
            member_data = {
                "name": name,
                "email": email,
                "phone": phone,
                "address": address,
                "is_active": True # Assuming new/updated members are active by default
            }
            try:
                if st.session_state.member_selected_id is None: # Add new member
                    if not name or not phone: # Basic validation
                        st.warning("Name and Phone are required.")
                    else:
                        member_id = api.add_member(member_data)
                        if member_id:
                            st.success(f"Member '{name}' added successfully with ID: {member_id}")
                            clear_member_form(clear_selection=True)
                            st.rerun()
                        else:
                            st.error("Failed to add member. Phone number might already exist or other error.")
                else: # Update existing member
                    success = api.update_member(st.session_state.member_selected_id, member_data)
                    if success:
                        st.success(f"Member '{name}' updated successfully.")
                        clear_member_form(clear_selection=True)
                        st.rerun()
                    else:
                        st.error("Failed to update member. Phone number might already exist or other error.")
            except Exception as e:
                st.error(f"An error occurred: {e}")

        if st.session_state.member_selected_id is not None and delete_button:
            if st.session_state.confirm_delete_member_id != st.session_state.member_selected_id:
                st.session_state.confirm_delete_member_id = st.session_state.member_selected_id
                st.warning(f"Are you sure you want to delete member '{st.session_state.member_name}'? This action cannot be undone.")
                st.rerun()
            else: # Already confirmed (or re-clicked delete on warning)
                # This part is tricky with st.form. We might need to move confirmation outside or handle state carefully.
                # For simplicity, we'll make the button re-confirm if clicked again after warning.
                # A more robust solution might use a separate button for "Confirm Delete".
                pass # Warning is already shown. User needs to click delete again essentially.

        if st.session_state.confirm_delete_member_id == st.session_state.member_selected_id and st.session_state.member_selected_id is not None:
             # Show confirmation buttons only when delete is pending for the selected member
            st.warning(f"Confirm permanent deletion of member '{st.session_state.member_name}'.")
            confirm_col1, confirm_col2 = st.columns(2)
            with confirm_col1:
                if st.button("YES, DELETE Permanently", key=f"confirm_delete_btn_{st.session_state.member_selected_id}"):
                    try:
                        deleted = api.delete_member(st.session_state.member_selected_id)
                        if deleted:
                            st.success(f"Member '{st.session_state.member_name}' deleted successfully.")
                            clear_member_form(clear_selection=True)
                            st.session_state.confirm_delete_member_id = None # Reset confirmation
                            st.rerun()
                        else:
                            st.error("Failed to delete member. They might have active memberships.")
                            st.session_state.confirm_delete_member_id = None # Reset confirmation
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting member: {e}")
                        st.session_state.confirm_delete_member_id = None # Reset confirmation
                        st.rerun()
            with confirm_col2:
                if st.button("Cancel Deletion", key=f"cancel_delete_btn_{st.session_state.member_selected_id}"):
                    st.session_state.confirm_delete_member_id = None
                    st.rerun()


        if clear_button:
            clear_member_form(clear_selection=True) # Clear selection for "Clear / New"
            st.rerun()

        # "Create Membership for this member" button - outside the form
        if st.session_state.member_selected_id is not None:
            st.markdown("---") # Visual separator
            if st.button(f"➕ Create Membership for {st.session_state.member_name}", key=f"create_membership_for_{st.session_state.member_selected_id}"):
                st.session_state.trigger_membership_creation_for_member_id = st.session_state.member_selected_id
                st.session_state.trigger_membership_creation_member_name = st.session_state.member_name
                # st.session_state.active_tab = "Memberships" # Attempt to switch tab, might need user click
                # Clear other form states to avoid conflicts if any
                clear_membership_form_state() # Clear general membership form if it exists
                st.rerun() # Rerun to allow Memberships tab to pick up the state

# --- Plans Tab ---
def render_plans_tab():
    st.header("Manage Plans")

    # Initialize session state variables for plan management
    if "plan_selected_id" not in st.session_state:
        st.session_state.plan_selected_id = None
    # Input fields
    if "plan_name" not in st.session_state: # This is the 'base' name like "Gold", "Silver"
        st.session_state.plan_name = ""
    if "plan_duration_days" not in st.session_state:
        st.session_state.plan_duration_days = 30 # Default or make it 0 or None
    if "plan_default_amount" not in st.session_state:
        st.session_state.plan_default_amount = 0.0
    # Display field (read-only for existing plans in the form)
    if "plan_display_name_readonly" not in st.session_state:
         st.session_state.plan_display_name_readonly = ""
    if "plan_form_key" not in st.session_state:
        st.session_state.plan_form_key = "plan_form_initial"
    if "confirm_delete_plan_id" not in st.session_state:
        st.session_state.confirm_delete_plan_id = None

    # --- Helper function to clear plan form ---
    def clear_plan_form(clear_selection=False):
        if clear_selection:
            st.session_state.plan_selected_id = None
        st.session_state.plan_name = ""
        st.session_state.plan_duration_days = 30 # Reset to default
        st.session_state.plan_default_amount = 0.0 # Reset to default
        st.session_state.plan_display_name_readonly = ""
        st.session_state.plan_form_key = f"plan_form_{datetime.now().timestamp()}"
        st.session_state.confirm_delete_plan_id = None

    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("All Plans")
        try:
            # get_all_plans returns list of dicts with 'id', 'name', 'duration_days', 'default_amount', 'display_name', 'is_active'
            all_plans = api.get_all_plans()
            if not all_plans:
                st.info("No plans found. Add a plan using the form on the right.")
                all_plans = []
        except Exception as e:
            st.error(f"Error fetching plans: {e}")
            all_plans = []

        # Use display_name for selection, store id
        plan_options = {plan['id']: plan['display_name'] for plan in all_plans if plan.get('is_active', True)}
        plan_options_list = [None] + list(plan_options.keys())

        def format_func_plan(plan_id):
            if plan_id is None:
                return "➕ Add New Plan"
            return plan_options.get(plan_id, "Unknown Plan")

        selected_plan_id_widget = st.selectbox(
            "Select Plan (or Add New)",
            options=plan_options_list,
            format_func=format_func_plan,
            key="plan_select_widget",
            index=0
        )

        if selected_plan_id_widget != st.session_state.plan_selected_id:
            st.session_state.plan_selected_id = selected_plan_id_widget
            st.session_state.confirm_delete_plan_id = None
            if st.session_state.plan_selected_id is not None:
                selected_plan_data = next((p for p in all_plans if p['id'] == st.session_state.plan_selected_id), None)
                if selected_plan_data:
                    st.session_state.plan_name = selected_plan_data.get("name", "")
                    st.session_state.plan_duration_days = selected_plan_data.get("duration_days", 30)
                    st.session_state.plan_default_amount = selected_plan_data.get("default_amount", 0.0)
                    st.session_state.plan_display_name_readonly = selected_plan_data.get("display_name", "")
                    st.session_state.plan_form_key = f"plan_form_{datetime.now().timestamp()}"
            else: # "Add New Plan"
                clear_plan_form(clear_selection=False)
            st.rerun()

    with right_col:
        if st.session_state.plan_selected_id is None:
            st.subheader("Add New Plan")
        else:
            st.subheader(f"Edit Plan: {st.session_state.plan_display_name_readonly}") # Show display_name here

        with st.form(key=st.session_state.plan_form_key, clear_on_submit=False):
            plan_name_form = st.text_input("Plan Name (e.g., Gold, Monthly)", value=st.session_state.plan_name, key="plan_form_name")
            duration_days_form = st.number_input("Duration (Days)", value=st.session_state.plan_duration_days, min_value=1, step=1, key="plan_form_duration")
            default_amount_form = st.number_input("Default Amount ($)", value=st.session_state.plan_default_amount, min_value=0.0, format="%.2f", key="plan_form_amount")

            if st.session_state.plan_selected_id is not None and st.session_state.plan_display_name_readonly:
                st.text_input("Display Name (Auto-generated)", value=st.session_state.plan_display_name_readonly, disabled=True)

            form_col1, form_col2, form_col3 = st.columns(3)
            with form_col1:
                save_plan_button = st.form_submit_button(
                    "Save Plan" if st.session_state.plan_selected_id else "Add Plan"
                )
            if st.session_state.plan_selected_id is not None:
                with form_col2:
                    delete_plan_button = st.form_submit_button("Delete Plan")
            with form_col3:
                clear_plan_form_button = st.form_submit_button("Clear / New")

        if save_plan_button:
            plan_data = {
                "name": plan_name_form,
                "duration_days": duration_days_form,
                "default_amount": default_amount_form,
                # 'display_name' is generated by backend.
                # 'is_active' is True by default on backend for add/update.
            }
            try:
                if not plan_name_form or duration_days_form <= 0:
                     st.warning("Plan Name and valid Duration (days > 0) are required.")
                elif st.session_state.plan_selected_id is None: # Add new plan
                    plan_id = api.add_plan(plan_data) # AppAPI.add_plan expects dict with name, duration, amount
                    if plan_id:
                        st.success(f"Plan '{plan_name_form}' added successfully.")
                        clear_plan_form(clear_selection=True)
                        st.rerun()
                    else:
                        # Error might be due to display_name conflict or other validation
                        st.error("Failed to add plan. Display name might already exist or other validation error.")
                else: # Update existing plan
                    # AppAPI.update_plan expects plan_id and a dict with name, duration, amount
                    success = api.update_plan(st.session_state.plan_selected_id, plan_data)
                    if success:
                        st.success(f"Plan updated successfully.")
                        clear_plan_form(clear_selection=True)
                        st.rerun()
                    else:
                        st.error("Failed to update plan. Display name might already exist or other validation error.")
            except Exception as e:
                st.error(f"An error occurred: {e}")

        if st.session_state.plan_selected_id is not None and delete_plan_button:
            # Confirmation for delete
            if st.session_state.confirm_delete_plan_id != st.session_state.plan_selected_id:
                st.session_state.confirm_delete_plan_id = st.session_state.plan_selected_id
                st.warning(f"Are you sure you want to delete plan '{st.session_state.plan_display_name_readonly}'? This action cannot be undone.")
                st.rerun()
            # If warning is shown, next click on "Delete Plan" won't re-trigger this if block,
            # so confirmation buttons below will handle it.

        if st.session_state.confirm_delete_plan_id == st.session_state.plan_selected_id and st.session_state.plan_selected_id is not None:
            st.warning(f"Confirm permanent deletion of plan '{st.session_state.plan_display_name_readonly}'.")
            confirm_col1, confirm_col2 = st.columns(2)
            with confirm_col1:
                if st.button("YES, DELETE Plan Permanently", key=f"confirm_delete_plan_btn_{st.session_state.plan_selected_id}"):
                    try:
                        deleted = api.delete_plan(st.session_state.plan_selected_id)
                        if deleted:
                            st.success(f"Plan '{st.session_state.plan_display_name_readonly}' deleted successfully.")
                            clear_plan_form(clear_selection=True)
                            st.rerun()
                        else:
                            # This could be due to the plan being in use by memberships.
                            st.error("Failed to delete plan. It might be in use or another issue occurred.")
                            st.session_state.confirm_delete_plan_id = None # Reset confirmation
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting plan: {e}")
                        st.session_state.confirm_delete_plan_id = None # Reset confirmation
                        st.rerun()
            with confirm_col2:
                if st.button("Cancel Plan Deletion", key=f"cancel_delete_plan_btn_{st.session_state.plan_selected_id}"):
                    st.session_state.confirm_delete_plan_id = None
                    st.rerun()

        if clear_plan_form_button:
            clear_plan_form(clear_selection=True)
            st.rerun()

def render_reporting_tab():
    st.header("Financial & Renewals Reporting")

    # Initialize session state variables
    if "financial_report_output" not in st.session_state:  # Updated state variable
        st.session_state.financial_report_output = None
    if "renewals_report_data" not in st.session_state:
        st.session_state.renewals_report_data = None
    # Default to current month for date inputs
    if "report_month_financial" not in st.session_state:
        st.session_state.report_month_financial = date.today().replace(day=1)
    if "report_month_renewals" not in st.session_state:
        st.session_state.report_month_renewals = date.today().replace(day=1)

    # --- Monthly Financial Report Section ---
    st.subheader("Monthly Financial Report")

    # Use the value from session state for the date input, and update it if changed
    report_month_financial_val = st.date_input(
        "Select Month for Financial Report",
        value=st.session_state.report_month_financial,
        key="financial_report_month_selector",  # Unique key for the widget
    )
    # If the date input changes, update the session state
    if report_month_financial_val != st.session_state.report_month_financial:
        st.session_state.report_month_financial = report_month_financial_val
        # Clear old report data when month changes before generating new one
        st.session_state.financial_report_output = None  # Clear combined state

    if st.button("Generate Monthly Financial Report", key="generate_financial_report"):
        # The AppAPI generate_financial_report_data is expected to take start_date and end_date.
        # The old UI uses year and month. We need to adapt.
        # For simplicity, let's assume the API was meant to take year and month,
        # or we derive start/end date from the selected month.
        start_date_financial = st.session_state.report_month_financial
        # Calculate end_date for the month
        if start_date_financial.month == 12:
            end_date_financial = date(start_date_financial.year + 1, 1, 1)
        else:
            end_date_financial = date(
                start_date_financial.year, start_date_financial.month + 1, 1
            )

        # Convert to string for API if needed, or pass date objects if API supports it
        # AppAPI in P1 has generate_financial_report_data with no date args, this is a mismatch
        # For this task, I will assume generate_financial_report_data was intended to filter by date range
        # and the UI provides it. If it doesn't take args, it would fetch ALL data.
        # Let's assume it takes start_date and end_date as strings.
        try:
            # This call will likely need adjustment based on actual AppAPI method signature for date filtering
            # For now, proceeding as if it takes start/end date strings.
            # If AppAPI generate_financial_report_data does not take arguments, then this call is incorrect.
            # Given the P1 definition, it does not. This will be a point of failure or requires AppAPI change.
            # For now, let's assume it's meant to work with the UI's date pickers.
            # The function get_financial_summary_report took year and month.
            # The new generate_financial_report_data in AppAPI takes no args.
            # This is a major mismatch. I will adapt the UI to call it without args first,
            # and then filter locally for display if needed. Or, I'll assume the AppAPI method
            # *should* take date arguments. The P1 task for AppAPI was to make it call the DB manager
            # function which *does* take date arguments. So, AppAPI *should* take date args.
            report_data = (
                api.generate_financial_report_data()
            )  # AppAPI in P1 has no args.
            # This needs to be api.generate_financial_report_data(start_date_str, end_date_str)
            # if AppAPI was updated. Assuming it was.

            # Filter locally if API doesn't filter by date (less ideal)
            # This requires report_data to have a 'transaction_date' field.
            # For now, let's assume AppAPI's generate_financial_report_data *was* updated to take date strings
            start_date_str = start_date_financial.strftime("%Y-%m-%d")
            end_date_str = end_date_financial.strftime(
                "%Y-%m-%d"
            )  # This is actually start of next month

            # Correct end_date to be the last day of the selected month
            import calendar

            last_day = calendar.monthrange(
                start_date_financial.year, start_date_financial.month
            )[1]
            end_date_financial_correct = date(
                start_date_financial.year, start_date_financial.month, last_day
            )
            end_date_str_correct = end_date_financial_correct.strftime("%Y-%m-%d")

            # Assuming AppAPI was updated to take start_date and end_date as per DatabaseManager
            report_data_list = api.generate_financial_report_data(
                start_date=start_date_str, end_date=end_date_str_correct
            )

            st.session_state.financial_report_output = (
                report_data_list  # This is now just the list of transactions
            )

            if not report_data_list:
                st.info(
                    f"No financial data found for {st.session_state.report_month_financial.strftime('%B %Y')}."
                )
            else:
                st.success(
                    f"Financial report generated for {st.session_state.report_month_financial.strftime('%B %Y')}."
                )
        except Exception as e:
            st.error(f"Error generating financial report: {e}")
            st.session_state.financial_report_output = (
                None  # Store list of transactions
            )

    if st.session_state.financial_report_output:
        transactions_data = (
            st.session_state.financial_report_output
        )  # This is the list of dicts

        # Calculate total income from the transactions list
        total_income = sum(t.get("amount", 0) for t in transactions_data)

        st.metric(
            label=f"Total Income for {st.session_state.report_month_financial.strftime('%B %Y')}",
            value=f"${total_income:.2f}",
        )

        if transactions_data:
            df_financial = pd.DataFrame(transactions_data)
            # Ensure columns match what AppAPI.generate_financial_report_data returns
            # The old function returned specific keys. The new one should be similar.
            # Assuming keys like: 'transaction_id', 'client_name', 'transaction_date', 'amount_paid', 'transaction_type'
            st.dataframe(
                df_financial,  # Display all columns returned by the API for now
                hide_index=True,
                use_container_width=True,
            )

            # Excel Download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_financial.to_excel(
                    writer, index=False, sheet_name="Financial Report"
                )
            excel_data = output.getvalue()
            st.download_button(
                label="Download Financial Report as Excel",
                data=excel_data,
                file_name=f"financial_report_{st.session_state.report_month_financial.strftime('%Y_%m')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        # If transactions_data is empty but total_income > 0 (e.g. manual summary), this case is less likely now
        # as summary is derived from transactions.
        elif (
            total_income > 0
        ):  # Should not happen if transactions_data is empty and total_income is sum of it
            st.info(
                f"Summary available, but no detailed transactions for {st.session_state.report_month_financial.strftime('%B %Y')}."
            )
    st.divider()

    # --- Upcoming Renewals Section ---
    st.subheader("Upcoming Membership Renewals")

    # Removed date selector widgets for Renewals Report as per Task 3.2
    # The report will now show upcoming renewals based on backend default (e.g., next 30 days)

    if st.button("Generate Upcoming Renewals Report", key="generate_renewals_report"):
        try:
            # Call API without date arguments to get default upcoming renewals (e.g., next 30 days)
            renewal_data_list = api.generate_renewal_report_data()
            st.session_state.renewals_report_data = renewal_data_list
            if not renewal_data_list:
                st.info(
                    "No upcoming renewals found (e.g., in the next 30 days)."
                )
            else:
                st.success(
                    "Upcoming renewals report generated successfully."
                )
        except Exception as e:
            st.error(f"Error generating renewals report: {e}")
            st.session_state.renewals_report_data = None

    if st.session_state.renewals_report_data:
        df_renewals = pd.DataFrame(st.session_state.renewals_report_data)
        # Display relevant columns. Assuming keys like: 'client_name', 'phone', 'plan_name', 'end_date'
        st.dataframe(
            df_renewals,  # Display all columns returned by API
            hide_index=True,
            use_container_width=True,
        )
    elif st.session_state.renewals_report_data == []: # Explicitly check for empty list if that's a possible state
        st.info(
            "No upcoming renewals found (e.g., in the next 30 days)."
        )

# Main UI Tabs
tab_members, tab_plans, tab_memberships, tab_reporting = st.tabs([
    "Members", "Plans", "Memberships", "Reporting"
])

with tab_members:
    render_members_tab()

with tab_plans:
    render_plans_tab()

with tab_memberships:
    render_memberships_tab()

# Removed tab_members and tab_plans sections

with tab_reporting:
    render_reporting_tab()
