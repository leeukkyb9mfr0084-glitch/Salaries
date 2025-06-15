import streamlit as st
import requests
import pandas as pd
import os
from datetime import datetime, date

# Define the base URL for the API
# Assumes the Flask API (api.py) is running locally on port 5000
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000/api")

# --- Helper function to fetch active plans ---
def fetch_active_plans():
    """Fetches active plans from the API for selection (typically id and name)."""
    url = f"{API_BASE_URL}/plans/list"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json() # Expected: list of {"id": plan_id, "name": plan_name}
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching active plans: {e}")
        return [] # Return empty list on error

# --- Helper function to fetch all plan details ---
def fetch_all_plans_details():
    """Fetches all plans with full details from the API."""
    url = f"{API_BASE_URL}/plans/all" # Hypothetical endpoint
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        # Expected: list of dicts with id, name, price, duration_days, type, is_active
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching all plan details: {e}")
        return [] # Return empty list on error

def fetch_renewal_report(days_ahead):
    """Fetches the renewal report from the API."""
    url = f"{API_BASE_URL}/reports/renewal?days_ahead={days_ahead}"
    try:
        response = requests.get(url, timeout=10) # Added timeout
        response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
        return response.json(), None
    except requests.exceptions.HTTPError as http_err:
        try:
            # Try to get a specific error message from API's JSON response
            error_detail = response.json().get("error", str(http_err))
        except ValueError: # If response is not JSON
            error_detail = response.text if response.text else str(http_err)
        return None, f"HTTP error: {error_detail}"
    except requests.exceptions.ConnectionError as conn_err:
        return None, f"Connection error: Could not connect to the API at {url}. Ensure the API is running."
    except requests.exceptions.Timeout as timeout_err:
        return None, f"Timeout error: The request to {url} timed out."
    except requests.exceptions.RequestException as req_err: # Catch any other requests error
        return None, f"Request error: {req_err}"
    except ValueError as json_err: # Catch JSON decoding errors
        return None, f"JSON decode error: Could not parse API response. {json_err}"

def fetch_monthly_report_data(month, year):
    """Fetches the monthly report data from the API."""
    url = f"{API_BASE_URL}/reports/monthly?month={month}&year={year}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.HTTPError as http_err:
        try:
            error_detail = response.json().get("error", str(http_err))
        except ValueError:
            error_detail = response.text if response.text else str(http_err)
        return None, f"HTTP error: {error_detail}"
    except requests.exceptions.ConnectionError as conn_err:
        return None, f"Connection error: Could not connect to the API at {url}. Ensure the API is running."
    except requests.exceptions.Timeout as timeout_err:
        return None, f"Timeout error: The request to {url} timed out."
    except requests.exceptions.RequestException as req_err:
        return None, f"Request error: {req_err}"
    except ValueError as json_err:
        return None, f"JSON decode error: Could not parse API response. {json_err}"

def display_reporting_tab():
    """Displays the Reporting Tab content."""
    st.header("Reporting")

    report_col1, report_col2 = st.columns(2)

    with report_col1:
        st.subheader("Monthly Report")

        # Month and Year selection
        current_time = datetime.now()
        month_names = [datetime(2000, m, 1).strftime('%B') for m in range(1, 13)]

        selected_month_name = st.selectbox(
            "Month:",
            options=month_names,
            index=current_time.month - 1,  # Default to current month
            key="monthly_report_month"
        )

        selected_year = st.number_input(
            "Year:",
            min_value=current_time.year - 10, # Allow 10 years back
            max_value=current_time.year + 5, # Allow 5 years ahead (for future planning if needed)
            value=current_time.year, # Default to current year
            step=1,
            key="monthly_report_year"
        )

        if st.button("Generate Monthly Report"):
            selected_month_number = month_names.index(selected_month_name) + 1
            with st.spinner(f"Fetching monthly report for {selected_month_name} {selected_year}..."):
                report_data, error = fetch_monthly_report_data(selected_month_number, selected_year)

            if error:
                st.error(error)
            elif report_data is not None:
                if not report_data:
                    st.info(f"No transactions found for {selected_month_name} {selected_year}.")
                else:
                    try:
                        df = pd.DataFrame(report_data)
                        st.dataframe(df)

                        if not df.empty:
                            csv = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="Download Monthly Report as CSV",
                                data=csv,
                                file_name=f"monthly_report_{selected_year}_{selected_month_name}.csv",
                                mime="text/csv",
                                key="download_monthly_report"
                            )
                    except Exception as e:
                        st.error(f"An error occurred while processing the monthly report data: {e}")
            else:
                st.error("An unknown error occurred while fetching the monthly report.")

    with report_col2:
        st.subheader("Upcoming Renewals") # Renamed from "Renewal Report"

        days_ahead = st.number_input(
            "Days Ahead for Renewal Report:",
            min_value=1,
            max_value=365,
            value=30,
            step=1,
            help="Enter the number of days (from today) to look for upcoming renewals."
        )

        if st.button("Generate Renewal Report"):
            with st.spinner(f"Fetching renewal report for the next {days_ahead} days..."):
                report_data, error = fetch_renewal_report(days_ahead)

            if error:
                st.error(error)
            elif report_data is not None: # report_data could be an empty list
                if not report_data: # Explicitly check if the list is empty
                    st.info("No members found for renewal in the specified period.")
                else:
                    try:
                        df = pd.DataFrame(report_data)
                        st.dataframe(df)

                        if not df.empty:
                            csv = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="Download Report as CSV",
                                data=csv,
                                file_name=f"renewal_report_{days_ahead}_days.csv",
                                mime="text/csv",
                            )
                    except Exception as e:
                        st.error(f"An error occurred while processing the report data: {e}")
            else:
                # This case should ideally be covered by error handling in fetch_renewal_report
                st.error("An unknown error occurred while fetching the report.")

