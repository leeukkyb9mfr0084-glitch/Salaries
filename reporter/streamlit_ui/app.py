import streamlit as st
import pandas as pd
from datetime import date, datetime  # Added datetime
import sqlite3
import io  # For Excel download
from reporter.app_api import AppAPI
from reporter.database import DB_FILE
# --- Database Connection & API Initialization ---
from reporter.database_manager import DatabaseManager
import sqlite3 # Added for connection for DB Manager

# Create a single connection for the app session for DatabaseManager
conn = sqlite3.connect(DB_FILE, check_same_thread=False) # check_same_thread for Streamlit
db_manager = DatabaseManager(connection=conn) # Pass the connection
api = AppAPI(db_manager=db_manager)


# --- Helper function to clear form state ---
# This function might need to be adapted or split if forms become too different
def clear_membership_form_state(): # Keep for now, might be useful for GC form
    st.session_state.create_member_id = None
    st.session_state.create_plan_id_display = None
    st.session_state.create_transaction_amount = 0.0
    st.session_state.create_start_date = date.today()
    st.session_state.selected_plan_duration_display = ""

    if "form_key_create_membership" in st.session_state: # GC specific form key
        st.session_state.form_key_create_membership = f"form_gc_{datetime.now().timestamp()}"
    if "pt_form_key" in st.session_state: # PT specific form key
        st.session_state.pt_form_key = f"form_pt_{datetime.now().timestamp()}"


# --- Tab Rendering Functions ---

# Helper function for new GROUP CLASS membership creation (adapted from old render_new_membership_form_section)
# This will be part of the 'Memberships' tab now.
def render_new_group_class_membership_form():
    st.subheader("Create New Group Class Membership")

    # Fetch active members for selectbox
    try:
        all_members = api.get_all_members()
        member_options = {member['id']: f"{member['name']} (ID: {member['id']})" for member in all_members if member.get('is_active', True)}
        if not member_options:
            st.warning("No active members available to create a membership for.")
            return
    except Exception as e:
        st.error(f"Error fetching members: {e}")
        return

    # Fetch active group plans for selectbox
    try:
        all_group_plans = api.get_all_group_plans()
        plan_options = {plan['id']: f"{plan['display_name']} ({plan['duration_days']} days, ${plan['default_amount']})"
                        for plan in all_group_plans if plan.get('is_active', True)}
        if not plan_options:
            st.warning("No active group plans available.")
            return
    except Exception as e:
        st.error(f"Error fetching group plans: {e}")
        return

    with st.form("new_gc_membership_form", clear_on_submit=True):
        selected_member_id = st.selectbox("Select Member", options=list(member_options.keys()), format_func=lambda id: member_options[id])
        selected_plan_id = st.selectbox("Select Group Plan", options=list(plan_options.keys()), format_func=lambda id: plan_options[id])
        start_date = st.date_input("Start Date", value=date.today())
        amount_paid = st.number_input("Amount Paid ($)", min_value=0.0, format="%.2f")
        # purchase_date is auto-set by DBManager/API
        # membership_type ('New'/'Renewal') is also auto-set by DBManager/API

        submitted = st.form_submit_button("Create Group Class Membership")
        if submitted:
            if not selected_member_id or not selected_plan_id:
                st.error("Member and Plan must be selected.")
            elif amount_paid <= 0:
                st.error("Amount paid must be greater than zero.")
            else:
                try:
                    record_id = api.create_group_class_membership(
                        member_id=selected_member_id,
                        plan_id=selected_plan_id,
                        start_date_str=start_date.strftime("%Y-%m-%d"),
                        amount_paid=amount_paid
                    )
                    if record_id:
                        st.success(f"Group Class Membership created with ID: {record_id}")
                        st.rerun()
                    else:
                        st.error("Failed to create Group Class Membership.")
                except Exception as e:
                    st.error(f"Error creating membership: {e}")

