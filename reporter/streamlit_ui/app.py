import streamlit as st
st.set_page_config(layout="wide")
import pandas as pd
from datetime import date, datetime  # Added datetime
import sqlite3
import io  # For Excel download
from reporter.app_api import AppAPI
from reporter.database import DB_FILE
from reporter.database_manager import DatabaseManager
import sqlite3
from reporter.models import MemberView, GroupPlanView, GroupClassMembershipView, PTMembershipView # DTOs

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
db_manager = DatabaseManager(connection=conn)
api = AppAPI(db_manager=db_manager)

# Initialize session state keys to prevent KeyErrors and ensure defined starting states
default_today = date.today()

# Keys from render_memberships_tab (Group Class)
if 'selected_gc_membership_id' not in st.session_state:
    st.session_state.selected_gc_membership_id = "add_new"
if 'gc_member_id_form' not in st.session_state:
    st.session_state.gc_member_id_form = None
if 'gc_member_name_display' not in st.session_state:
    st.session_state.gc_member_name_display = ""
if 'gc_plan_id_form' not in st.session_state:
    st.session_state.gc_plan_id_form = None
if 'gc_start_date_form' not in st.session_state:
    st.session_state.gc_start_date_form = default_today
if 'gc_amount_paid_form' not in st.session_state:
    st.session_state.gc_amount_paid_form = 0.0
if 'gc_membership_form_key' not in st.session_state:
    st.session_state.gc_membership_form_key = "gc_membership_form_initial"
if 'confirm_delete_gc_membership_id' not in st.session_state:
    st.session_state.confirm_delete_gc_membership_id = None

# Keys from render_memberships_tab (Personal Training)
if 'selected_pt_membership_id' not in st.session_state:
    st.session_state.selected_pt_membership_id = "add_new"
if 'pt_member_id_form' not in st.session_state:
    st.session_state.pt_member_id_form = None
if 'pt_member_name_display' not in st.session_state:
    st.session_state.pt_member_name_display = ""
if 'pt_purchase_date_form' not in st.session_state:
    st.session_state.pt_purchase_date_form = default_today
if 'pt_amount_paid_form' not in st.session_state:
    st.session_state.pt_amount_paid_form = 0.0
if 'pt_sessions_purchased_form' not in st.session_state:
    st.session_state.pt_sessions_purchased_form = 1
if 'pt_membership_form_key' not in st.session_state:
    st.session_state.pt_membership_form_key = "pt_membership_form_initial"
if 'confirm_delete_pt_membership_id' not in st.session_state:
    st.session_state.confirm_delete_pt_membership_id = None

# Keys from render_members_tab
if 'member_selected_id' not in st.session_state:
    st.session_state.member_selected_id = None
if 'member_name' not in st.session_state:
    st.session_state.member_name = ""
if 'member_email' not in st.session_state:
    st.session_state.member_email = ""
if 'member_phone' not in st.session_state:
    st.session_state.member_phone = ""
if 'member_is_active' not in st.session_state:
    st.session_state.member_is_active = True
if 'member_form_key' not in st.session_state:
    st.session_state.member_form_key = "member_form_initial"
if 'confirm_delete_member_id' not in st.session_state:
    st.session_state.confirm_delete_member_id = None

# Keys from render_group_plans_tab
if 'group_plan_selected_id' not in st.session_state:
    st.session_state.group_plan_selected_id = None
if 'group_plan_name' not in st.session_state:
    st.session_state.group_plan_name = ""
if 'group_plan_duration_days' not in st.session_state:
    st.session_state.group_plan_duration_days = 30
if 'group_plan_default_amount' not in st.session_state:
    st.session_state.group_plan_default_amount = 0.0
if 'group_plan_is_active' not in st.session_state:
    st.session_state.group_plan_is_active = True
if 'group_plan_display_name_readonly' not in st.session_state:
    st.session_state.group_plan_display_name_readonly = ""
if 'group_plan_form_key' not in st.session_state:
    st.session_state.group_plan_form_key = "group_plan_form_initial"
if 'confirm_delete_group_plan_id' not in st.session_state:
    st.session_state.confirm_delete_group_plan_id = None

# Keys from render_reporting_tab
if 'financial_report_output' not in st.session_state:
    st.session_state.financial_report_output = None
if 'renewals_report_data' not in st.session_state:
    st.session_state.renewals_report_data = None
if 'report_month_financial' not in st.session_state:
    st.session_state.report_month_financial = default_today.replace(day=1)

# Key for radio button in memberships tab
if 'membership_mode_selector' not in st.session_state:
    st.session_state.membership_mode_selector = 'Group Class Memberships'

# Keys related to clear_membership_form_state() - these are typically set by the function itself
# but initializing them can prevent potential conditional read-before-write issues if logic changes.
if 'create_member_id' not in st.session_state:
    st.session_state.create_member_id = None
if 'create_plan_id_display' not in st.session_state:
    st.session_state.create_plan_id_display = None # Or ""
if 'create_transaction_amount' not in st.session_state:
    st.session_state.create_transaction_amount = 0.0
if 'create_start_date' not in st.session_state:
    st.session_state.create_start_date = default_today
if 'selected_plan_duration_display' not in st.session_state:
    st.session_state.selected_plan_duration_display = ""

# Dynamic form keys for clearing/resetting forms (already initialized in the list above, e.g. gc_membership_form_key)
# Widget keys like 'gc_membership_select_widget', 'pt_membership_select_widget', 'member_select_widget',
# 'group_plan_select_widget', 'financial_report_month_selector' are generally managed by Streamlit.
# Explicit initialization is mostly for custom logic state variables.

def clear_membership_form_state():
    st.session_state.create_member_id = None
    st.session_state.create_plan_id_display = None
    st.session_state.create_transaction_amount = 0.0
    st.session_state.create_start_date = date.today()
    st.session_state.selected_plan_duration_display = ""

    if "form_key_create_membership" in st.session_state: # GC specific form key
        st.session_state.form_key_create_membership = f"form_gc_{datetime.now().timestamp()}"
    if "pt_form_key" in st.session_state: # PT specific form key
        st.session_state.pt_form_key = f"form_pt_{datetime.now().timestamp()}"