# Ensure this is the only definition of display_plans_tab

def display_plans_tab():
    """Displays the Plans Tab content."""
    st.header("Manage Plans")

    col1, col2 = st.columns(2) # Or st.columns([1,2]) for different widths, 2 is fine for now

    with col1:
        st.subheader("Add/Edit Plan")

        # Initialize session state for form fields if not already present
        if 'plan_name_input' not in st.session_state:
            st.session_state.plan_name_input = ""
        if 'plan_price_input' not in st.session_state:
            st.session_state.plan_price_input = 0.0 # Use float for price
        if 'plan_duration_input' not in st.session_state:
            st.session_state.plan_duration_input = 30 # Default duration
        if 'plan_type_input' not in st.session_state:
            st.session_state.plan_type_input = "GC" # Default type
        if 'plan_is_active_input' not in st.session_state:
            st.session_state.plan_is_active_input = True
        if 'editing_plan_id' not in st.session_state:
            st.session_state.editing_plan_id = None

        form_title = "Edit Plan" if st.session_state.editing_plan_id else "Add New Plan"
        st.markdown(f"**{form_title}**")

        with st.form("add_edit_plan_form", clear_on_submit=False):
            name = st.text_input("Plan Name", value=st.session_state.plan_name_input, key="plan_name_setter")
            price = st.number_input("Price (INR)", min_value=0.0, value=st.session_state.plan_price_input, step=0.01, format="%.2f", key="plan_price_setter")
            duration_days = st.number_input("Duration (Days)", min_value=1, value=st.session_state.plan_duration_input, step=1, key="plan_duration_setter")
            plan_types = ["GC", "PT", "Open Mat", "Other"]
            # Find index of current plan_type_input for selectbox default
            try:
                current_type_index = plan_types.index(st.session_state.plan_type_input)
            except ValueError:
                current_type_index = 0 # Default to first item if not found
            plan_type = st.selectbox("Plan Type", options=plan_types, index=current_type_index, key="plan_type_setter")
            is_active = st.checkbox("Is Active", checked=st.session_state.plan_is_active_input, key="plan_is_active_setter")

            # Update session state from form inputs immediately for persistence across reruns if needed elsewhere
            st.session_state.plan_name_input = st.session_state.plan_name_setter
            st.session_state.plan_price_input = st.session_state.plan_price_setter
            st.session_state.plan_duration_input = st.session_state.plan_duration_setter
            st.session_state.plan_type_input = st.session_state.plan_type_setter
            st.session_state.plan_is_active_input = st.session_state.plan_is_active_setter

            save_button_text = "Update Plan" if st.session_state.editing_plan_id else "Save Plan"
            submitted = st.form_submit_button(save_button_text)

            if submitted:
                if not st.session_state.plan_name_input:
                    st.error("Plan Name cannot be empty.")
                elif st.session_state.plan_price_input < 0:
                    st.error("Price cannot be negative.")
                elif st.session_state.plan_duration_input <= 0:
                    st.error("Duration must be a positive number of days.")
                else:
                    payload = {
                        "name": st.session_state.plan_name_input,
                        "price": st.session_state.plan_price_input,
                        "duration_days": st.session_state.plan_duration_input,
                        "type": st.session_state.plan_type_input,
                        "is_active": st.session_state.plan_is_active_input
                    }
                    try:
                        if st.session_state.editing_plan_id:
                            url = f"{API_BASE_URL}/plans/{st.session_state.editing_plan_id}"
                            response = requests.put(url, json=payload, timeout=10)
                            success_message = f"Plan '{st.session_state.plan_name_input}' updated successfully!"
                        else:
                            url = f"{API_BASE_URL}/plans"
                            response = requests.post(url, json=payload, timeout=10)
                            success_message = f"Plan '{st.session_state.plan_name_input}' saved successfully! Plan ID: {response.json().get('plan_id', 'N/A')}"

                        response.raise_for_status()
                        st.success(success_message)

                        # Clear form and editing state
                        st.session_state.editing_plan_id = None
                        st.session_state.plan_name_input = ""
                        st.session_state.plan_price_input = 0.0
                        st.session_state.plan_duration_input = 30
                        st.session_state.plan_type_input = "GC"
                        st.session_state.plan_is_active_input = True
                        st.rerun()
                    except requests.exceptions.HTTPError as http_err:
                        try:
                            error_detail = response.json().get("error", str(http_err))
                        except ValueError:
                            error_detail = response.text if response.text else str(http_err)
                        st.error(f"Error saving plan: {error_detail}")
                    except requests.exceptions.ConnectionError:
                        st.error(f"Connection error: Could not connect to the API.")
                    except requests.exceptions.Timeout:
                        st.error(f"Timeout error: The request timed out.")
                    except requests.exceptions.RequestException as req_err:
                        st.error(f"Request error: {req_err}")
                    except ValueError as json_err:
                        st.error(f"JSON decode error: Could not parse API response. {json_err}")

        if st.button("Clear Form"):
            st.session_state.editing_plan_id = None
            st.session_state.plan_name_input = ""
            st.session_state.plan_price_input = 0.0
            st.session_state.plan_duration_input = 30
            st.session_state.plan_type_input = "GC"
            st.session_state.plan_is_active_input = True
            st.rerun()

    with col2:
        st.subheader("Existing Plans")
        all_plans = fetch_all_plans_details()

        if not all_plans:
            st.info("No plans found or unable to fetch plans. Please ensure the API is running and accessible.")
        else:
            for plan in all_plans:
                plan_id = plan.get("id", "N/A")
                with st.container(): # Use a container for each plan for better layout
                    st.markdown(f"**{plan.get('name', 'N/A')}**")
                    details_col1, details_col2 = st.columns(2)
                    with details_col1:
                        st.caption(f"ID: {plan_id}")
                        st.text(f"Price: ₹{plan.get('price', 0.0):.2f}")
                        st.text(f"Duration: {plan.get('duration_days', 0)} days")
                        st.text(f"Type: {plan.get('type', 'N/A')}")

                    with details_col2:
                        current_is_active = plan.get('is_active', False)
                        new_is_active = st.checkbox("Active", value=current_is_active, key=f"active_{plan_id}")
                        if new_is_active != current_is_active:
                            # API call to update status
                            try:
                                status_update_url = f"{API_BASE_URL}/plan/{plan_id}/status" # Hypothetical
                                response = requests.put(status_update_url, json={"is_active": new_is_active}, timeout=5)
                                response.raise_for_status()
                                st.success(f"Plan {plan.get('name')} status updated!")
                                # To reflect change immediately, we'd need to rerun or update `all_plans`
                                # For now, a success message and the checkbox will update visually on next full rerun
                                st.rerun()
                            except requests.exceptions.RequestException as e:
                                st.error(f"Failed to update status for plan {plan_id}: {e}")
                                # Revert checkbox optimistically if API call fails
                                # This requires more complex state handling or a rerun to fetch fresh state.
                                # For now, error is shown, user might need to retry or refresh.

                    action_col1, action_col2 = st.columns(2)
                    with action_col1:
                        if st.button("Edit", key=f"edit_{plan_id}"):
                            st.session_state.editing_plan_id = plan_id
                            st.session_state.plan_name_input = plan.get('name', "")
                            st.session_state.plan_price_input = plan.get('price', 0.0)
                            st.session_state.plan_duration_input = plan.get('duration_days', 30)
                            st.session_state.plan_type_input = plan.get('type', "GC")
                            st.session_state.plan_is_active_input = plan.get('is_active', True)
                            st.rerun() # Rerun to reflect changes in the form

                    with action_col2:
                        if st.button("Delete", key=f"delete_{plan_id}", type="secondary"):
                            # Confirmation for delete
                            # For now, just a toast. Ideally, a modal confirmation.
                            st.warning(f"Attempting to delete Plan ID: {plan_id} (API call pending).")
                            # delete_url = f"{API_BASE_URL}/plan/{plan_id}" # Hypothetical
                            # try:
                            #     response = requests.delete(delete_url, timeout=5)
                            #     response.raise_for_status()
                            #     st.success(f"Plan {plan.get('name')} deleted successfully!")
                            #     st.rerun()
                            # except requests.exceptions.RequestException as e:
                            #     st.error(f"Failed to delete plan {plan_id}: {e}")
                    st.divider()