# Helper function for new PERSONAL TRAINING membership creation
def render_new_pt_membership_form():
    st.subheader("Create New Personal Training Membership")

    try:
        all_members = api.get_all_members()
        member_options = {member['id']: f"{member['name']} (ID: {member['id']})" for member in all_members if member.get('is_active', True)}
        if not member_options:
            st.warning("No active members available to create a PT membership for.")
            return
    except Exception as e:
        st.error(f"Error fetching members: {e}")
        return

    with st.form("new_pt_membership_form", clear_on_submit=True):
        selected_member_id = st.selectbox("Select Member", options=list(member_options.keys()), format_func=lambda id: member_options[id])
        purchase_date = st.date_input("Purchase Date", value=date.today())
        amount_paid = st.number_input("Amount Paid ($)", min_value=0.0, format="%.2f")
        sessions_purchased = st.number_input("Sessions Purchased", min_value=1, step=1)
        notes = st.text_area("Notes (Optional)")

        submitted = st.form_submit_button("Create Personal Training Membership")
        if submitted:
            if not selected_member_id or sessions_purchased <= 0:
                st.error("Member must be selected and sessions purchased must be greater than zero.")
            elif amount_paid <= 0:
                 st.error("Amount paid must be greater than zero.")
            else:
                try:
                    record_id = api.create_pt_membership(
                        member_id=selected_member_id,
                        purchase_date=purchase_date.strftime("%Y-%m-%d"),
                        amount_paid=amount_paid,
                        sessions_purchased=sessions_purchased,
                        notes=notes
                    )
                    if record_id:
                        st.success(f"Personal Training Membership created with ID: {record_id}")
                        st.rerun()
                    else:
                        st.error("Failed to create Personal Training Membership.")
                except Exception as e:
                    st.error(f"Error creating PT membership: {e}")


def render_memberships_tab():
    st.header("Manage Memberships")

    membership_mode = st.radio(
        "Select Membership Type",
        ('Group Class Memberships', 'Personal Training Memberships'),
        key="membership_mode_selector"
    )

    if membership_mode == 'Group Class Memberships':
        render_new_group_class_membership_form()
        st.subheader("Existing Group Class Memberships")
        try:
            gc_memberships = api.get_all_group_class_memberships_for_view() # This API takes optional filters
            if gc_memberships:
                df_gc = pd.DataFrame(gc_memberships)
                # Select and order columns for display
                cols_gc = ['membership_id', 'member_name', 'plan_name', 'start_date', 'end_date', 'amount_paid', 'purchase_date', 'membership_type', 'is_active']
                df_gc_display = df_gc[cols_gc]
                df_gc_display['is_active'] = df_gc_display['is_active'].apply(lambda x: 'Active' if x else 'Inactive')
                st.dataframe(df_gc_display, hide_index=True, use_container_width=True)

                # Simple Delete for GC Memberships (can be enhanced with selection like other tabs)
                if 'delete_gc_membership_id' not in st.session_state:
                    st.session_state.delete_gc_membership_id = ""

                gc_ids = [str(m['membership_id']) for m in gc_memberships]
                gc_id_to_delete = st.selectbox("Select Group Class Membership ID to Delete", options=[""] + gc_ids, key="delete_gc_membership_id_select")

                if st.button("Delete Selected Group Class Membership", key="delete_gc_button"):
                    if gc_id_to_delete:
                        try:
                            success = api.delete_group_class_membership_record(int(gc_id_to_delete))
                            if success:
                                st.success(f"Group Class Membership ID {gc_id_to_delete} deleted.")
                                st.rerun()
                            else:
                                st.error(f"Failed to delete Group Class Membership ID {gc_id_to_delete}.")
                        except Exception as e:
                            st.error(f"Error deleting: {e}")
                    else:
                        st.warning("Please select a Group Class Membership ID to delete.")
            else:
                st.info("No Group Class Memberships found.")
        except Exception as e:
            st.error(f"Error fetching Group Class Memberships: {e}")

    elif membership_mode == 'Personal Training Memberships':
        render_new_pt_membership_form()
        st.subheader("Existing Personal Training Memberships")
        try:
            pt_memberships = api.get_all_pt_memberships()
            if pt_memberships:
                df_pt = pd.DataFrame(pt_memberships)
                # Select and order columns for display
                cols_pt = ['id', 'member_name', 'purchase_date', 'amount_paid', 'sessions_purchased', 'sessions_remaining', 'notes']
                df_pt_display = df_pt[cols_pt]
                st.dataframe(df_pt_display, hide_index=True, use_container_width=True)

                # Simple Delete for PT Memberships
                if 'delete_pt_membership_id' not in st.session_state:
                    st.session_state.delete_pt_membership_id = ""

                pt_ids = [str(m['id']) for m in pt_memberships]
                pt_id_to_delete = st.selectbox("Select PT Membership ID to Delete", options=[""] + pt_ids, key="delete_pt_membership_id_select")

                if st.button("Delete Selected PT Membership", key="delete_pt_button"):
                    if pt_id_to_delete:
                        try:
                            success = api.delete_pt_membership(int(pt_id_to_delete))
                            if success:
                                st.success(f"PT Membership ID {pt_id_to_delete} deleted.")
                                st.rerun()
                            else:
                                st.error(f"Failed to delete PT Membership ID {pt_id_to_delete}.")
                        except Exception as e:
                             st.error(f"Error deleting: {e}")
                    else:
                        st.warning("Please select a PT Membership ID to delete.")
            else:
                st.info("No Personal Training Memberships found.")
        except Exception as e:
            st.error(f"Error fetching Personal Training Memberships: {e}")

    # Note: The old detailed edit form from render_memberships_tab for group class memberships
    # has been removed for simplicity in this overhaul. It was also incompatible with new API.
    # A new edit mechanism would need to be designed for both GC and PT if required.
    # The "Create Membership for Member X" button on Members tab is currently non-functional
    # as render_new_membership_form_section was removed. This functionality is now part of this tab.


