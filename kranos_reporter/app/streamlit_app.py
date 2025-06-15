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
    """Fetches active plans from the API for selection."""
    url = f"{API_BASE_URL}/plans/list"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json() # Expected: list of {"id": plan_id, "name": plan_name}
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching plans: {e}")
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


def display_reporting_tab():
    """Displays the Reporting Tab content."""
    st.header("Reporting")
    st.subheader("Renewal Report")

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

def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="Kranos MMA Reporter", layout="wide")
    st.title("Kranos MMA Reporter")

    # Placeholder for tab navigation - focusing on Reporting for now
    # tab_titles = ["Members", "Plans", "Transactions", "Reporting", "Settings"]
    # selected_tab = st.sidebar.radio("Navigation", tab_titles, index=3) # Default to Reporting

    # For now, directly display the reporting content.
    # When other tabs are implemented, this structure will change.
    # if selected_tab == "Reporting":
    #     display_reporting_tab()
    # elif selected_tab == "Members":
    #     st.write("Members section (To be implemented)")
    # # etc. for other tabs

    # Directly calling the reporting tab function for this subtask
    # display_reporting_tab() # Comment out for now to focus on plans

    # You could add other sections/tabs here as they are developed.
    # For example:
    # st.header("Members Management")
    # st.write("Content for members management will go here.")
    # st.header("Settings")
    # st.write("App settings will go here.")

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

        with st.form("add_edit_plan_form", clear_on_submit=False): # Keep clear_on_submit False for manual reset
            name = st.text_input("Plan Name", key="plan_name_input")
            price = st.number_input("Price (INR)", min_value=0.0, step=0.01, format="%.2f", key="plan_price_input")
            duration_days = st.number_input("Duration (Days)", min_value=1, step=1, key="plan_duration_input")
            # Define plan types - these could be dynamic or from config
            plan_types = ["GC", "PT", "Open Mat", "Other"]
            plan_type = st.selectbox("Plan Type", options=plan_types, key="plan_type_input")
            is_active = st.checkbox("Is Active", key="plan_is_active_input")

            submitted = st.form_submit_button("Save Plan")
            if submitted:
                if not name: # Basic validation
                    st.error("Plan Name cannot be empty.")
                elif price < 0: # price is float, so check against 0.0
                    st.error("Price cannot be negative.")
                elif duration_days <= 0:
                    st.error("Duration must be a positive number of days.")
                else:
                    payload = {
                        "name": name,
                        "price": price,
                        "duration_days": duration_days,
                        "type": plan_type,
                        "is_active": is_active
                    }
                    url = f"{API_BASE_URL}/plans"
                    try:
                        # Assuming this is primarily for adding new plans for now.
                        # Edit would require a plan_id and likely a PUT request or different endpoint.
                        response = requests.post(url, json=payload, timeout=10)
                        response.raise_for_status()
                        response_data = response.json()
                        st.success(f"Plan '{name}' saved successfully! Plan ID: {response_data.get('plan_id')}")

                        # Clear form fields after successful submission by resetting their session state keys
                        st.session_state.plan_name_input = ""
                        st.session_state.plan_price_input = 0.0
                        st.session_state.plan_duration_input = 30
                        st.session_state.plan_type_input = "GC"
                        st.session_state.plan_is_active_input = True
                        st.rerun() # Rerun to reflect cleared fields
                    except requests.exceptions.HTTPError as http_err:
                        try:
                            error_detail = response.json().get("error", str(http_err))
                        except ValueError:
                            error_detail = response.text if response.text else str(http_err)
                        st.error(f"Error saving plan: {error_detail}")
                    except requests.exceptions.ConnectionError:
                        st.error(f"Connection error: Could not connect to the API at {url}.")
                    except requests.exceptions.Timeout:
                        st.error(f"Timeout error: The request to {url} timed out.")
                    except requests.exceptions.RequestException as req_err:
                        st.error(f"Request error: {req_err}")
                    except ValueError as json_err: # Catch JSON decoding errors
                        st.error(f"JSON decode error: Could not parse API response. {json_err}")

        # Clear button outside the form
        if st.button("Clear Form"):
            st.session_state.plan_name_input = ""
            st.session_state.plan_price_input = 0.0
            st.session_state.plan_duration_input = 30
            st.session_state.plan_type_input = "GC"
            st.session_state.plan_is_active_input = True
            st.rerun() # Rerun to reflect cleared fields

    with col2:
        st.subheader("Existing Plans")
        # List of existing plans will go here (as per a future task)
        st.write("Display of existing plans will be implemented here.")