def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="Kranos MMA Reporter", layout="wide")
    st.title("Kranos MMA Reporter")

    tab_titles = ["Memberships", "Members", "Plans", "Reporting"] # Added "Memberships"
    # Default to "Memberships" for now, can be changed later
    try:
        default_index = tab_titles.index("Members") # Default to Members for Task 2.1
    except ValueError:
        default_index = 0 # Fallback if "Members" is not in the list
    selected_tab = st.sidebar.radio("Navigation", tab_titles, index=default_index)

    if selected_tab == "Memberships":
        display_memberships_tab()
    elif selected_tab == "Members":
        display_members_tab()
    elif selected_tab == "Plans":
        display_plans_tab()
    elif selected_tab == "Reporting":
        display_reporting_tab()
    # Add other tabs here

def display_memberships_tab():
    """Displays the Memberships Tab content."""
    st.header("Manage Memberships")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Add Membership")
        # Form for adding membership will go here (as per a future task)
        st.write("Form for adding new memberships will be implemented here.")

    with col2:
        st.subheader("Recent Transactions & Filters")

        # --- Initialize Session State for Filters (if not already present) ---
        if 'transactions_start_date' not in st.session_state:
            st.session_state.transactions_start_date = None # Or a default like date.today() - 30 days
        if 'transactions_end_date' not in st.session_state:
            st.session_state.transactions_end_date = None # Or a default like date.today()
        if 'transactions_member_search' not in st.session_state:
            st.session_state.transactions_member_search = ""
        if 'transactions_type_filter' not in st.session_state:
            # Assuming common transaction types. These might need to be fetched or configured.
            st.session_state.transactions_type_filter = "All"

        # --- Filter Widgets ---
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            st.date_input("From Date:", key="transactions_start_date")
            st.text_input("Search by Member Name:", key="transactions_member_search")
        with filter_col2:
            st.date_input("To Date:", key="transactions_end_date")
            # Define transaction types - these could be dynamic if needed
            transaction_types = ["All", "New Subscription", "Renewal", "Payment"] # Example types
            st.selectbox("Transaction Type:", options=transaction_types, key="transactions_type_filter")

        # --- Fetch and Display Filtered Transactions ---
        params = {}
        if st.session_state.transactions_start_date:
            params['start_date'] = st.session_state.transactions_start_date.strftime('%Y-%m-%d')
        if st.session_state.transactions_end_date:
            params['end_date'] = st.session_state.transactions_end_date.strftime('%Y-%m-%d')
        if st.session_state.transactions_member_search:
            params['member_name_search'] = st.session_state.transactions_member_search
        if st.session_state.transactions_type_filter and st.session_state.transactions_type_filter != "All":
            params['transaction_type'] = st.session_state.transactions_type_filter

        # A button to trigger search, or search on change (st.rerun might be needed for on_change)
        # For simplicity, let's use a button or rely on Streamlit's auto-rerun for widgets.
        # Adding an explicit button can be better for performance with many filters.
        # if st.button("Search Transactions"): # Optional: Use a button to trigger search

        api_url = f"{API_BASE_URL}/transactions/filtered"
        try:
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            transactions_data = response.json()

            if transactions_data:
                df_transactions = pd.DataFrame(transactions_data)
                # Select and order columns for display
                display_cols = [
                    "member_name", "plan_name", "transaction_date", "amount",
                    "transaction_type", "payment_method",
                    "membership_start_date", "membership_end_date"
                ]
                # Filter df_transactions to only include columns that actually exist in it
                existing_display_cols = [col for col in display_cols if col in df_transactions.columns]
                st.dataframe(df_transactions[existing_display_cols], hide_index=True)
            else:
                st.info("No transactions found matching your criteria.")

        except requests.exceptions.HTTPError as http_err:
            try:
                error_detail = response.json().get("error", str(http_err))
            except ValueError:
                error_detail = response.text if response.text else str(http_err)
            st.error(f"Error fetching transactions: {error_detail}")
        except requests.exceptions.ConnectionError:
            st.error(f"Connection error: Could not connect to the API at {api_url}.")
        except requests.exceptions.Timeout:
            st.error(f"Timeout error: The request to {api_url} timed out.")
        except requests.exceptions.RequestException as req_err:
            st.error(f"An error occurred while fetching transactions: {req_err}")
        except ValueError as json_err: # Catch JSON decoding errors
            st.error(f"Error parsing transaction data: {json_err}")

    # --- Close Books for Month Section ---
    st.divider() # Visual separator
    st.subheader("Close Books for Month")

    # Get current year and month for defaults
    current_year = datetime.now().year
    current_month = datetime.now().month

    # Month selection - list of month names
    month_names = [datetime(2000, m, 1).strftime('%B') for m in range(1, 13)] # January to December
    # Default to previous month, or December if current month is January
    default_month_index = (current_month - 2) if current_month > 1 else 11

    selected_month_name = st.selectbox(
        "Month:",
        options=month_names,
        index=default_month_index, # Default to previous month
        key="close_books_month"
    )
    # Convert month name back to month number (1-12)
    selected_month_number = month_names.index(selected_month_name) + 1

    selected_year = st.number_input(
        "Year:",
        min_value=current_year - 10, # Allow selecting back 10 years
        max_value=current_year,      # Max year is current year
        value=current_year if current_month > 1 else current_year -1, # Default to current year or previous if Jan
        step=1,
        key="close_books_year"
    )

    if st.button(f"Close Books for {selected_month_name} {selected_year}", type="primary"):
        payload = {
            "month": selected_month_number,
            "year": selected_year
        }
        close_books_url = f"{API_BASE_URL}/books/close"
        try:
            response = requests.post(close_books_url, json=payload, timeout=15) # Increased timeout for potentially long operation
            response.raise_for_status()
            response_data = response.json()
            st.success(response_data.get("message", "Books closed successfully!"))
        except requests.exceptions.HTTPError as http_err:
            try:
                error_detail = response.json().get("error", str(http_err))
            except ValueError:
                error_detail = response.text if response.text else str(http_err)
            st.error(f"Error closing books: {error_detail}")
        except requests.exceptions.ConnectionError as conn_err: # More specific
            st.error(f"Connection error: Could not connect to the API at {close_books_url}. Details: {conn_err}")
        except requests.exceptions.Timeout as timeout_err: # More specific
            st.error(f"Timeout error: The request to {close_books_url} timed out. Details: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            st.error(f"Request error: {req_err}")
        except ValueError as json_err:
            st.error(f"JSON decode error: Could not parse API response. {json_err}")

# Ensure this is the only definition of main()
def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="Kranos MMA Reporter", layout="wide")
    st.title("Kranos MMA Reporter")

    tab_titles = ["Memberships", "Members", "Plans", "Reporting"]
    # Default to "Memberships" for Task 2.2
    try:
        default_index = tab_titles.index("Memberships")
    except ValueError:
        default_index = 0 # Fallback
    selected_tab = st.sidebar.radio("Navigation", tab_titles, index=default_index)

    if selected_tab == "Memberships":
        display_memberships_tab()
    elif selected_tab == "Members":
        display_members_tab()
    elif selected_tab == "Plans":
        display_plans_tab()
    elif selected_tab == "Reporting":
        display_reporting_tab()