# --- Members Tab ---
def render_members_tab():
    st.header("Manage Members")
    if "member_selected_id" not in st.session_state:
        st.session_state.member_selected_id = None
    if "member_name" not in st.session_state:
        st.session_state.member_name = ""
    if "member_email" not in st.session_state:
        st.session_state.member_email = ""
    if "member_phone" not in st.session_state:
        st.session_state.member_phone = ""
    if "member_is_active" not in st.session_state:
        st.session_state.member_is_active = True
    if "member_form_key" not in st.session_state:
        st.session_state.member_form_key = "member_form_initial"
    if "confirm_delete_member_id" not in st.session_state:
        st.session_state.confirm_delete_member_id = None
    # Removed trigger_membership_creation states, as that form is now part of Memberships tab.

    def clear_member_form(clear_selection=False):
        if clear_selection:
            st.session_state.member_selected_id = None
        st.session_state.member_name = ""
        st.session_state.member_email = ""
        st.session_state.member_phone = ""
        st.session_state.member_is_active = True
        st.session_state.member_form_key = f"member_form_{datetime.now().timestamp()}"
        st.session_state.confirm_delete_member_id = None

    left_col, right_col = st.columns([1, 2])
    with left_col:
        st.subheader("All Members")
        try:
            all_members = api.get_all_members()
            if not all_members:
                st.info("No members found. Add a member using the form on the right.")
                all_members = []
        except Exception as e:
            st.error(f"Error fetching members: {e}")
            all_members = []

        member_options = {member['id']: f"{member['name']} ({member['phone']})" for member in all_members}
        member_options_list = [None] + list(member_options.keys())

        def format_func_member(member_id):
            if member_id is None:
                return "➕ Add New Member"
            return member_options.get(member_id, "Unknown Member")

        selected_id_display = st.selectbox(
            "Select Member (or Add New)",
            options=member_options_list,
            format_func=format_func_member,
            key="member_select_widget",
            index=0
        )
        if st.session_state.member_select_widget != st.session_state.member_selected_id:
            st.session_state.member_selected_id = st.session_state.member_select_widget
            st.session_state.confirm_delete_member_id = None
            if st.session_state.member_selected_id is not None:
                selected_member_data = next((m for m in all_members if m['id'] == st.session_state.member_selected_id), None)
                if selected_member_data:
                    st.session_state.member_name = selected_member_data.get("name", "")
                    st.session_state.member_email = selected_member_data.get("email", "")
                    st.session_state.member_phone = selected_member_data.get("phone", "")
                    st.session_state.member_is_active = bool(selected_member_data.get("is_active", 1))
                    st.session_state.member_form_key = f"member_form_{datetime.now().timestamp()}"
            else:
                clear_member_form(clear_selection=False)
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
            is_active_form = st.checkbox("Is Active", value=st.session_state.member_is_active, key="member_form_is_active")
            form_col1, form_col2, form_col3 = st.columns(3)
            with form_col1:
                save_button = st.form_submit_button("Save Member" if st.session_state.member_selected_id else "Add Member")
            if st.session_state.member_selected_id is not None:
                with form_col2:
                    delete_button = st.form_submit_button("Delete Member")
            with form_col3:
                clear_button = st.form_submit_button("Clear / New")

        if save_button:
            try:
                if st.session_state.member_selected_id is None:
                    if not name or not phone:
                        st.warning("Name and Phone are required.")
                    else:
                        try:
                            member_id = api.add_member(name=name, phone=phone, email=email)
                            if member_id: # Assuming add_member returns member_id on success, None or raises error on fail
                                st.success(f"Member '{name}' added successfully with ID: {member_id}")
                                clear_member_form(clear_selection=True) # Rerun handled by clear_member_form or needs st.rerun()
                                st.rerun()
                            else:
                                # This else might not be reached if add_member raises ValueError for duplicates
                                st.error("Failed to add member. Please check details.")
                        except ValueError as e:
                            st.error(f"Error: {e}")
                        # Removed the generic Exception catch to let Streamlit handle unexpected errors,
                        # or it can be added back if specific logging/handling is needed.
                else: # This is the update block
                    try:
                        success = api.update_member(
                            member_id=st.session_state.member_selected_id,
                            name=name,
                            phone=phone,
                            email=email,
                            is_active=is_active_form
                        )
                        if success:
                            st.success(f"Member '{name}' updated successfully.")
                            clear_member_form(clear_selection=True) # Rerun handled by clear_member_form or needs st.rerun()
                            # st.session_state.edit_member_id = None # This was in snippet, but seems not used here
                            st.rerun()
                        else:
                            # This else might not be reached if update_member raises ValueError for duplicates
                            st.error("Failed to update member. Please check details.")
                    except ValueError as e:
                        st.error(f"Error: {e}")
                    # Removed the generic Exception catch here as well for similar reasons.
            # The existing ValueError catch below this block seems to be from a previous structure.
            # It might be redundant now or might need to be integrated if it serves a different purpose.
            # For now, I'm commenting it out as the try-except blocks are added directly around API calls.
            # except ValueError as ve:
            #      st.error(f"Validation error: {ve}")
            except Exception as e: # This can be kept as a fallback for other unexpected errors
                st.error(f"An error occurred: {e}")

        if st.session_state.member_selected_id is not None and delete_button:
            if st.session_state.confirm_delete_member_id != st.session_state.member_selected_id:
                st.session_state.confirm_delete_member_id = st.session_state.member_selected_id
                st.warning(f"Are you sure you want to delete member '{st.session_state.member_name}'? This action cannot be undone.")
                st.rerun()
            else:
                pass

        if st.session_state.confirm_delete_member_id == st.session_state.member_selected_id and st.session_state.member_selected_id is not None:
            st.warning(f"Confirm permanent deletion of member '{st.session_state.member_name}'.")
            confirm_col1, confirm_col2 = st.columns(2)
            with confirm_col1:
                if st.button("YES, DELETE Permanently", key=f"confirm_delete_btn_{st.session_state.member_selected_id}"):
                    try:
                        deleted = api.delete_member(st.session_state.member_selected_id)
                        if deleted:
                            st.success(f"Member '{st.session_state.member_name}' deleted successfully.")
                            clear_member_form(clear_selection=True)
                            st.session_state.confirm_delete_member_id = None
                            st.rerun()
                        else:
                            st.error("Failed to delete member. They might have active memberships or other issue.")
                            st.session_state.confirm_delete_member_id = None
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting member: {e}")
                        st.session_state.confirm_delete_member_id = None
                        st.rerun()
            with confirm_col2:
                if st.button("Cancel Deletion", key=f"cancel_delete_btn_{st.session_state.member_selected_id}"):
                    st.session_state.confirm_delete_member_id = None
                    st.rerun()

        if clear_button:
            clear_member_form(clear_selection=True)
            st.rerun()

        # Removed "Create Membership for this member" button as this functionality is now in Memberships tab.