def render_new_group_class_membership_form():
    st.subheader("Create New Group Class Membership")

    try:
        all_members = api.get_all_members_for_view() # Updated API call
        member_options = {member.id: f"{member.name} (ID: {member.id})" for member in all_members if member.is_active == 1}
        if not member_options:
            st.warning("No active members available to create a membership for.")
            return
    except Exception as e:
        st.error(f"Error fetching members: {e}")
        return

    try:
        all_group_plans = api.get_all_group_plans_for_view() # Updated API call
        plan_options = {
            plan.id: f"{plan.name} ({plan.duration_days} days, ₹{plan.price or 0:.2f})"
            for plan in all_group_plans if plan.is_active # Corrected
        }
        if not plan_options:
            st.warning("No active group plans available.")
            return
    except Exception as e:
        st.error(f"Error fetching group plans: {e}")
        return

    with st.form("new_gc_membership_form", clear_on_submit=True):
        selected_member_id = st.selectbox("Select Member", options=list(member_options.keys()), format_func=lambda id: member_options[id])
        selected_plan_id = st.selectbox("Select Group Plan", options=list(plan_options.keys()), format_func=lambda id: plan_options[id])
        start_date_form = st.date_input("Start Date", value=date.today()) # Renamed to avoid conflict
        amount_paid_form = st.number_input("Amount Paid (₹)", min_value=0.0, format="%.2f") # Renamed

        submitted = st.form_submit_button("Create Group Class Membership")
        if submitted:
            if not selected_member_id or not selected_plan_id:
                st.error("Member and Plan must be selected.")
                return # Added return
            elif amount_paid_form <= 0: # Use renamed variable
                st.error("Amount paid must be greater than zero.")
                return # Added return
            else:
                try:
                    record_id = api.create_group_class_membership(
                        member_id=selected_member_id,
                        plan_id=selected_plan_id,
                        start_date_str=start_date_form.strftime("%Y-%m-%d"), # Use renamed
                        amount_paid=amount_paid_form # Use renamed
                    )
                    if record_id:
                        st.success(f"Group Class Membership created with ID: {record_id}")
                        st.rerun()
                    else:
                        st.error("Failed to create Group Class Membership.")
                except Exception as e:
                    st.error(f"Error creating membership: {e}")