# Ensure this is the only definition of display_memberships_tab
def display_memberships_tab():
    """Displays the Memberships Tab content."""
    st.header("Manage Memberships")

    # Initialize session state variables for the Add Membership form
    if 'add_membership_member_id' not in st.session_state:
        st.session_state.add_membership_member_id = None
    if 'add_membership_plan_id' not in st.session_state:
        st.session_state.add_membership_plan_id = None
    if 'add_membership_amount_paid' not in st.session_state:
        st.session_state.add_membership_amount_paid = 0.0
    if 'add_membership_payment_method' not in st.session_state:
        st.session_state.add_membership_payment_method = "Cash"
    if 'add_membership_payment_date' not in st.session_state:
        st.session_state.add_membership_payment_date = date.today()
    if 'add_membership_start_date' not in st.session_state:
        st.session_state.add_membership_start_date = date.today()
    if 'add_membership_sessions' not in st.session_state: # For PT plans
        st.session_state.add_membership_sessions = None # Or an appropriate default like 10
    if 'add_membership_transaction_type' not in st.session_state:
        st.session_state.add_membership_transaction_type = "New Subscription"


    # Fetch members for selectbox
    if 'all_members_for_selectbox' not in st.session_state:
        try:
            # Using the existing filtered members endpoint without filters to get all
            response = requests.get(f"{API_BASE_URL}/members/filtered/", timeout=5)
            response.raise_for_status()
            members_list_data = response.json()
            # Assuming members_list_data is a list of dicts with 'member_id' and 'client_name'
            st.session_state.all_members_for_selectbox = {member['member_id']: member['client_name'] for member in members_list_data}
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching members for selection: {e}")
            st.session_state.all_members_for_selectbox = {}
        except (KeyError, TypeError) as e:
            st.error(f"Error processing member data for selection: {e}")
            st.session_state.all_members_for_selectbox = {}


    # Fetch active plans for selectbox (uses existing helper)
    if 'active_plans_for_selectbox' not in st.session_state:
        plans_data = fetch_active_plans() # This returns list of dicts: {"id": plan_id, "name": plan_name}
        st.session_state.active_plans_for_selectbox = {plan['id']: plan['name'] for plan in plans_data}


    col1_add_membership, col2_transactions = st.columns(2)

    with col1_add_membership:
        st.subheader("Add Membership / Record Transaction")
        with st.form("add_membership_form", clear_on_submit=True):
            member_id = st.selectbox(
                "Select Member:",
                options=list(st.session_state.all_members_for_selectbox.keys()),
                format_func=lambda m_id: st.session_state.all_members_for_selectbox.get(m_id, "Unknown Member"),
                key="add_membership_member_id"
            )
            transaction_type = st.selectbox(
                "Transaction Type:",
                options=["New Subscription", "Renewal", "Personal Training Session(s)", "Other Payment"], # Example types
                key="add_membership_transaction_type"
            )
            plan_id = st.selectbox(
                "Select Plan (if applicable):",
                options=[None] + list(st.session_state.active_plans_for_selectbox.keys()), # Allow None
                format_func=lambda p_id: st.session_state.active_plans_for_selectbox.get(p_id, "N/A - No Plan / PT"),
                key="add_membership_plan_id"
            )
            amount_paid = st.number_input("Amount Paid (INR):", min_value=0.0, step=0.01, key="add_membership_amount_paid")
            payment_method_options = ["Cash", "Card", "Online", "Other"]
            payment_method = st.selectbox("Payment Method:", options=payment_method_options, key="add_membership_payment_method")
            payment_date = st.date_input("Payment Date:", key="add_membership_payment_date")
            start_date = st.date_input("Membership Start Date (if new/renewal):", key="add_membership_start_date")

            sessions = None
            if transaction_type == "Personal Training Session(s)":
                 sessions = st.number_input("Number of Sessions (for PT):", min_value=1, step=1, key="add_membership_sessions", value=10)


            submit_membership_button = st.form_submit_button("Save Membership Transaction")

            if submit_membership_button:
                if not member_id:
                    st.error("Please select a member.")
                elif transaction_type in ["New Subscription", "Renewal"] and not plan_id:
                    st.error("Please select a plan for new subscriptions or renewals.")
                else:
                    st.info("Adding membership/transaction is not yet available via the API.")
                    # TODO: Call API endpoint when available.
                    # payload = {
                    #     "member_id": member_id,
                    #     "transaction_type": transaction_type,
                    #     "plan_id": plan_id,
                    #     "amount_paid": amount_paid,
                    #     "payment_method": payment_method,
                    #     "payment_date": payment_date.isoformat(),
                    #     "start_date": start_date.isoformat(),
                    #     "sessions": sessions
                    # }
                    # add_transaction_url = f"{API_BASE_URL}/transactions" # Hypothetical
                    # try:
                    #     response = requests.post(add_transaction_url, json=payload, timeout=5)
                    #     response.raise_for_status()
                    #     st.success("Membership transaction recorded successfully!")
                    #     st.rerun()
                    # except requests.exceptions.RequestException as e:
                    #     st.error(f"Error recording transaction: {e}")


    with col2_transactions:
        st.subheader("Recent Transactions & Filters")
        # Filters (re-using structure from previous state of this tab)
        if 'transactions_start_date_filter' not in st.session_state: # Renamed keys for uniqueness
            st.session_state.transactions_start_date_filter = None
        if 'transactions_end_date_filter' not in st.session_state:
            st.session_state.transactions_end_date_filter = None
        if 'transactions_member_search_filter' not in st.session_state:
            st.session_state.transactions_member_search_filter = ""
        if 'transactions_type_filter_select' not in st.session_state:
            st.session_state.transactions_type_filter_select = "All"

        filter_col1_trans, filter_col2_trans = st.columns(2)
        with filter_col1_trans:
            st.date_input("From Date:", key="transactions_start_date_filter")
            st.text_input("Search by Member Name:", key="transactions_member_search_filter")
        with filter_col2_trans:
            st.date_input("To Date:", key="transactions_end_date_filter")
            transaction_filter_types = ["All", "New Subscription", "Renewal", "Personal Training Session(s)", "Other Payment"]
            st.selectbox("Transaction Type:", options=transaction_filter_types, key="transactions_type_filter_select")

        params_trans_list = {}
        if st.session_state.transactions_start_date_filter:
            params_trans_list['start_date'] = st.session_state.transactions_start_date_filter.strftime('%Y-%m-%d')
        if st.session_state.transactions_end_date_filter:
            params_trans_list['end_date'] = st.session_state.transactions_end_date_filter.strftime('%Y-%m-%d')
        if st.session_state.transactions_member_search_filter:
            params_trans_list['member_name_search'] = st.session_state.transactions_member_search_filter
        if st.session_state.transactions_type_filter_select and st.session_state.transactions_type_filter_select != "All":
            params_trans_list['transaction_type'] = st.session_state.transactions_type_filter_select

        api_url_trans_list = f"{API_BASE_URL}/transactions/filtered"
        try:
            response_trans_list = requests.get(api_url_trans_list, params=params_trans_list, timeout=10)
            response_trans_list.raise_for_status()
            transactions_data_list = response_trans_list.json()

            if transactions_data_list:
                df_transactions = pd.DataFrame(transactions_data_list)
                display_cols = ["member_name", "plan_name", "transaction_date", "amount", "transaction_type", "payment_method", "membership_start_date", "membership_end_date"]
                existing_display_cols = [col for col in display_cols if col in df_transactions.columns]
                st.dataframe(df_transactions[existing_display_cols], hide_index=True)
            else:
                st.info("No transactions found matching your criteria.")
        except requests.exceptions.HTTPError as http_err:
            error_detail = response_trans_list.json().get("error", str(http_err)) if response_trans_list else str(http_err)
            st.error(f"Error fetching transactions: {error_detail}")
        except requests.exceptions.ConnectionError:
            st.error(f"Connection error when fetching transactions.")
        except requests.exceptions.Timeout:
            st.error(f"Timeout error when fetching transactions.")
        except requests.exceptions.RequestException as req_err:
            st.error(f"An error occurred while fetching transactions: {req_err}")
        except ValueError as json_err:
            st.error(f"Error parsing transaction data: {json_err}")

    # Close Books for Month Section (remains at the bottom, outside columns)
    st.divider()
    st.subheader("Close Books for Month")
    # Using existing session state keys as this section was mostly functional
    current_year_cb = datetime.now().year
    current_month_cb = datetime.now().month
    month_names_cb = [datetime(2000, m, 1).strftime('%B') for m in range(1, 13)]
    default_month_index_cb = (current_month_cb - 2) if current_month_cb > 1 else 11

    selected_month_name_cb = st.selectbox(
        "Month:", options=month_names_cb, index=default_month_index_cb, key="close_books_month_select"
    )
    selected_month_number_cb = month_names_cb.index(selected_month_name_cb) + 1

    selected_year_cb = st.number_input(
        "Year:", min_value=current_year_cb - 10, max_value=current_year_cb,
        value=current_year_cb if current_month_cb > 1 else current_year_cb -1, step=1, key="close_books_year_input"
    )

    if st.button(f"Close Books for {selected_month_name_cb} {selected_year_cb}", type="primary", key="close_books_button"):
        payload_cb = {"month": selected_month_number_cb, "year": selected_year_cb}
        close_books_api_url = f"{API_BASE_URL}/books/close"
        try:
            response_cb = requests.post(close_books_api_url, json=payload_cb, timeout=15)
            response_cb.raise_for_status()
            response_data_cb = response_cb.json()
            st.success(response_data_cb.get("message", "Books closed successfully!"))
        except requests.exceptions.HTTPError as http_err:
            error_detail = response_cb.json().get("error", str(http_err)) if response_cb else str(http_err)
            st.error(f"Error closing books: {error_detail}")
        except requests.exceptions.ConnectionError as e:
            st.error(f"Failed to connect to API to close books: {e}")
        except requests.exceptions.Timeout as e:
             st.error(f"Timeout closing books: {e}")
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to close books: {e}")
        except ValueError as json_err:
            st.error(f"Error parsing API response for closing books: {json_err}")