def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="Kranos MMA Reporter", layout="wide")
    st.title("Kranos MMA Reporter")

    tab_titles = ["Memberships", "Members", "Plans", "Reporting"] # Added "Memberships"
    # Default to "Memberships" for now, can be changed later
    try:
        default_index = tab_titles.index("Plans") # Default to Plans for this task
    except ValueError:
        default_index = 0
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
                    except ValueError:
                        error_detail = response.text if response.text else str(http_err)
                    st.error(f"Error adding plan: {error_detail}")
                except requests.exceptions.ConnectionError:
                    st.error(f"Connection error: Could not connect to the API at {url}.")
                except requests.exceptions.Timeout:
                    st.error(f"Timeout error: The request to {url} timed out.")
                except requests.exceptions.RequestException as req_err:
                    st.error(f"Request error: {req_err}")
                except ValueError as json_err: # Catch JSON decoding errors
                    st.error(f"JSON decode error: Could not parse API response. {json_err}")

    with col2:
        st.subheader("Existing Plans")
        # List of existing plans will go here (as per a future task)
        st.write("Display of existing plans will be implemented here.")


def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="Kranos MMA Reporter", layout="wide")
    st.title("Kranos MMA Reporter")

    tab_titles = ["Memberships", "Members", "Plans", "Reporting"] # Added "Memberships"
    # Default to "Memberships" for now, can be changed later
    try:
        default_index = tab_titles.index("Memberships") # Default to Memberships
    except ValueError:
        default_index = 0
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
            except ValueError: # If response is not JSON
                error_detail = response.text if response.text else str(http_err)
            st.error(f"Error closing books: {error_detail}")
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to API: {e}")
        except ValueError as json_err: # Catch JSON decoding errors
            st.error(f"Error parsing API response: {json_err}")