# --- Group Plans Tab ---
def render_group_plans_tab():
    st.header("Manage Group Plans")

    if "group_plan_selected_id" not in st.session_state:
        st.session_state.group_plan_selected_id = None
    if "group_plan_name" not in st.session_state:
        st.session_state.group_plan_name = ""
    if "group_plan_duration_days" not in st.session_state:
        st.session_state.group_plan_duration_days = 30
    if "group_plan_default_amount" not in st.session_state:
        st.session_state.group_plan_default_amount = 0.0
    if "group_plan_is_active" not in st.session_state:
        st.session_state.group_plan_is_active = True
    if "group_plan_display_name_readonly" not in st.session_state:
         st.session_state.group_plan_display_name_readonly = ""
    if "group_plan_form_key" not in st.session_state:
        st.session_state.group_plan_form_key = "group_plan_form_initial"
    if "confirm_delete_group_plan_id" not in st.session_state:
        st.session_state.confirm_delete_group_plan_id = None

    def clear_group_plan_form(clear_selection=False):
        if clear_selection:
            st.session_state.group_plan_selected_id = None
        st.session_state.group_plan_name = ""
        st.session_state.group_plan_duration_days = 30
        st.session_state.group_plan_default_amount = 0.0
        st.session_state.group_plan_is_active = True
        st.session_state.group_plan_display_name_readonly = ""
        st.session_state.group_plan_form_key = f"group_plan_form_{datetime.now().timestamp()}"
        st.session_state.confirm_delete_group_plan_id = None

    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("All Group Plans")
        try:
            all_group_plans = api.get_all_group_plans()
            if not all_group_plans:
                st.info("No group plans found. Add a plan using the form on the right.")
                all_group_plans = []
        except Exception as e:
            st.error(f"Error fetching group plans: {e}")
            all_group_plans = []

        plan_options = {plan['id']: plan['display_name'] for plan in all_group_plans}
        plan_options_list = [None] + list(plan_options.keys())

        def format_func_group_plan(plan_id):
            if plan_id is None:
                return "➕ Add New Group Plan"  # Restoring the emoji
            # This part makes the function robust against missing names in the database
            display_name = plan_options.get(plan_id)
            if not display_name:
                return f"Unnamed Plan (ID: {plan_id})"
            return display_name

        selected_group_plan_id_widget = st.selectbox(
            "Select Group Plan (or Add New)",
            options=plan_options_list,
            format_func=format_func_group_plan,
            key="group_plan_select_widget",
            index=0
        )

        if selected_group_plan_id_widget != st.session_state.group_plan_selected_id:
            st.session_state.group_plan_selected_id = selected_group_plan_id_widget
            st.session_state.confirm_delete_group_plan_id = None
            if st.session_state.group_plan_selected_id is not None:
                selected_plan_data = next((p for p in all_group_plans if p['id'] == st.session_state.group_plan_selected_id), None)
                if selected_plan_data:
                    st.session_state.group_plan_name = selected_plan_data.get("name", "")
                    st.session_state.group_plan_duration_days = selected_plan_data.get("duration_days", 30)
                    st.session_state.group_plan_default_amount = selected_plan_data.get("default_amount", 0.0)
                    st.session_state.group_plan_is_active = bool(selected_plan_data.get("is_active", 1))
                    st.session_state.group_plan_display_name_readonly = selected_plan_data.get("display_name", "")
                    st.session_state.group_plan_form_key = f"group_plan_form_{datetime.now().timestamp()}"
            else:
                clear_group_plan_form(clear_selection=False)
            st.rerun()

    with right_col:
        if st.session_state.group_plan_selected_id is None:
            st.subheader("Add New Group Plan")
        else:
            st.subheader(f"Edit Group Plan: {st.session_state.group_plan_display_name_readonly}")

        with st.form(key=st.session_state.group_plan_form_key, clear_on_submit=False):
            plan_name_form = st.text_input("Group Plan Name (e.g., Gold, Monthly)", value=st.session_state.group_plan_name, key="group_plan_form_name")
            duration_days_form = st.number_input("Duration (Days)", value=st.session_state.group_plan_duration_days, min_value=1, step=1, key="group_plan_form_duration")
            default_amount_form = st.number_input("Default Amount ($)", value=st.session_state.group_plan_default_amount, min_value=0.0, format="%.2f", key="group_plan_form_amount")
            is_active_form = st.checkbox("Is Active", value=st.session_state.group_plan_is_active, key="group_plan_form_is_active")

            if st.session_state.group_plan_selected_id is not None and st.session_state.group_plan_display_name_readonly:
                st.text_input("Display Name (Auto-generated)", value=st.session_state.group_plan_display_name_readonly, disabled=True)

            form_col1, form_col2, form_col3 = st.columns(3)
            with form_col1:
                save_plan_button = st.form_submit_button(
                    "Save Group Plan" if st.session_state.group_plan_selected_id else "Add Group Plan"
                )
            if st.session_state.group_plan_selected_id is not None:
                with form_col2:
                    delete_plan_button = st.form_submit_button("Delete Group Plan")
            with form_col3:
                clear_plan_form_button = st.form_submit_button("Clear / New")

        if save_plan_button:
            try:
                if not plan_name_form or duration_days_form <= 0:
                     st.warning("Group Plan Name and valid Duration (days > 0) are required.")
                elif st.session_state.group_plan_selected_id is None:
                    plan_id = api.add_group_plan(
                        name=plan_name_form,
                        duration_days=duration_days_form,
                        default_amount=default_amount_form
                    )
                    if plan_id:
                        st.success(f"Group Plan '{plan_name_form}' added successfully.")
                        clear_group_plan_form(clear_selection=True)
                        st.rerun()
                    else:
                        st.error("Failed to add group plan. Display name might already exist or other validation error.")
                else:
                    success = api.update_group_plan(
                        plan_id=st.session_state.group_plan_selected_id,
                        name=plan_name_form,
                        duration_days=duration_days_form,
                        default_amount=default_amount_form,
                        is_active=is_active_form
                    )
                    if success:
                        st.success(f"Group Plan updated successfully.")
                        clear_group_plan_form(clear_selection=True)
                        st.rerun()
                    else:
                        st.error("Failed to update group plan. Display name might already exist or other validation error.")
            except ValueError as ve:
                 st.error(f"Validation error: {ve}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

        if st.session_state.group_plan_selected_id is not None and delete_plan_button:
            if st.session_state.confirm_delete_group_plan_id != st.session_state.group_plan_selected_id:
                st.session_state.confirm_delete_group_plan_id = st.session_state.group_plan_selected_id
                st.warning(f"Are you sure you want to delete group plan '{st.session_state.group_plan_display_name_readonly}'? This action cannot be undone.")
                st.rerun()

        if st.session_state.confirm_delete_group_plan_id == st.session_state.group_plan_selected_id and st.session_state.group_plan_selected_id is not None:
            st.warning(f"Confirm permanent deletion of group plan '{st.session_state.group_plan_display_name_readonly}'.")
            confirm_col1, confirm_col2 = st.columns(2)
            with confirm_col1:
                if st.button("YES, DELETE Group Plan Permanently", key=f"confirm_delete_gplan_btn_{st.session_state.group_plan_selected_id}"):
                    try:
                        deleted = api.delete_group_plan(st.session_state.group_plan_selected_id)
                        if deleted:
                            st.success(f"Group Plan '{st.session_state.group_plan_display_name_readonly}' deleted successfully.")
                            clear_group_plan_form(clear_selection=True)
                            st.rerun()
                        else:
                            st.error("Failed to delete group plan. It might be in use or another issue occurred.")
                            st.session_state.confirm_delete_group_plan_id = None
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting group plan: {e}")
                        st.session_state.confirm_delete_group_plan_id = None
                        st.rerun()
            with confirm_col2:
                if st.button("Cancel Group Plan Deletion", key=f"cancel_delete_gplan_btn_{st.session_state.group_plan_selected_id}"):
                    st.session_state.confirm_delete_group_plan_id = None
                    st.rerun()

        if clear_plan_form_button:
            clear_group_plan_form(clear_selection=True)
            st.rerun()

def render_reporting_tab():
    st.header("Financial & Renewals Reporting")

    if "financial_report_output" not in st.session_state:
        st.session_state.financial_report_output = None
    if "renewals_report_data" not in st.session_state:
        st.session_state.renewals_report_data = None
    if "report_month_financial" not in st.session_state:
        st.session_state.report_month_financial = date.today().replace(day=1)

    st.subheader("Monthly Financial Report")
    report_month_financial_val = st.date_input(
        "Select Month for Financial Report",
        value=st.session_state.report_month_financial,
        key="financial_report_month_selector",
    )
    if report_month_financial_val != st.session_state.report_month_financial:
        st.session_state.report_month_financial = report_month_financial_val
        st.session_state.financial_report_output = None

    if st.button("Generate Monthly Financial Report", key="generate_financial_report"):
        start_date_financial = st.session_state.report_month_financial
        import calendar
        last_day = calendar.monthrange(start_date_financial.year, start_date_financial.month)[1]
        end_date_financial_correct = date(start_date_financial.year, start_date_financial.month, last_day)
        start_date_str = start_date_financial.strftime("%Y-%m-%d")
        end_date_str_correct = end_date_financial_correct.strftime("%Y-%m-%d")
        try:
            report_output = api.generate_financial_report(
                start_date=start_date_str, end_date=end_date_str_correct
            )
            st.session_state.financial_report_output = report_output

            if not report_output or not report_output.get("details"):
                st.info(f"No financial data found for {st.session_state.report_month_financial.strftime('%B %Y')}.")
            else:
                st.success(f"Financial report generated for {st.session_state.report_month_financial.strftime('%B %Y')}.")
        except Exception as e:
            st.error(f"Error generating financial report: {e}")
            st.session_state.financial_report_output = None

    if st.session_state.financial_report_output:
        summary_data = st.session_state.financial_report_output.get("summary", {})
        details_data = st.session_state.financial_report_output.get("details", [])
        total_income = summary_data.get("total_revenue", 0.0)

        st.metric(
            label=f"Total Income for {st.session_state.report_month_financial.strftime('%B %Y')}",
            value=f"${total_income:.2f}",
        )

        if details_data:
            df_financial = pd.DataFrame(details_data)
            st.dataframe(
                df_financial,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "purchase_date": st.column_config.DateColumn("Purchase Date", format="YYYY-MM-DD"),
                    "amount_paid": st.column_config.NumberColumn("Amount Paid ($)", format="%.2f"),
                    "type": "Type",
                    "member_name": "Member Name",
                    "item_name": "Item/Plan Name"
                }
            )
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_financial.to_excel(writer, index=False, sheet_name="Financial Report")
            excel_data = output.getvalue()
            st.download_button(
                label="Download Financial Report as Excel",
                data=excel_data,
                file_name=f"financial_report_{st.session_state.report_month_financial.strftime('%Y_%m')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        elif total_income > 0:
            st.info(f"Summary available, but no detailed transactions for {st.session_state.report_month_financial.strftime('%B %Y')}.")
    st.divider()

    st.subheader("Upcoming Membership Renewals")
    if st.button("Generate Upcoming Renewals Report", key="generate_renewals_report"):
        try:
            renewal_data_list = api.generate_renewal_report()
            st.session_state.renewals_report_data = renewal_data_list
            if not renewal_data_list:
                st.info("No upcoming group class renewals found (e.g., in the next 30 days).")
            else:
                st.success("Upcoming group class renewals report generated successfully.")
        except Exception as e:
            st.error(f"Error generating renewals report: {e}")
            st.session_state.renewals_report_data = None

    if st.session_state.renewals_report_data:
        df_renewals = pd.DataFrame(st.session_state.renewals_report_data)
        st.dataframe(
            df_renewals,
            hide_index=True,
            use_container_width=True,
            column_config={
                "member_name": "Member Name",
                "member_phone": "Phone",
                "plan_name": "Plan Name",
                "start_date": st.column_config.DateColumn("Start Date", format="YYYY-MM-DD"),
                "end_date": st.column_config.DateColumn("End Date", format="YYYY-MM-DD"),
                "amount_paid": st.column_config.NumberColumn("Amount Paid ($)", format="%.2f"),
                "membership_type": "Type"
            }
        )
    elif st.session_state.renewals_report_data == []:
        st.info("No upcoming group class renewals found (e.g., in the next 30 days).")

# Main UI Tabs
tab_titles = ["Members", "Group Plans", "Memberships", "Reporting"]
tab_members, tab_group_plans, tab_memberships, tab_reporting = st.tabs(tab_titles)

with tab_members:
    render_members_tab()

with tab_group_plans:
    render_group_plans_tab()

with tab_memberships:
    render_memberships_tab() # This will be overhauled next

with tab_reporting:
    render_reporting_tab()

# Removed render_new_membership_form_section as it's integrated or replaced.
# The old render_memberships_tab is replaced by the new one.
# The old render_plans_tab is replaced by render_group_plans_tab.