# Ensure this is the only definition of display_members_tab
def display_members_tab():
    """Displays the Members Tab content."""
    st.header("Manage Members")

    col1_members_form, col2_members_list = st.columns(2) # Unique column names

    # Initialize session state keys if they don't exist
    if 'editing_member_id' not in st.session_state:
        st.session_state.editing_member_id = None
    if 'member_name_form_input' not in st.session_state:
        st.session_state.member_name_form_input = ""
    if 'member_email_form_input' not in st.session_state: # Assuming email is a field to add
        st.session_state.member_email_form_input = ""
    if 'member_phone_form_input' not in st.session_state:
        st.session_state.member_phone_form_input = ""
    if 'member_join_date_form_input' not in st.session_state:
        st.session_state.member_join_date_form_input = date.today() # Use date object
    if 'member_plan_selection_form' not in st.session_state:
         st.session_state.member_plan_selection_form = None
    if 'member_is_active_form_checkbox' not in st.session_state:
        st.session_state.member_is_active_form_checkbox = True
    if 'show_history_modal_member_id' not in st.session_state:
        st.session_state.show_history_modal_member_id = None
    if 'member_history_data' not in st.session_state:
        st.session_state.member_history_data = None
    if 'member_history_error' not in st.session_state:
        st.session_state.member_history_error = None

    # Fetch plans once
    if 'all_plans_for_members_tab' not in st.session_state:
        st.session_state.all_plans_for_members_tab = fetch_active_plans()

    active_plans_options = {plan['id']: plan['name'] for plan in st.session_state.all_plans_for_members_tab}
    active_plans_options_with_none = {None: "N/A (No Plan)"}
    active_plans_options_with_none.update(active_plans_options)


    with col1_members_form:
        st.subheader("Add/Edit Member")

        # If editing_member_id is set, fetch and prefill form
        if st.session_state.editing_member_id and not st.session_state.get(f"member_form_prefilled_{st.session_state.editing_member_id}", False):
            try:
                member_details_url = f"{API_BASE_URL}/member/{st.session_state.editing_member_id}"
                response = requests.get(member_details_url, timeout=5)
                response.raise_for_status()
                member_data = response.json()

                st.session_state.member_name_form_input = member_data.get("client_name", "")
                st.session_state.member_email_form_input = member_data.get("email", "") # Assuming 'email' field
                st.session_state.member_phone_form_input = member_data.get("phone", "")
                join_date_str = member_data.get("join_date")
                if join_date_str:
                    st.session_state.member_join_date_form_input = datetime.strptime(join_date_str, '%Y-%m-%d').date()
                else:
                    st.session_state.member_join_date_form_input = date.today()
                st.session_state.member_plan_selection_form = member_data.get("current_plan_id", None) # Assuming this field
                st.session_state.member_is_active_form_checkbox = bool(member_data.get("is_active", True))
                st.session_state[f"member_form_prefilled_{st.session_state.editing_member_id}"] = True # Mark as prefilled
            except requests.exceptions.RequestException as e:
                st.error(f"Error fetching member details: {e}")
            except ValueError as e: # Handles JSON parsing errors or date parsing errors
                st.error(f"Error parsing member data: {e}")


        form_title = "Edit Member" if st.session_state.editing_member_id else "Add New Member"
        st.markdown(f"**{form_title}**")

        with st.form("member_form", clear_on_submit=False):
            name = st.text_input("Name:", value=st.session_state.member_name_form_input, key="member_name_widget")
            email = st.text_input("Email:", value=st.session_state.member_email_form_input, key="member_email_widget")
            phone = st.text_input("Phone:", value=st.session_state.member_phone_form_input, key="member_phone_widget")
            join_date_val = st.date_input("Join Date:", value=st.session_state.member_join_date_form_input, key="member_join_date_widget")

            selected_plan_id = st.selectbox(
                "Plan:",
                options=list(active_plans_options_with_none.keys()),
                format_func=lambda plan_id_key: active_plans_options_with_none.get(plan_id_key, "Select Plan"),
                index = list(active_plans_options_with_none.keys()).index(st.session_state.member_plan_selection_form) if st.session_state.member_plan_selection_form in active_plans_options_with_none else 0,
                key="member_plan_widget"
            )
            is_active = st.checkbox("Is Active", checked=st.session_state.member_is_active_form_checkbox, key="member_is_active_widget")

            submitted = st.form_submit_button("Save Member")
            if submitted:
                # Update session state from widgets before processing
                st.session_state.member_name_form_input = name
                st.session_state.member_email_form_input = email
                st.session_state.member_phone_form_input = phone
                st.session_state.member_join_date_form_input = join_date_val
                st.session_state.member_plan_selection_form = selected_plan_id
                st.session_state.member_is_active_form_checkbox = is_active

                if not name or not phone:
                    st.error("Name and Phone are required.")
                else:
                    member_payload = {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "join_date": join_date_val.isoformat(),
                        "plan_id": selected_plan_id if selected_plan_id else None, # API might expect null not 0 for no plan
                        "is_active": is_active
                    }

                    if st.session_state.editing_member_id:
                        st.info("Update functionality is not yet available via the API.")
                        # member_update_url = f"{API_BASE_URL}/member/{st.session_state.editing_member_id}"
                        # try:
                        #     response = requests.put(member_update_url, json=member_payload, timeout=5)
                        #     response.raise_for_status()
                        #     st.success("Member updated successfully!")
                        #     st.session_state.editing_member_id = None # Clear editing state
                        #     st.session_state[f"member_form_prefilled_{st.session_state.editing_member_id}"] = False # Reset prefill flag
                        #     st.rerun()
                        # except requests.exceptions.RequestException as e:
                        #     st.error(f"Error updating member: {e}")
                    else:
                        member_add_url = f"{API_BASE_URL}/members" # Assuming this is the add member endpoint
                        try:
                            response = requests.post(member_add_url, json=member_payload, timeout=5)
                            response.raise_for_status()
                            st.success("Member added successfully!")
                            # st.rerun() # Rerun to clear form and refresh list
                        except requests.exceptions.RequestException as e:
                            st.error(f"Error adding member: {e}")
                        # Fallback for missing add member endpoint
                        st.info("Adding members is not yet available via the API.")

        if st.button("Clear Form", key="clear_member_form_button_main"):
            if st.session_state.editing_member_id: # Clear prefill flag if was editing
                 st.session_state[f"member_form_prefilled_{st.session_state.editing_member_id}"] = False
            st.session_state.editing_member_id = None
            if st.session_state.editing_member_id: # Clear prefill flag if was editing
                 st.session_state[f"member_form_prefilled_{st.session_state.editing_member_id}"] = False
            st.session_state.member_name_form_input = ""
            st.session_state.member_email_form_input = ""
            st.session_state.member_phone_form_input = ""
            st.session_state.member_join_date_form_input = date.today()
            st.session_state.member_plan_selection_form = None
            st.session_state.member_is_active_form_checkbox = True
            st.rerun()

    with col2_members_list:
        st.subheader("Members List & Filters")
        search_term = st.text_input("Search Member by Name/Phone:", key="member_search_list_input_main")

        # Filters - simplified for now
        status_filter = st.selectbox("Filter by Status:", ["All", "Active", "Inactive"], key="member_status_filter_select_main")

        # Fetch members based on filters
        members_url = f"{API_BASE_URL}/members/filtered/"
        params = {}
        if search_term:
            params['search_term'] = search_term
        if status_filter != "All":
            params['status'] = status_filter

        try:
            response = requests.get(members_url, params=params, timeout=5)
            response.raise_for_status()
            members_data = response.json()

            if members_data:
                df_members = pd.DataFrame(members_data)
                # Ensure all expected columns are present, fill with default if not
                expected_cols = ["member_id", "client_name", "phone", "email", "join_date", "plan_name", "status"]
                for col in expected_cols:
                    if col not in df_members.columns:
                        df_members[col] = "N/A"

                # Display members in a more structured way
                for index, member in df_members.iterrows():
                    member_id = member["member_id"]
                    with st.container():
                        st.markdown(f"**{member['client_name']}** (ID: {member_id})")
                        sub_col1, sub_col2 = st.columns([3, 1])
                        with sub_col1:
                            st.caption(f"Phone: {member['phone']} | Email: {member.get('email', 'N/A')}")
                            st.caption(f"Joined: {member['join_date']} | Plan: {member.get('plan_name', 'N/A')} | Status: {member['status']}")

                        action_cols = sub_col2.columns(3)
                        if action_cols[0].button("Edit", key=f"edit_member_{member_id}"):
                            st.session_state.editing_member_id = member_id
                            st.session_state[f"member_form_prefilled_{member_id}"] = False # Trigger prefill
                            st.rerun()

                        if action_cols[1].button("Delete", key=f"delete_member_{member_id}"):
                            st.info(f"Delete for member {member_id} clicked. (API call not implemented yet)")
                            # delete_url = f"{API_BASE_URL}/member/{member_id}/deactivate"
                            # try:
                            #     del_response = requests.put(delete_url) # Or POST, depending on API design
                            #     del_response.raise_for_status()
                            #     st.success(f"Member {member_id} deactivated.")
                            #     st.rerun()
                            # except Exception as e:
                            #     st.error(f"Could not deactivate member {member_id}: {e}")

                        if action_cols[2].button("History", key=f"history_member_{member_id}"):
                            st.session_state.show_history_modal_member_id = member_id
                            # Fetch history data
                            try:
                                history_url = f"{API_BASE_URL}/member/{member_id}/transactions"
                                hist_response = requests.get(history_url, timeout=5)
                                hist_response.raise_for_status()
                                st.session_state.member_history_data = hist_response.json()
                                st.session_state.member_history_error = None
                            except requests.exceptions.RequestException as e:
                                st.session_state.member_history_data = None
                                st.session_state.member_history_error = f"Error fetching history: {e}"
                            except ValueError as e: # JSON parsing error
                                st.session_state.member_history_data = None
                                st.session_state.member_history_error = f"Error parsing history data: {e}"
                            st.rerun() # Rerun to show modal if data is ready
                        st.divider()
            else:
                st.info("No members found matching your criteria.")

        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching members: {e}")

    # Modal for Member History
    if st.session_state.show_history_modal_member_id:
        member_id_for_modal = st.session_state.show_history_modal_member_id
        # Attempt to find member name for modal title
        # This is a bit inefficient here, ideally member name would be passed or fetched cleanly
        member_name_for_modal = f"Member ID {member_id_for_modal}"
        # (If df_members is accessible here, could use it to find name)

        with st.container(): # Using st.container as a workaround for modal dialog behavior
            st.subheader(f"Transaction History for {member_name_for_modal}")
            if st.session_state.member_history_error:
                st.error(st.session_state.member_history_error)
            elif st.session_state.member_history_data:
                df_history = pd.DataFrame(st.session_state.member_history_data)
                if not df_history.empty:
                    st.dataframe(df_history)
                    total_paid = df_history["amount_paid"].sum() if "amount_paid" in df_history.columns else 0
                    st.metric("Total Amount Paid", f"₹{total_paid:.2f}")
                else:
                    st.info("No transaction history found for this member.")
            else:
                st.info("Loading history...") # Should have been fetched by button click already

            if st.button("Close History", key=f"close_history_{member_id_for_modal}"):
                st.session_state.show_history_modal_member_id = None
                st.session_state.member_history_data = None
                st.session_state.member_history_error = None
                st.rerun()

if __name__ == '__main__':
    main()