def display_members_tab():
    """Displays the Members Tab content."""
    st.header("Manage Members")

    # As per project plan, two-column layout
    col1, col2 = st.columns(2)

    # --- Initialize Session State for Form Fields (if not already present) ---
    if 'editing_member_id' not in st.session_state:
        st.session_state.editing_member_id = None
    if 'member_name_input' not in st.session_state:
        st.session_state.member_name_input = ""
    if 'member_email_input' not in st.session_state:
        st.session_state.member_email_input = ""
    if 'member_phone_input' not in st.session_state:
        st.session_state.member_phone_input = ""
    if 'member_join_date_input' not in st.session_state:
        st.session_state.member_join_date_input = datetime.now().date()
    if 'member_plan_selection' not in st.session_state:
        st.session_state.member_plan_selection = None # Will store plan_id
    if 'member_is_active_checkbox' not in st.session_state:
        st.session_state.member_is_active_checkbox = True
    if 'all_plans_list' not in st.session_state: # Cache plans list
        st.session_state.all_plans_list = fetch_active_plans()


    with col1:
        st.subheader("Add/Edit Member")
        form_title = "Edit Member" if st.session_state.editing_member_id else "Add New Member"
        st.markdown(f"**{form_title}**")

        st.text_input("Name:", key="member_name_input")
        st.text_input("Email:", key="member_email_input")
        st.text_input("Phone:", key="member_phone_input")
        st.date_input("Join Date:", key="member_join_date_input")

        # Plan selection
        plans_options = {plan['id']: plan['name'] for plan in st.session_state.all_plans_list}
        st.selectbox(
            "Plan:",
            options=list(plans_options.keys()),
            format_func=lambda plan_id: plans_options.get(plan_id, "Select Plan"),
            key="member_plan_selection"
        )

        st.checkbox("Is Active", key="member_is_active_checkbox")

        form_col1, form_col2 = st.columns(2)
        if form_col1.button("Save", type="primary"):
            if st.session_state.editing_member_id:
                st.toast(f"Save clicked for editing member {st.session_state.editing_member_id}") # Placeholder
                # Actual save logic for update will be here
            else:
                st.toast("Save clicked for new member") # Placeholder
                # Actual save logic for add will be here
            # For now, we don't clear the form on save.

        if form_col2.button("Clear"):
            st.session_state.editing_member_id = None
            st.session_state.member_name_input = ""
            st.session_state.member_email_input = ""
            st.session_state.member_phone_input = ""
            st.session_state.member_join_date_input = datetime.now().date()
            st.session_state.member_plan_selection = None
            st.session_state.member_is_active_checkbox = True
            st.rerun()


    with col2:
        st.subheader("Members List & Filters")

        # Filter widgets
        st.text_input("Search Member", key="member_search")
        st.selectbox("Plan Type", ["All", "GC", "PT"], key="member_plan_type_filter")
        st.selectbox("Status", ["All", "Active", "Inactive"], key="member_status_filter")

        # Fetch and display filtered members
        search_term = st.session_state.member_search
        plan_type_filter = st.session_state.member_plan_type_filter
        status_filter = st.session_state.member_status_filter

        params = {}
        if search_term:
            params['search_term'] = search_term
        if plan_type_filter and plan_type_filter != "All":
            params['plan_type'] = plan_type_filter
        if status_filter and status_filter != "All":
            params['status'] = status_filter

        api_url = f"{API_BASE_URL}/members/filtered/"

        try:
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

            members_data = response.json()

            if members_data:
                df_members = pd.DataFrame(members_data)
                if not df_members.empty:
                    # Define columns for the header
                    header_cols = st.columns([3, 2, 1, 1, 1, 1]) # Adjust ratios as needed
                    header_cols[0].write("**Name**")
                    header_cols[1].write("**Plan**")
                    header_cols[2].write("**Status**")
                    header_cols[3].write("**Actions**") # Placeholder for action buttons header

                    for index, row in df_members.iterrows():
                        member_id = row["member_id"]
                        cols = st.columns([3, 2, 1, 1, 1, 1]) # Name, Plan, Status, History, Edit, Delete

                        cols[0].write(row.get("member_name", "N/A"))
                        cols[1].write(row.get("plan_name", "N/A"))
                        cols[2].write("Active" if row.get("is_active") else "Inactive")

                        # Action buttons
                        if cols[3].button("History", key=f"history_{member_id}"):
                            # --- History Modal Logic ---
                            @st.dialog(f"Transaction History: {row.get('member_name', 'Member')}")
                            def show_history_modal(member_id_for_modal, member_name_for_modal):
                                st.subheader(f"Transactions for {member_name_for_modal}")
                                transactions_url = f"{API_BASE_URL}/member/{member_id_for_modal}/transactions"
                                try:
                                    response = requests.get(transactions_url, timeout=10)
                                    response.raise_for_status()
                                    transactions_data = response.json()

                                    if transactions_data:
                                        df_transactions = pd.DataFrame(transactions_data)
                                        # Ensure 'amount' column exists and is numeric for sum
                                        if 'amount' not in df_transactions.columns:
                                            df_transactions['amount'] = 0 # Add column if missing, or handle error

                                        # Convert 'amount' to numeric, coercing errors to NaN, then fill NaN with 0
                                        df_transactions['amount'] = pd.to_numeric(df_transactions['amount'], errors='coerce').fillna(0)

                                        st.dataframe(df_transactions[[
                                            'transaction_date', 'transaction_type', 'plan_name', 'amount',
                                            'payment_method', 'start_date', 'end_date'
                                        ]], hide_index=True) # hide_index for cleaner table

                                        total_paid = df_transactions['amount'].sum()
                                        st.metric("Total Amount Paid", f"₹{total_paid:,.2f}")
                                    else:
                                        st.info("No transaction history found for this member.")
                                except requests.exceptions.HTTPError as http_err:
                                    try:
                                        error_detail = response.json().get("error", str(http_err))
                                    except ValueError:
                                        error_detail = response.text if response.text else str(http_err)
                                    st.error(f"Error fetching history: {error_detail}")
                                except requests.exceptions.RequestException as e:
                                    st.error(f"Could not fetch transaction history: {e}")
                                except ValueError as json_err: # Catch JSON decoding errors
                                    st.error(f"Error parsing transaction data: {json_err}")

                                if st.button("Close"):
                                    st.rerun() # Close the dialog

                            show_history_modal(member_id, row.get("member_name", "Member"))
                            # --- End of History Modal Logic ---

                        if cols[4].button("Edit", key=f"edit_{member_id}"):
                            # Fetch member details and populate form
                            member_api_url = f"{API_BASE_URL}/member/{member_id}"
                            try:
                                response = requests.get(member_api_url, timeout=5)
                                response.raise_for_status()
                                member_data = response.json()

                                st.session_state.editing_member_id = member_data.get('member_id')
                                st.session_state.member_name_input = member_data.get('member_name', "")
                                st.session_state.member_email_input = member_data.get('email', "")
                                st.session_state.member_phone_input = member_data.get('phone', "")

                                join_date_str = member_data.get('join_date')
                                if join_date_str:
                                    try:
                                        st.session_state.member_join_date_input = datetime.strptime(join_date_str, '%Y-%m-%d').date()
                                    except ValueError: # Handle cases where date might be in other formats or malformed
                                        st.session_state.member_join_date_input = datetime.now().date()
                                        st.warning(f"Could not parse join date '{join_date_str}'. Please check.")
                                else:
                                    st.session_state.member_join_date_input = datetime.now().date()

                                st.session_state.member_plan_selection = member_data.get('current_plan_id')
                                st.session_state.member_is_active_checkbox = member_data.get('is_active', True)

                                # Refresh all_plans_list if it's empty (e.g. initial load error)
                                if not st.session_state.all_plans_list:
                                     st.session_state.all_plans_list = fetch_active_plans()
                                st.rerun() # Rerun to update the form fields in col1

                            except requests.exceptions.RequestException as e:
                                st.error(f"Error fetching member details: {e}")
                            except ValueError as e: # JSON decoding error
                                st.error(f"Error parsing member data: {e}")

                        if cols[5].button("Delete", key=f"delete_{member_id}"):
                            st.toast(f"Delete clicked for {member_id}") # Placeholder action
                        st.divider() # Visual separation between rows
                else:
                    st.info("No members found matching your criteria.")
            else: # This case handles if members_data itself is empty from the start
                st.info("No members found matching your criteria.")

        except requests.exceptions.HTTPError as http_err:
            try:
                error_detail = response.json().get("error", str(http_err))
            except ValueError: # If response is not JSON
                error_detail = response.text if response.text else str(http_err)
            st.error(f"Error fetching members: {error_detail}")
        except requests.exceptions.ConnectionError:
            st.error(f"Connection error: Could not connect to the API at {api_url}. Ensure the API is running.")
        except requests.exceptions.Timeout:
            st.error(f"Timeout error: The request to {api_url} timed out.")
        except requests.exceptions.RequestException as req_err:
            st.error(f"An error occurred while fetching members: {req_err}")
        except ValueError as json_err: # Catch JSON decoding errors
             st.error(f"Error parsing member data: {json_err}")


if __name__ == '__main__':
    main()
