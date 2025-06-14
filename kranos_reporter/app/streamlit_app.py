import streamlit as st
import requests
import pandas as pd
import os

# Define the base URL for the API
# Assumes the Flask API (api.py) is running locally on port 5000
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000/api")

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
    display_reporting_tab()

    # You could add other sections/tabs here as they are developed.
    # For example:
    # st.header("Members Management")
    # st.write("Content for members management will go here.")
    # st.header("Settings")
    # st.write("App settings will go here.")


if __name__ == '__main__':
    main()