def render_new_pt_membership_form():
    st.subheader("Create New Personal Training Membership")

    try:
        all_members_for_pt_form = api.get_all_members_for_view()
        member_options = {
            member.id: f"{member.name} (ID: {member.id})"
            for member in all_members_for_pt_form if member.is_active == 1
        }
        if not member_options:
            st.warning("No active members available to create a PT membership for.")
            return
    except Exception as e:
        st.error(f"Error fetching members: {e}")
        return

    with st.form("new_pt_membership_form", clear_on_submit=True):
        selected_member_id_pt = st.selectbox("Select Member", options=list(member_options.keys()), format_func=lambda id: member_options[id]) # Renamed
        purchase_date_pt = st.date_input("Purchase Date", value=date.today()) # Renamed
        amount_paid_pt = st.number_input("Amount Paid (₹)", min_value=0.0, format="%.2f") # Renamed
        sessions_purchased_pt = st.number_input("Sessions Purchased", min_value=1, step=1) # Renamed

        submitted = st.form_submit_button("Create Personal Training Membership")
        if submitted:
            if not selected_member_id_pt or sessions_purchased_pt <= 0: # Use renamed
                st.error("Member must be selected and sessions purchased must be greater than zero.")
                return # Added return
            elif amount_paid_pt <= 0: # Use renamed
                 st.error("Amount paid must be greater than zero.")
                 return # Added return
            else:
                try:
                    record_id = api.create_pt_membership(
                        member_id=selected_member_id_pt, # Use renamed
                        purchase_date=purchase_date_pt.strftime("%Y-%m-%d"), # Use renamed
                        amount_paid=amount_paid_pt, # Use renamed
                        sessions_purchased=sessions_purchased_pt # Use renamed
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
        if st.button("➕ Add New Group Class Membership", key="gc_add_new_button"): # Moved
            st.session_state.selected_gc_membership_id = "add_new"
            st.session_state.confirm_delete_gc_membership_id = None
            st.session_state.gc_membership_form_key = f"gc_form_{datetime.now().timestamp()}"
            st.session_state.gc_member_id_form = None
            st.session_state.gc_member_name_display = ""
            st.session_state.gc_plan_id_form = None
            st.session_state.gc_start_date_form = date.today()
            st.session_state.gc_amount_paid_form = 0.0
            # st.rerun() # Commented for testing

        left_col, right_col = st.columns([1, 2])

        with right_col:
            st.subheader("Existing Group Class Memberships")
            try:
                all_gc_memberships = api.get_all_group_class_memberships_for_view()
                if not all_gc_memberships:
                    all_gc_memberships = []
            except Exception as e:
                st.error(f"Error fetching group class memberships: {e}")
                all_gc_memberships = []

            # Button moved up
            st.markdown("---")
            st.write("**Existing Group Class Memberships:**")

            if not all_gc_memberships:
                st.info("No group class memberships found.")

            gc_membership_options = { # Defined here for delete confirmation message
                m.id: f"{m.member_name} - {m.plan_name}" for m in all_gc_memberships
            }

            for m in all_gc_memberships:
                display_text = f"{m.member_name} - {m.plan_name} (Start: {m.start_date}) - ID: {m.id}"
                st.markdown(display_text)
                if st.button(f"Select##GC{m.id}", key=f"select_gc_{m.id}"):
                    st.session_state.selected_gc_membership_id = m.id
                    st.session_state.confirm_delete_gc_membership_id = None
                    st.session_state.gc_membership_form_key = f"gc_form_{datetime.now().timestamp()}"
                    selected_data = next((mem for mem in all_gc_memberships if mem.id == m.id), None)
                    if selected_data:
                        st.session_state.gc_member_id_form = selected_data.member_id
                        st.session_state.gc_member_name_display = selected_data.member_name or ""
                        st.session_state.gc_plan_id_form = selected_data.plan_id
                        start_date_val = selected_data.start_date
                        if isinstance(start_date_val, str):
                            st.session_state.gc_start_date_form = datetime.strptime(start_date_val, "%Y-%m-%d").date()
                        elif isinstance(start_date_val, date):
                            st.session_state.gc_start_date_form = start_date_val
                        else:
                            st.session_state.gc_start_date_form = date.today()
                        st.session_state.gc_amount_paid_form = selected_data.amount_paid or 0.0
                    else:
                        st.error("Selected membership data not found. Please try again.")
                        st.session_state.selected_gc_membership_id = "add_new"
                    # st.rerun() # Commented for testing
                st.markdown("---")

        with left_col:
            if st.session_state.selected_gc_membership_id == "add_new":
                st.subheader("Add New Group Class Membership")
            else:
                st.subheader(f"Edit Group Class Membership (ID: {st.session_state.selected_gc_membership_id})")

            try:
                all_members = api.get_all_members_for_view()
                active_members = [member for member in all_members if member.is_active == 1]
                member_options_for_select = {member.id: f"{member.name} (ID: {member.id})" for member in active_members}
            except Exception as e:
                st.error(f"Error fetching members: {e}")
                member_options_for_select = {}

            try:
                all_group_plans = api.get_all_group_plans_for_view()
                plan_options_for_select = {
                    plan.id: f"{plan.name} ({plan.duration_days} days, ₹{plan.price or 0:.2f})"
                    for plan in all_group_plans if plan.is_active # Corrected
                }
            except Exception as e:
                st.error(f"Error fetching group plans: {e}")
                plan_options_for_select = {}

            with st.form(key=st.session_state.gc_membership_form_key, clear_on_submit=False):
                form_member_id_gc = None # Renamed to avoid conflict
                if st.session_state.selected_gc_membership_id == "add_new":
                    if not member_options_for_select:
                        st.warning("No active members available. Please add members first.")
                    else:
                        form_member_id_gc = st.selectbox( # Use renamed
                            "Select Member",
                            options=list(member_options_for_select.keys()),
                            format_func=lambda id_val: member_options_for_select[id_val],
                            key="gc_form_member_id_select",
                            index=0
                        )
                else:
                    st.text_input("Member", value=st.session_state.gc_member_name_display, disabled=True, key="gc_form_member_name_display")
                    form_member_id_gc = st.session_state.gc_member_id_form

                form_plan_id_gc = None # Renamed
                if not plan_options_for_select:
                    st.warning("No active group plans available. Please add plans first.")
                else:
                    plan_ids_list = list(plan_options_for_select.keys())
                    current_plan_id_index = 0
                    if st.session_state.gc_plan_id_form and st.session_state.gc_plan_id_form in plan_ids_list:
                        current_plan_id_index = plan_ids_list.index(st.session_state.gc_plan_id_form)

                    form_plan_id_gc = st.selectbox( # Use renamed
                        "Select Group Plan",
                        options=plan_ids_list,
                        format_func=lambda id_val: plan_options_for_select[id_val],
                        key="gc_form_plan_id_select",
                        index=current_plan_id_index
                    )

                form_start_date_gc = st.date_input("Start Date", value=st.session_state.gc_start_date_form, key="gc_form_start_date") # Renamed
                form_amount_paid_gc = st.number_input("Amount Paid (₹)", value=st.session_state.gc_amount_paid_form, min_value=0.0, format="%.2f", key="gc_form_amount_paid") # Renamed

                form_cols = st.columns(3 if st.session_state.selected_gc_membership_id != "add_new" else 2)
                with form_cols[0]:
                    save_button_gc = st.form_submit_button("Save Membership") # Renamed
                delete_button_gc = None # Initialize
                if st.session_state.selected_gc_membership_id != "add_new":
                    with form_cols[1]:
                        delete_button_gc = st.form_submit_button("Delete Membership") # Use Renamed
                with form_cols[-1]:
                    clear_button_gc = st.form_submit_button("Clear / Cancel") # Renamed

            # Actions triggered by form submission buttons are processed here, outside the form context.
            if save_button_gc: # Use renamed
                if not form_member_id_gc or not form_plan_id_gc: # Use renamed
                    st.error("Member and Plan must be selected.")
                elif form_amount_paid_gc <= 0 and st.session_state.selected_gc_membership_id == "add_new":
                    st.error("Amount paid must be greater than zero for new memberships.")
                else:
                    try:
                        if st.session_state.selected_gc_membership_id == "add_new":
                            record_id = api.create_group_class_membership(
                                member_id=form_member_id_gc, # Use renamed
                                plan_id=form_plan_id_gc, # Use renamed
                                start_date_str=form_start_date_gc.strftime("%Y-%m-%d"), # Use renamed
                                amount_paid=form_amount_paid_gc # Use renamed
                            )
                            if record_id:
                                st.success(f"Group Class Membership created with ID: {record_id}")
                                st.session_state.selected_gc_membership_id = "add_new"
                                st.session_state.gc_member_id_form = None
                                st.session_state.gc_plan_id_form = None
                                st.session_state.gc_start_date_form = date.today()
                                st.session_state.gc_amount_paid_form = 0.0
                                st.session_state.gc_membership_form_key = f"gc_form_{datetime.now().timestamp()}"
                                # st.rerun() # Commented for testing
                            else:
                                st.error("Failed to create Group Class Membership.")
                        else:
                            try:
                                success_gc_update = api.update_group_class_membership_record( # Renamed
                                    membership_id=st.session_state.selected_gc_membership_id,
                                    member_id=form_member_id_gc, # Use stored member_id for update (already renamed form_member_id_gc)
                                    plan_id=form_plan_id_gc, # Use renamed
                                    start_date=form_start_date_gc.strftime("%Y-%m-%d"), # Use renamed
                                    amount_paid=form_amount_paid_gc, # Use renamed
                                )
                                if success_gc_update: # Use renamed
                                    st.success("Membership updated successfully!")
                                    st.session_state.selected_gc_membership_id = "add_new"
                                    # st.rerun() # Commented for testing
                                else:
                                    st.error("Failed to update membership.")
                            except Exception as e:
                                st.error(f"An error occurred while updating: {e}")
                    except Exception as e:
                        st.error(f"Error processing membership: {e}")

            if st.session_state.selected_gc_membership_id != "add_new" and delete_button_gc: # Use renamed
                st.session_state.confirm_delete_gc_membership_id = st.session_state.selected_gc_membership_id
                # st.rerun() # Commented for testing to allow confirmation to show

            if clear_button_gc: # Use renamed
                st.session_state.selected_gc_membership_id = "add_new"
                st.session_state.gc_member_id_form = None
                st.session_state.gc_member_name_display = ""
                st.session_state.gc_plan_id_form = None
                st.session_state.gc_start_date_form = date.today()
                st.session_state.gc_amount_paid_form = 0.0
                st.session_state.confirm_delete_gc_membership_id = None
                st.session_state.gc_membership_form_key = f"gc_form_{datetime.now().timestamp()}"
                # st.rerun() # Commented for testing

            # Confirmation dialog for GC deletion - Placed outside the form block
            if st.session_state.confirm_delete_gc_membership_id is not None and \
               st.session_state.confirm_delete_gc_membership_id == st.session_state.selected_gc_membership_id and \
               st.session_state.selected_gc_membership_id != "add_new":

                membership_to_delete_info = gc_membership_options.get(st.session_state.confirm_delete_gc_membership_id, "this membership")
                st.warning(f"Are you sure you want to delete {membership_to_delete_info}? This action cannot be undone.")

                confirm_cols_delete_gc = st.columns(2) # Renamed to avoid conflict
                with confirm_cols_delete_gc[0]:
                    if st.button("YES, DELETE Permanently", key=f"confirm_delete_gc_btn_{st.session_state.confirm_delete_gc_membership_id}"):
                        try:
                            success_gc_delete = api.delete_group_class_membership_record(st.session_state.confirm_delete_gc_membership_id) # Renamed
                            if success_gc_delete: # Use renamed
                                st.success(f"Group Class Membership ID {st.session_state.confirm_delete_gc_membership_id} deleted.")
                                st.session_state.selected_gc_membership_id = "add_new" # Reset selection
                                st.session_state.gc_member_id_form = None
                                st.session_state.gc_plan_id_form = None
                                st.session_state.gc_start_date_form = date.today()
                                st.session_state.gc_amount_paid_form = 0.0
                                st.session_state.confirm_delete_gc_membership_id = None # Clear confirmation
                                st.session_state.gc_membership_form_key = f"gc_form_{datetime.now().timestamp()}" # Reset form
                                # st.rerun() # Commented for testing
                            else:
                                st.error(f"Failed to delete Group Class Membership ID {st.session_state.confirm_delete_gc_membership_id}.")
                                st.session_state.confirm_delete_gc_membership_id = None # Clear confirmation on failure
                                # st.rerun() # Commented for testing
                        except Exception as e:
                            st.error(f"Error deleting: {e}")
                            st.session_state.confirm_delete_gc_membership_id = None # Clear confirmation on error
                            # st.rerun() # Commented for testing
                with confirm_cols_delete_gc[1]: # Use renamed columns
                    if st.button("Cancel Deletion", key=f"cancel_delete_gc_btn_{st.session_state.confirm_delete_gc_membership_id}"):
                        st.session_state.confirm_delete_gc_membership_id = None # Clear confirmation
                        # st.rerun() # Commented for testing

    elif membership_mode == 'Personal Training Memberships':
        if st.button("➕ Add New PT Membership", key="pt_add_new_button"):
            st.session_state.selected_pt_membership_id = "add_new"
            st.session_state.confirm_delete_pt_membership_id = None
            st.session_state.pt_membership_form_key = f"pt_form_{datetime.now().timestamp()}"
            st.session_state.pt_member_id_form = None
            st.session_state.pt_member_name_display = ""
            st.session_state.pt_purchase_date_form = date.today()
            st.session_state.pt_amount_paid_form = 0.0
            st.session_state.pt_sessions_purchased_form = 1
            if 'pt_notes_form' in st.session_state:
                st.session_state.pt_notes_form = ""
            # st.rerun() # Commented for testing

        pt_left_col, pt_right_col = st.columns([1, 2])

        with pt_right_col:
            st.subheader("Existing Personal Training Memberships")
            try:
                all_pt_memberships = api.get_all_pt_memberships_for_view()
                if not all_pt_memberships:
                    all_pt_memberships = []
            except Exception as e:
                st.error(f"Error fetching PT memberships: {e}")
                all_pt_memberships = []

            # Button moved up
            st.markdown("---")
            st.write("**Existing Personal Training Memberships:**")

            if not all_pt_memberships:
                st.info("No Personal Training memberships found.")

            pt_membership_options = { # Defined here for delete confirmation
                pt_m.membership_id: f"{pt_m.member_name} - Sessions: {pt_m.sessions_remaining}/{pt_m.sessions_total}"
                for pt_m in all_pt_memberships
            }

            for pt_m in all_pt_memberships:
                display_text = (
                    f"{pt_m.member_name} - Total: {pt_m.sessions_total}, Rem: {pt_m.sessions_remaining} "
                    f"(Purchased: {pt_m.purchase_date}) - ID: {pt_m.membership_id}"
                )
                st.markdown(display_text)
                if st.button(f"Select##PT{pt_m.membership_id}", key=f"select_pt_{pt_m.membership_id}"):
                    st.session_state.selected_pt_membership_id = pt_m.membership_id
                    st.session_state.confirm_delete_pt_membership_id = None
                    st.session_state.pt_membership_form_key = f"pt_form_{datetime.now().timestamp()}"
                    selected_pt_data = next((m_pt for m_pt in all_pt_memberships if m_pt.membership_id == pt_m.membership_id), None) # Shadowing m
                    if selected_pt_data:
                        st.session_state.pt_member_id_form = selected_pt_data.member_id
                        st.session_state.pt_member_name_display = selected_pt_data.member_name or ""
                        purchase_date_val = selected_pt_data.purchase_date
                        if isinstance(purchase_date_val, str):
                            st.session_state.pt_purchase_date_form = datetime.strptime(purchase_date_val, "%Y-%m-%d").date()
                        elif isinstance(purchase_date_val, date):
                            st.session_state.pt_purchase_date_form = purchase_date_val
                        else:
                            st.session_state.pt_purchase_date_form = date.today()

                        st.session_state.pt_amount_paid_form = selected_pt_data.amount_paid or 0.0
                        st.session_state.pt_sessions_purchased_form = selected_pt_data.sessions_total or 1
                        if hasattr(selected_pt_data, 'notes') and 'pt_notes_form' in st.session_state:
                             st.session_state.pt_notes_form = selected_pt_data.notes or ""
                    else:
                        st.error("Selected PT membership data not found.")
                        st.session_state.selected_pt_membership_id = "add_new"
                    # st.rerun() # Commented for testing
                st.markdown("---")

        with pt_left_col:
            if st.session_state.selected_pt_membership_id == "add_new":
                st.subheader("Add New PT Membership")
            else:
                st.subheader(f"Edit PT Membership (ID: {st.session_state.selected_pt_membership_id})")

            try:
                all_members_pt_form = api.get_all_members_for_view() # Renamed
                active_members_pt = [member for member in all_members_pt_form if member.is_active == 1]
                member_options_for_pt_select = {member.id: f"{member.name} (ID: {member.id})" for member in active_members_pt}
            except Exception as e:
                st.error(f"Error fetching members: {e}")
                member_options_for_pt_select = {}

            with st.form(key=st.session_state.pt_membership_form_key, clear_on_submit=False):
                form_pt_member_id_select_val = None # Renamed
                if st.session_state.selected_pt_membership_id == "add_new":
                    if not member_options_for_pt_select:
                        st.warning("No active members available. Please add members first.")
                    else:
                        form_pt_member_id_select_val = st.selectbox( # Use Renamed
                            "Select Member",
                            options=list(member_options_for_pt_select.keys()),
                            format_func=lambda id_val: member_options_for_pt_select[id_val],
                            key="pt_form_member_id_select"
                        )
                else:
                    st.text_input("Member", value=st.session_state.pt_member_name_display, disabled=True, key="pt_form_member_name_display")

                form_pt_purchase_date_val = st.date_input("Purchase Date", value=st.session_state.pt_purchase_date_form, key="pt_form_purchase_date") # Renamed
                form_pt_amount_paid_val = st.number_input("Amount Paid (₹)", value=st.session_state.pt_amount_paid_form, min_value=0.0, format="%.2f", key="pt_form_amount_paid") # Renamed
                form_pt_sessions_purchased_val = st.number_input("Sessions Purchased", value=st.session_state.pt_sessions_purchased_form, min_value=1, step=1, key="pt_form_sessions_purchased") # Renamed

                pt_form_cols = st.columns(3 if st.session_state.selected_pt_membership_id != "add_new" else 2)
                with pt_form_cols[0]:
                    pt_save_button = st.form_submit_button("Save PT Membership")
                pt_delete_button = None # Initialize
                if st.session_state.selected_pt_membership_id != "add_new":
                    with pt_form_cols[1]:
                        pt_delete_button = st.form_submit_button("Delete PT Membership")
                with pt_form_cols[-1]:
                    pt_clear_button = st.form_submit_button("Clear / Cancel")

            # Actions triggered by PT form submission buttons are processed here, outside the form context.
            if pt_save_button:
                member_id_to_save = form_pt_member_id_select_val if st.session_state.selected_pt_membership_id == "add_new" else st.session_state.pt_member_id_form

                if st.session_state.selected_pt_membership_id == "add_new":
                    if not member_id_to_save: # Check renamed variable
                        st.error("Member must be selected.")
                    elif form_pt_amount_paid_val <= 0: # Check renamed
                        st.error("Amount paid must be greater than zero.")
                    elif form_pt_sessions_purchased_val <= 0: # Check renamed
                        st.error("Sessions purchased must be greater than zero.")
                    else:
                        try:
                            record_id = api.create_pt_membership(
                                member_id=member_id_to_save, # Use common variable
                                purchase_date=form_pt_purchase_date_val.strftime("%Y-%m-%d"), # Use renamed
                                amount_paid=form_pt_amount_paid_val, # Use renamed
                                sessions_purchased=form_pt_sessions_purchased_val # Use renamed
                            )
                            if record_id:
                                st.success(f"PT Membership created with ID: {record_id}")
                                st.session_state.selected_pt_membership_id = "add_new"
                                st.session_state.pt_membership_form_key = f"pt_form_{datetime.now().timestamp()}"
                                # st.rerun() # Commented for testing
                            else:
                                st.error("Failed to create PT Membership.")
                        except Exception as e:
                            st.error(f"Error creating PT membership: {e}")
                else:
                    if form_pt_amount_paid_val <= 0: # Check renamed
                        st.error("Amount paid must be greater than zero.")
                    elif form_pt_sessions_purchased_val <= 0: # Check renamed
                        st.error("Sessions purchased must be greater than zero.")
                    else:
                        try:
                            success_pt_update = api.update_pt_membership( # Renamed
                                membership_id=st.session_state.selected_pt_membership_id,
                                purchase_date=form_pt_purchase_date_val.strftime("%Y-%m-%d"), # Use renamed
                                amount_paid=form_pt_amount_paid_val, # Use renamed
                                sessions_purchased=form_pt_sessions_purchased_val # Use renamed
                            )
                            if success_pt_update: # Use renamed
                                st.success(f"PT Membership ID {st.session_state.selected_pt_membership_id} updated.")
                                # st.rerun() # Commented for testing
                            else:
                                st.error(f"Failed to update PT Membership ID {st.session_state.selected_pt_membership_id}.")
                        except Exception as e:
                            st.error(f"Error updating PT membership: {e}")

            if st.session_state.selected_pt_membership_id != "add_new" and pt_delete_button:
                st.session_state.confirm_delete_pt_membership_id = st.session_state.selected_pt_membership_id
                # st.rerun() # Commented for testing to allow confirmation to show

            if pt_clear_button:
                st.session_state.selected_pt_membership_id = "add_new"
                st.session_state.pt_member_id_form = None
                st.session_state.pt_member_name_display = ""
                st.session_state.pt_purchase_date_form = date.today()
                st.session_state.pt_amount_paid_form = 0.0
                st.session_state.pt_sessions_purchased_form = 1
                st.session_state.confirm_delete_pt_membership_id = None
                st.session_state.pt_membership_form_key = f"pt_form_{datetime.now().timestamp()}"
                # st.rerun() # Commented for testing

            # Confirmation dialog for PT deletion - Placed outside the form block
            if st.session_state.confirm_delete_pt_membership_id is not None and \
               st.session_state.confirm_delete_pt_membership_id == st.session_state.selected_pt_membership_id and \
               st.session_state.selected_pt_membership_id != "add_new":

                pt_membership_to_delete_info = pt_membership_options.get(st.session_state.confirm_delete_pt_membership_id, "this PT membership")
                st.warning(f"Are you sure you want to delete {pt_membership_to_delete_info}? This action cannot be undone.")

                pt_confirm_cols_delete_pt = st.columns(2) # Renamed to avoid conflict
                with pt_confirm_cols_delete_pt[0]:
                    if st.button("YES, DELETE PT Membership Permanently", key=f"confirm_delete_pt_btn_{st.session_state.confirm_delete_pt_membership_id}"):
                        try:
                            deleted_pt = api.delete_pt_membership(st.session_state.confirm_delete_pt_membership_id) # Renamed
                            if deleted_pt: # Use renamed
                                st.success(f"PT Membership ID {st.session_state.confirm_delete_pt_membership_id} deleted.")
                                st.session_state.selected_pt_membership_id = "add_new" # Reset selection
                                st.session_state.confirm_delete_pt_membership_id = None # Clear confirmation
                                st.session_state.pt_membership_form_key = f"pt_form_{datetime.now().timestamp()}" # Reset form
                                # st.rerun() # Commented for testing
                            else:
                                st.error(f"Failed to delete PT Membership ID {st.session_state.confirm_delete_pt_membership_id}.")
                                st.session_state.confirm_delete_pt_membership_id = None # Clear confirmation on failure
                                # st.rerun() # Commented for testing
                        except Exception as e:
                            st.error(f"Error deleting PT membership: {e}")
                            st.session_state.confirm_delete_pt_membership_id = None # Clear confirmation on error
                            # st.rerun() # Commented for testing
                with pt_confirm_cols_delete_pt[1]: # Use renamed columns
                    if st.button("Cancel PT Deletion", key=f"cancel_delete_pt_btn_{st.session_state.confirm_delete_pt_membership_id}"):
                        st.session_state.confirm_delete_pt_membership_id = None # Clear confirmation
                        # st.rerun() # Commented for testing


def render_members_tab():
    st.header("Manage Members")

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
            all_members = api.get_all_members_for_view()
            if not all_members:
                st.info("No members found. Add a member using the form on the right.")
                all_members = []
        except Exception as e:
            st.error(f"Error fetching members: {e}")
            all_members = []

        member_options = {member.id: f"{member.name} ({member.phone or 'N/A'})" for member in all_members}
        member_options_list = [None] + list(member_options.keys())

        def format_func_member(member_id):
            if member_id is None:
                return "➕ Add New Member"
            return member_options.get(member_id, "Unknown Member")

        selected_id_display = st.selectbox(
            "Select Member (or Add New)",
            options=member_options_list,
            format_func=format_func_member,
            key="member_select_widget", # Removed index to default to current session state if value exists
            index=member_options_list.index(st.session_state.member_selected_id) if st.session_state.member_selected_id in member_options_list else 0
        )
        if selected_id_display != st.session_state.member_selected_id : # Check against widget value
            st.session_state.member_selected_id = selected_id_display # Update from widget
            st.session_state.confirm_delete_member_id = None # Reset delete confirmation
            if st.session_state.member_selected_id is not None:
                selected_member_data = next((m for m in all_members if m.id == st.session_state.member_selected_id), None)
                if selected_member_data:
                    st.session_state.member_name = selected_member_data.name or ""
                    st.session_state.member_email = selected_member_data.email or ""
                    st.session_state.member_phone = selected_member_data.phone or ""
                    st.session_state.member_is_active = bool(selected_member_data.is_active)
                    st.session_state.member_form_key = f"member_form_{datetime.now().timestamp()}" # Reset form
            else: # "Add New Member" is selected
                clear_member_form(clear_selection=False) # Clear form fields but keep "Add New" selected
            # st.rerun() # Commented for testing

    with right_col:
        if st.session_state.member_selected_id is None:
            st.subheader("Add New Member")
        else:
            st.subheader(f"Edit Member: {st.session_state.member_name}")

        st.write("Member form is temporarily commented out for debugging.")
        # with st.form(key=st.session_state.member_form_key, clear_on_submit=False):
        #     name_form_val = st.text_input("Name", value=st.session_state.member_name, key="member_form_name") # Renamed
        #     email_form_val = st.text_input("Email", value=st.session_state.member_email, key="member_form_email") # Renamed
        #     phone_form_val = st.text_input("Phone", value=st.session_state.member_phone, key="member_form_phone") # Renamed
        #     is_active_form_val = st.checkbox("Is Active", value=st.session_state.member_is_active, key="member_form_is_active") # Renamed

        #     form_col1, form_col2, form_col3 = st.columns(3)
        #     with form_col1:
        #         save_button_member = st.form_submit_button("Save Member" if st.session_state.member_selected_id else "Add Member") # Renamed
        #     delete_button_member = None # Initialize
        #     if st.session_state.member_selected_id is not None:
        #         with form_col2:
        #             delete_button_member = st.form_submit_button("Delete Member") # Renamed
        #     with form_col3:
        #         clear_button_member = st.form_submit_button("Clear / New") # Renamed

        # if save_button_member: # Use Renamed
        #     if st.session_state.member_selected_id is None: # ADD Path
        #         if not name_form_val or not phone_form_val: # Use Renamed
        #             st.error("Name and Phone are required.")
        #         else:
        #             try:
        #                 member_id = api.add_member(name=name_form_val, phone=phone_form_val, email=email_form_val) # Use Renamed
        #                 if member_id:
        #                     st.success(f"Member '{name_form_val}' added successfully with ID: {member_id}") # Use Renamed
        #                     clear_member_form(clear_selection=True)
        #                     # st.rerun() # Commented for testing
        #                 else:
        #                     st.error("Failed to add member. Please check details.")
        #             except ValueError as e:
        #                 st.error(f"Error: {e}")
        #             except Exception as e:
        #                 st.error(f"An unexpected error occurred: {e}")
        #     else: # UPDATE Path
        #         if not name_form_val or not phone_form_val: # Use Renamed
        #             st.error("Name and Phone cannot be empty.")
        #         else:
        #             try:
        #                 success_member_update = api.update_member( # Renamed
        #                     member_id=st.session_state.member_selected_id,
        #                     name=name_form_val, # Use Renamed
        #                     phone=phone_form_val, # Use Renamed
        #                     email=email_form_val, # Use Renamed
        #                     is_active=is_active_form_val # Use Renamed
        #                 )
        #                 if success_member_update: # Use Renamed
        #                     st.success(f"Member '{name_form_val}' updated successfully.") # Use Renamed
        #                     clear_member_form(clear_selection=True)
        #                     # st.rerun() # Commented for testing
        #                 else:
        #                     st.error("Failed to update member. The phone number might already be in use by another member.")
        #             except ValueError as e:
        #                 st.error(f"Error: {e}")
        #             except Exception as e:
        #                 st.error(f"An unexpected error occurred: {e}")

        # if st.session_state.member_selected_id is not None and delete_button_member: # Use Renamed
        #     # Confirmation logic starts here
        #     if st.session_state.confirm_delete_member_id != st.session_state.member_selected_id:
        #         st.session_state.confirm_delete_member_id = st.session_state.member_selected_id
        #         # No immediate rerun, let the warning and buttons appear below
        #     # This part will now always execute if confirm_delete_member_id is set
        #     if st.session_state.confirm_delete_member_id == st.session_state.member_selected_id: # Ensure it's for current selection
        #         st.warning(f"Are you sure you want to delete member '{st.session_state.member_name}'? This action cannot be undone.")
        #         confirm_col1, confirm_col2 = st.columns(2)
        #         with confirm_col1:
        #             if st.button("YES, DELETE Permanently", key=f"confirm_delete_member_btn_{st.session_state.member_selected_id}"):
        #                 try:
        #                     deleted_member = api.delete_member(st.session_state.member_selected_id) # Renamed
        #                     if deleted_member: # Use Renamed
        #                         st.success(f"Member '{st.session_state.member_name}' deleted successfully.")
        #                         clear_member_form(clear_selection=True)
        #                         st.session_state.confirm_delete_member_id = None
        #                         # st.rerun() # Commented for testing
        #                     else:
        #                         st.error("Failed to delete member. They might have active memberships or other issue.")
        #                         st.session_state.confirm_delete_member_id = None
        #                         # st.rerun() # Commented for testing
        #                 except Exception as e:
        #                     st.error(f"Error deleting member: {e}")
        #                     st.session_state.confirm_delete_member_id = None
        #                     # st.rerun() # Commented for testing
        #         with confirm_col2:
        #             if st.button("Cancel Deletion", key=f"cancel_delete_member_btn_{st.session_state.member_selected_id}"):
        #                 st.session_state.confirm_delete_member_id = None
        #                 # st.rerun() # Commented for testing

        # if clear_button_member: # Use Renamed
        #     clear_member_form(clear_selection=True)
        #     # st.rerun() # Commented for testing


def render_group_plans_tab():
    st.header("Manage Group Plans")

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
            all_group_plans = api.get_all_group_plans_for_view()
            if not all_group_plans:
                st.info("No group plans found. Add a plan using the form on the right.")
                all_group_plans = []
        except Exception as e:
            st.error(f"Error fetching group plans: {e}")
            all_group_plans = []

        plan_options = {plan.id: f"{plan.name} ({plan.duration_days} days)" for plan in all_group_plans}
        plan_options_list = [None] + list(plan_options.keys())

        def format_func_group_plan(plan_id):
            if plan_id is None:
                return "➕ Add New Group Plan"
            return plan_options.get(plan_id, f"Unnamed Plan (ID: {plan_id})")

        selected_group_plan_id_widget = st.selectbox(
            "Select Group Plan (or Add New)",
            options=plan_options_list,
            format_func=format_func_group_plan,
            key="group_plan_select_widget",
            index=plan_options_list.index(st.session_state.group_plan_selected_id) if st.session_state.group_plan_selected_id in plan_options_list else 0
        )

        if selected_group_plan_id_widget != st.session_state.group_plan_selected_id:
            st.session_state.group_plan_selected_id = selected_group_plan_id_widget
            st.session_state.confirm_delete_group_plan_id = None
            if st.session_state.group_plan_selected_id is not None:
                selected_plan_data = next((p for p in all_group_plans if p.id == st.session_state.group_plan_selected_id), None)
                if selected_plan_data:
                    st.session_state.group_plan_name = selected_plan_data.name or ""
                    st.session_state.group_plan_duration_days = selected_plan_data.duration_days or 30
                    st.session_state.group_plan_default_amount = selected_plan_data.price or 0.0
                    st.session_state.group_plan_is_active = selected_plan_data.is_active # Corrected: Use boolean is_active
                    st.session_state.group_plan_display_name_readonly = f"{selected_plan_data.name} ({selected_plan_data.duration_days} days)"
                    st.session_state.group_plan_form_key = f"group_plan_form_{datetime.now().timestamp()}"
            else:
                clear_group_plan_form(clear_selection=False)
            # st.rerun() # Commented for testing

    with right_col:
        if st.session_state.group_plan_selected_id is None:
            st.subheader("Add New Group Plan")
        else:
            st.subheader(f"Edit Group Plan: {st.session_state.group_plan_display_name_readonly}")

        st.write("Group Plan form is temporarily commented out for debugging.")
        # with st.form(key=st.session_state.group_plan_form_key, clear_on_submit=False):
        #     plan_name_form_val = st.text_input("Group Plan Name (e.g., Gold, Monthly)", value=st.session_state.group_plan_name, key="group_plan_form_name")
        #     duration_days_form_val = st.number_input("Duration (Days)", value=st.session_state.group_plan_duration_days, min_value=1, step=1, key="group_plan_form_duration")
        #     default_amount_form_val = st.number_input("Default Amount (₹)", value=st.session_state.group_plan_default_amount, min_value=0.0, format="%.2f", key="group_plan_form_amount")
        #     is_active_form_gp = st.checkbox("Is Active", value=st.session_state.group_plan_is_active, key="group_plan_form_is_active") # Renamed

        #     if st.session_state.group_plan_selected_id is not None and st.session_state.group_plan_display_name_readonly:
        #         st.text_input("Display Name (Auto-generated)", value=st.session_state.group_plan_display_name_readonly, disabled=True)

        #     form_col1, form_col2, form_col3 = st.columns(3)
        #     with form_col1:
        #         save_plan_button = st.form_submit_button(
        #             "Save Group Plan" if st.session_state.group_plan_selected_id else "Add Group Plan"
        #         )
        #     delete_plan_button = None # Initialize
        #     if st.session_state.group_plan_selected_id is not None:
        #         with form_col2:
        #             delete_plan_button = st.form_submit_button("Delete Group Plan")
        #     with form_col3:
        #         clear_plan_form_button = st.form_submit_button("Clear / New")

        # if save_plan_button:
        #     try:
        #         if not plan_name_form_val or duration_days_form_val <= 0:
        #             st.error("Group Plan Name and valid Duration (days > 0) are required.")
        #         elif st.session_state.group_plan_selected_id is None:  # ADD PATH
        #             plan_id = api.add_group_plan(
        #                 name=plan_name_form_val,
        #                 duration_days=duration_days_form_val,
        #                 default_amount=default_amount_form_val
        #                 # Note: is_active is not passed for add, API likely defaults it.
        #             )
        #             if plan_id:
        #                 st.success(f"Group Plan '{plan_name_form_val}' added successfully.")
        #                 clear_group_plan_form(clear_selection=True)
        #                 # st.rerun() # Commented for testing
        #             else:
        #                 st.error("Failed to add group plan. Display name might already exist or other validation error.")
        #         else:  # UPDATE PATH
        #             success_gp_update = api.update_group_plan( # Renamed result variable
        #                 plan_id=st.session_state.group_plan_selected_id,
        #                 name=plan_name_form_val,
        #                 duration_days=duration_days_form_val,
        #                 default_amount=default_amount_form_val,
        #                 is_active=is_active_form_gp # Use renamed checkbox value
        #             )
        #             if success_gp_update: # Use renamed result
        #                 st.success(f"Group Plan updated successfully.")
        #                 clear_group_plan_form(clear_selection=True)
        #                 # st.rerun() # Commented for testing
        #             else:
        #                 st.error("Failed to update group plan. Display name might already exist or other validation error.")
        #     except ValueError as ve:
        #         st.error(f"Validation error: {ve}")
        #     except Exception as e: # Catch-all for other exceptions
        #         st.error(f"An error occurred: {e}")

        # # Confirmation logic for delete
        # if st.session_state.group_plan_selected_id is not None and delete_plan_button:
        #     if st.session_state.confirm_delete_group_plan_id != st.session_state.group_plan_selected_id:
        #          st.session_state.confirm_delete_group_plan_id = st.session_state.group_plan_selected_id
        #     # This block now executes if confirm_delete_group_plan_id is set appropriately
        #     if st.session_state.confirm_delete_group_plan_id == st.session_state.group_plan_selected_id: # Check if it's the current one
        #         st.warning(f"Are you sure you want to delete group plan '{st.session_state.group_plan_display_name_readonly}'? This action cannot be undone.")
        #         confirm_col1, confirm_col2 = st.columns(2)
        #         with confirm_col1:
        #             if st.button("YES, DELETE Group Plan Permanently", key=f"confirm_delete_gplan_btn_{st.session_state.group_plan_selected_id}"):
        #                 try:
        #                     deleted_gp = api.delete_group_plan(st.session_state.group_plan_selected_id) # Renamed
        #                     if deleted_gp: # Use renamed
        #                         st.success(f"Group Plan '{st.session_state.group_plan_display_name_readonly}' deleted successfully.")
        #                         clear_group_plan_form(clear_selection=True)
        #                         st.session_state.confirm_delete_group_plan_id = None # Reset confirmation
        #                         # st.rerun() # Commented for testing
        #                     else:
        #                         st.error("Failed to delete group plan. It might be in use or another issue occurred.")
        #                         st.session_state.confirm_delete_group_plan_id = None # Reset confirmation
        #                         # st.rerun() # Commented for testing
        #                 except Exception as e:
        #                     st.error(f"Error deleting group plan: {e}")
        #                     st.session_state.confirm_delete_group_plan_id = None # Reset confirmation
        #                     # st.rerun() # Commented for testing
        #         with confirm_col2:
        #             if st.button("Cancel Group Plan Deletion", key=f"cancel_delete_gplan_btn_{st.session_state.group_plan_selected_id}"):
        #                 st.session_state.confirm_delete_group_plan_id = None # Reset confirmation
        #                 # st.rerun() # Commented for testing

        # if clear_plan_form_button:
        #     clear_group_plan_form(clear_selection=True)
        #     # st.rerun() # Commented for testing

def render_reporting_tab():
    st.header("Financial & Renewals Reporting")

    st.subheader("Monthly Financial Report")
    report_month_financial_val = st.date_input(
        "Select Month for Financial Report",
        value=st.session_state.report_month_financial, # Default to session state
        key="financial_report_month_selector",
    )
    # Update session state only if the widget value changes from the current session state
    if report_month_financial_val != st.session_state.report_month_financial:
        st.session_state.report_month_financial = report_month_financial_val
        st.session_state.financial_report_output = None # Clear old report data

    if st.button("Generate Monthly Financial Report", key="generate_financial_report"):
        # Use the value from session state, which is synced with the widget
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

            if not report_output or not report_output.get("details"): # Check for empty details
                st.info(f"No financial data found for {st.session_state.report_month_financial.strftime('%B %Y')}.")
            else:
                st.success(f"Financial report generated for {st.session_state.report_month_financial.strftime('%B %Y')}.")
        except Exception as e:
            st.error(f"Error generating financial report: {e}")
            st.session_state.financial_report_output = None # Clear on error

    if st.session_state.financial_report_output:
        summary_data = st.session_state.financial_report_output.get("summary", {})
        details_data = st.session_state.financial_report_output.get("details", [])
        total_income = summary_data.get("total_revenue", 0.0)

        st.metric(
            label=f"Total Income for {st.session_state.report_month_financial.strftime('%B %Y')}",
            value=f"₹{total_income:.2f}",
        )

        if details_data: # Only show dataframe and download if details exist
            df_financial = pd.DataFrame(details_data)
            st.dataframe(
                df_financial,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "purchase_date": st.column_config.DateColumn("Purchase Date", format="YYYY-MM-DD"),
                    "amount_paid": st.column_config.NumberColumn("Amount Paid (₹)", format="%.2f"),
                    "type": "Type",
                    "member_name": "Member Name",
                    "item_name": "Item/Plan Name"
                }
            )
            # Excel Download
            output_excel = io.BytesIO() # Renamed to avoid conflict
            with pd.ExcelWriter(output_excel, engine="openpyxl") as writer: # Use renamed
                df_financial.to_excel(writer, index=False, sheet_name="Financial Report")
            excel_data = output_excel.getvalue() # Use renamed
            st.download_button(
                label="Download Financial Report as Excel",
                data=excel_data,
                file_name=f"financial_report_{st.session_state.report_month_financial.strftime('%Y_%m')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        # If no details but there was a summary (e.g. total income > 0 but no line items)
        elif total_income > 0: # total_income is already calculated
            st.info(f"Summary available, but no detailed transactions for {st.session_state.report_month_financial.strftime('%B %Y')}.")
        # If financial_report_output exists but was empty (already handled by "No financial data found" above)
    st.divider()

    st.subheader("Upcoming Membership Renewals")
    if st.button("Generate Upcoming Renewals Report", key="generate_renewals_report"):
        try:
            renewal_data_list = api.generate_renewal_report()
            st.session_state.renewals_report_data = renewal_data_list # Store in session state
            if not renewal_data_list: # Check if list is empty
                st.info("No upcoming group class renewals found (e.g., in the next 30 days).")
            else:
                st.success("Upcoming group class renewals report generated successfully.")
        except Exception as e:
            st.error(f"Error generating renewals report: {e}")
            st.session_state.renewals_report_data = None # Clear on error

    # Display logic based on session state
    if st.session_state.renewals_report_data: # Check if data (even empty list) exists
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
                "amount_paid": st.column_config.NumberColumn("Amount Paid (₹)", format="%.2f"),
                "membership_type": "Type" # Assuming this field exists in the DTO from API
            }
        )
    elif st.session_state.renewals_report_data == []: # Explicitly check for empty list if already fetched
        st.info("No upcoming group class renewals found (e.g., in the next 30 days).")


tab_titles = ["Members", "Group Plans", "Memberships", "Reporting"]
tab_members, tab_group_plans, tab_memberships, tab_reporting = st.tabs(tab_titles)

with tab_members:
    render_members_tab()

with tab_group_plans:
    render_group_plans_tab()

with tab_memberships:
    render_memberships_tab()

with tab_reporting:
    render_reporting_tab()
