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

    st.subheader("Add New Plan")
    with st.form("add_plan_form"):
        plan_name = st.text_input("Plan Name", key="plan_name")
        plan_price = st.number_input("Price (INR)", min_value=0, step=1, key="plan_price")
        plan_duration_days = st.number_input("Duration (Days)", min_value=1, step=1, key="plan_duration")
        plan_type = st.selectbox("Plan Type", ["GC", "PT"], key="plan_type") # GC: Group Class, PT: Personal Training

        submitted = st.form_submit_button("Add Plan")
        if submitted:
            if not plan_name:
                st.error("Plan Name cannot be empty.")
            else:
                payload = {
                    "name": plan_name,
                    "price": plan_price,
                    "duration_days": plan_duration_days,
                    "type": plan_type
                }
                url = f"{API_BASE_URL}/plans"
                try:
                    response = requests.post(url, json=payload, timeout=10)
                    response.raise_for_status()
                    response_data = response.json()
                    st.success(f"Plan '{plan_name}' added successfully! Plan ID: {response_data.get('plan_id')}")
                    # Clear form by resetting session state for these keys
                    st.session_state.plan_name = ""
                    st.session_state.plan_price = 0
                    st.session_state.plan_duration = 1
                    st.session_state.plan_type = "GC" # Reset to default
                except requests.exceptions.HTTPError as http_err:
                    try:
                        error_detail = response.json().get("error", str(http_err))
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


def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="Kranos MMA Reporter", layout="wide")
    st.title("Kranos MMA Reporter")

    tab_titles = ["Reporting", "Plans", "Members"] # Add other tabs as needed
    # Default to "Plans" for now, can be changed later
    # Find default index for "Members" or set to 0 if not found
    try:
        default_index = tab_titles.index("Members")
    except ValueError:
        default_index = 0
    selected_tab = st.sidebar.radio("Navigation", tab_titles, index=default_index)

    if selected_tab == "Reporting":
        display_reporting_tab()
    elif selected_tab == "Plans":
        display_plans_tab()
    elif selected_tab == "Members":
        display_members_tab()
    # Add other tabs here


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
                            st.toast(f"History clicked for {member_id}") # Placeholder action

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
