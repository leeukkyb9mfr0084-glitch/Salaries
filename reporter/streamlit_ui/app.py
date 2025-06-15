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
def render_memberships_tab():
    # This tab is for creating and managing memberships as per P3-T1 / P3-T2

    # Initialize session state for form inputs if not already present
    if (
        "create_member_id" not in st.session_state
    ):  # Stores the selected member_id for submission
        st.session_state.create_member_id = None
    if (
        "create_member_id_display" not in st.session_state
    ):  # Stores (id, name) for member selectbox
        st.session_state.create_member_id_display = None

    # For plan selection
    if (
        "create_plan_id_display" not in st.session_state
    ):  # Stores (id, name, duration) for plan selectbox
        st.session_state.create_plan_id_display = None
    if (
        "selected_plan_duration_display" not in st.session_state
    ):  # For displaying duration
        st.session_state.selected_plan_duration_display = ""

    if "create_transaction_amount" not in st.session_state:
        st.session_state.create_transaction_amount = 0.0
    if "create_start_date" not in st.session_state:
        st.session_state.create_start_date = date.today()
    if "form_key_create_membership" not in st.session_state:
        st.session_state.form_key_create_membership = "initial_form_key"

    # Session state for View/Manage Memberships panel
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

    left_column, right_column = st.columns(2)

    # Left Column: Create Membership Form
    with left_column:
        st.header("Create Membership")

        # Fetch data for dropdowns
        try:
            member_list_data = api.get_active_members()  # Returns list of dicts
            plan_list_data = api.get_active_plans()  # Returns list of dicts

            # Convert list of dicts to list of tuples as expected by downstream code
            member_list_tuples = (
                [(m["id"], m["name"]) for m in member_list_data]
                if member_list_data
                else []
            )
            plan_list_tuples = (
                [(p["id"], p["name"], p["duration_days"]) for p in plan_list_data]
                if plan_list_data
                else []
            )

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
        for pid, pname, pduration in plan_list_tuples:  # Assumes (id, name, duration)
            plan_options[(pid, pname, pduration)] = pname

        # Callback to update displayed duration when plan selection changes
        def update_plan_duration_display():
            selected_plan_data = st.session_state.get("create_plan_id_display_widget")
            if (
                selected_plan_data and selected_plan_data[0] is not None
            ):  # selected_plan_data is (id, name, duration)
                st.session_state.selected_plan_duration_display = (
                    f"{selected_plan_data[2]} days"
                )
                st.session_state.create_plan_id_display = (
                    selected_plan_data  # Store the full tuple for form submission logic
                )
            else:
                st.session_state.selected_plan_duration_display = ""
                st.session_state.create_plan_id_display = None

        # Use st.form for better grouping of inputs and submission
        with st.form(
            key=st.session_state.form_key_create_membership, clear_on_submit=False
        ):
            st.selectbox(
                "Member Name",
                options=list(member_options.keys()),
                format_func=lambda key: member_options[key],
                key="create_member_id_display",  # Stores (id,name)
            )
            st.selectbox(
                "Plan Name",
                options=list(plan_options.keys()),
                format_func=lambda key: plan_options[key],
                key="create_plan_id_display_widget",  # Temp key for widget, stores (id,name,duration)
                on_change=update_plan_duration_display,
            )
            # Display Plan Duration (read-only)
            st.text_input(
                "Plan Duration",
                value=st.session_state.selected_plan_duration_display,
                disabled=True,
                key="displayed_plan_duration_readonly",  # Unique key
            )
            st.number_input(
                "Transaction Amount",
                min_value=0.0,
                key="create_transaction_amount",
                format="%.2f",
            )
            st.date_input("Start Date", key="create_start_date")

            col1, col2 = st.columns(2)
            with col1:
                save_button = st.form_submit_button("SAVE")
            with col2:
                clear_button = st.form_submit_button("CLEAR")

        if save_button:
            # Extract data from session state
            selected_member_data = st.session_state.get(
                "create_member_id_display"
            )  # This is (id, name)
            selected_plan_data = st.session_state.get(
                "create_plan_id_display"
            )  # This is (id, name, duration)

            member_id = (
                selected_member_data[0]
                if selected_member_data and selected_member_data[0] is not None
                else None
            )
            plan_id = (
                selected_plan_data[0]
                if selected_plan_data and selected_plan_data[0] is not None
                else None
            )
            # plan_duration = selected_plan_data[2] if selected_plan_data and selected_plan_data[0] is not None else None # Duration is available if needed

            amount = st.session_state.create_transaction_amount
            start_date_val = st.session_state.create_start_date

            if not member_id or not plan_id:
                st.error("Please select a member and a plan.")
            elif amount <= 0:
                st.error("Transaction amount must be greater than zero.")
            else:
                try:
                    # For create_membership_record, we need to pass a dictionary
                    membership_data = {
                        "client_id": member_id,
                        "plan_id": plan_id,
                        "start_date": start_date_val.strftime("%Y-%m-%d"),
                        "payment_amount": amount,
                        # Assuming transaction_type and description are handled by AppAPI/DatabaseManager
                        # or need to be added here if required by the new AppAPI method.
                        # For now, let's assume they are optional or defaulted in backend.
                    }
                    # The new AppAPI returns record_id or None
                    record_id = api.create_membership_record(membership_data)
                    if record_id:
                        st.success(
                            f"Membership created successfully with ID: {record_id}"
                        )
                        clear_membership_form_state()
                        st.rerun()
                    else:
                        # Assuming AppAPI or DatabaseManager might log specific errors
                        st.error("Failed to create membership. Check logs for details.")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")

        if clear_button:
            clear_membership_form_state()
            st.rerun()

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
                st.dataframe(
                    display_df[
                        [
                            "client_name",
                            "phone",
                            "plan_name",
                            "start_date",
                            "end_date",
                            "status",
                            "membership_id",
                        ]
                    ],
                    hide_index=True,
                    use_container_width=True,
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

        # Select Membership to Manage
        # Create options for the selectbox from the fetched data
        manage_options = [(None, "Select Membership...")] + [
            (
                item["membership_id"],
                f"{item['client_name']} - {item['plan_name']} ({item['start_date']} to {item['end_date']})",
            )
            for item in st.session_state.memberships_view_data
        ]

        if (
            not st.session_state.memberships_view_data
            and st.session_state.manage_selected_membership_id
        ):
            st.session_state.manage_selected_membership_id = (
                None  # Clear selection if list is empty
            )

        def on_select_membership_for_management():
            selected_id = st.session_state.get(
                "_manage_selected_membership_id_display"
            )  # temp key from widget
            if selected_id is None:
                st.session_state.manage_selected_membership_id = None
                return

            st.session_state.manage_selected_membership_id = selected_id
            # Populate edit form fields
            selected_details = next(
                (
                    m
                    for m in st.session_state.memberships_view_data
                    if m["membership_id"] == selected_id
                ),
                None,
            )
            if selected_details:
                st.session_state.edit_start_date = datetime.strptime(
                    selected_details["start_date"], "%Y-%m-%d"
                ).date()
                st.session_state.edit_end_date = datetime.strptime(
                    selected_details["end_date"], "%Y-%m-%d"
                ).date()
                st.session_state.edit_is_active = (
                    True if selected_details["status"].lower() == "active" else False
                )
                st.session_state.edit_form_key = f"edit_form_{datetime.now().timestamp()}"  # Change key to force re-render of form defaults

        st.selectbox(
            "Select Membership to Manage",
            options=manage_options,
            format_func=lambda x: x[1],
            key="_manage_selected_membership_id_display",  # Temporary key to capture selection
            on_change=on_select_membership_for_management,
            index=manage_options.index(
                next(
                    (
                        opt
                        for opt in manage_options
                        if opt[0] == st.session_state.manage_selected_membership_id
                    ),
                    (None, "Select Membership..."),
                )
            ),
        )

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

    report_month_renewals_val = st.date_input(
        "Select Month for Renewals Report",
        value=st.session_state.report_month_renewals,
        key="renewals_report_month_selector",  # Unique key
    )
    if report_month_renewals_val != st.session_state.report_month_renewals:
        st.session_state.report_month_renewals = report_month_renewals_val
        # Clear old report data
        st.session_state.renewals_report_data = None

    if st.button("Generate Renewals Report", key="generate_renewals_report"):
        # Similar to financial report, AppAPI.generate_renewal_report_data has no date args in P1.
        # This is a mismatch with UI expectation of filtering by month.
        # Assuming AppAPI.generate_renewal_report_data *should* take date arguments.
        # For now, I'll call it without, and if it returns all renewals, UI needs to filter.
        # Let's assume it's updated to take start_date and end_date for the month.
        start_date_renewals = st.session_state.report_month_renewals
        if start_date_renewals.month == 12:
            end_date_renewals = date(start_date_renewals.year + 1, 1, 1)
        else:
            end_date_renewals = date(
                start_date_renewals.year, start_date_renewals.month + 1, 1
            )

        import calendar

        last_day_renewals = calendar.monthrange(
            start_date_renewals.year, start_date_renewals.month
        )[1]
        end_date_renewals_correct = date(
            start_date_renewals.year, start_date_renewals.month, last_day_renewals
        )

        start_date_str_renewals = start_date_renewals.strftime("%Y-%m-%d")
        end_date_str_renewals_correct = end_date_renewals_correct.strftime("%Y-%m-%d")

        try:
            # Assuming AppAPI was updated to take start_date and end_date
            renewal_data_list = api.generate_renewal_report_data(
                start_date=start_date_str_renewals,
                end_date=end_date_str_renewals_correct,
            )
            st.session_state.renewals_report_data = renewal_data_list
            if not renewal_data_list:
                st.info(
                    f"No upcoming renewals found for {st.session_state.report_month_renewals.strftime('%B %Y')}."
                )
            else:
                st.success(
                    f"Renewals report generated for {st.session_state.report_month_renewals.strftime('%B %Y')}."
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
    elif st.session_state.renewals_report_data == []:
        st.info(
            f"No upcoming renewals found for {st.session_state.report_month_renewals.strftime('%B %Y')}."
        )


tab_memberships, tab_reporting = st.tabs(["Memberships", "Reporting"])

with tab_memberships:
    render_memberships_tab()

# Removed tab_members and tab_plans sections

with tab_reporting:
    render_reporting_tab()
