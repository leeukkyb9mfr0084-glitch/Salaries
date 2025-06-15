import streamlit as st
from reporter.app_api import AppAPI
import sqlite3  # Added for database connection

# --- Database Connection ---
# It's crucial that the path to the database is correct.
# Assuming 'reporter/data/kranos_data.db' is the intended database.
# This path is relative to the root of the project where streamlit is run.
DB_PATH = "reporter/data/kranos_data.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    # You might want to configure the connection further, e.g., row_factory
    # conn.row_factory = sqlite3.Row # Example: For dict-like row access
    return conn


# Initialize the API with a database connection
# A new connection will be created for each session/run, which is generally fine for Streamlit.
# For more complex scenarios, connection pooling or caching might be considered.
api = AppAPI(get_db_connection())  # Example if kept


# --- Tab Rendering Functions ---
def render_memberships_tab():
    st.header("Memberships Management")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Add New Membership")

        # Fetch data for selectboxes
        members = (
            api.get_all_members()
        )  # Assuming this returns list of dicts with 'id' and 'name'
        active_plans = (
            api.get_active_plans()
        )  # Assuming this returns list of dicts with 'id', 'name', 'price'

        if not members:
            st.warning("No members found. Please add members first.")
            return  # Or disable form elements

        if not active_plans:
            st.warning("No active plans found. Please add active plans first.")
            return  # Or disable form elements

        member_options = {member["id"]: member["name"] for member in members}
        plan_options = {
            plan["id"]: f"{plan['name']} (${plan['price']})" for plan in active_plans
        }

        with st.form("add_membership_form"):
            selected_member_id = st.selectbox(
                "Select Member",
                options=list(member_options.keys()),
                format_func=lambda x: member_options[x],
            )
            selected_plan_id = st.selectbox(
                "Select Plan",
                options=list(plan_options.keys()),
                format_func=lambda x: plan_options[x],
            )

            # Display selected plan's price (read-only for now)
            # This requires fetching the plan details again or having price in plan_options value if not too complex
            # For simplicity, let's assume plan_options format_func shows price, and we can retrieve it if needed.
            # Or, fetch all plan details to easily access price.
            selected_plan_details = next(
                (plan for plan in active_plans if plan["id"] == selected_plan_id), None
            )
            if selected_plan_details:
                st.write(f"Selected Plan Price: ${selected_plan_details['price']:.2f}")

            start_date = st.date_input("Membership Start Date")
            # Custom price input (optional, depending on requirements)
            # custom_price = st.number_input("Enter Price (optional, overrides plan price)", value=0.0, step=0.01)

            submit_button = st.form_submit_button("Save Membership")

            if submit_button:
                # Actual saving logic will be implemented later
                # For now, just show a success message
                st.success(
                    f"Membership for {member_options[selected_member_id]} with plan {plan_options[selected_plan_id]} starting {start_date} "
                    f"(price from plan) - Save action pending."
                )
                # Example: api.add_membership(selected_member_id, selected_plan_id, start_date, price_to_use)

    with col2:
        st.subheader("Right Column")
        st.write("This is the right column for the Memberships tab.")
        # Future content for recent transactions list and filters will go here.


def render_members_tab():
    st.header("Member Management")
    # Placeholder content
    # st.write("Content for member management will go here.") # Original placeholder

    col1, col2 = st.columns(2)
    with col1:
        st.header("Add/Edit Member")
        # st.write("Form will go here.") # Original placeholder
        with st.form(key="member_form"):
            st.text_input("Name")
            st.date_input("Join Date")  # Consider default value: datetime.date.today()
            st.text_input("Phone")
            st.selectbox("Status", options=["active", "inactive"])

            # Buttons
            # As per subtask: two st.form_submit_button, acknowledging both will submit.
            # Handling distinct "Clear" logic is a future step if required.
            submit_button = st.form_submit_button("Save")
            clear_button = st.form_submit_button("Clear")

            if submit_button:
                # Logic for saving will go here in a future task
                st.success("Save button pressed (logic not implemented).")
            if clear_button:
                # Logic for clearing will go here / or this button might be changed
                st.info("Clear button pressed (logic not implemented).")

    with col2:
        st.header("View Members")
        # Fetch and display members
        members_data = api.get_all_members()
        if members_data:
            # Display members with action buttons
            for member in members_data:
                member_id = member.get("id", "N/A")  # Assuming member is a dict
                member_name = member.get("name", "N/A")

                cols = st.columns([3, 1, 1, 1])  # Adjust column ratios as needed
                cols[0].write(f"ID: {member_id}, Name: {member_name}")

                # Placeholder for Edit button
                if cols[1].button("Edit", key=f"edit_{member_id}"):
                    st.info(f"Edit button for {member_name} clicked (not implemented).")

                # History button and modal
                if cols[2].button("History", key=f"history_{member_id}"):
                    with st.experimental_dialog(f"History for {member_name}"):
                        st.write(f"Transaction History for {member_name}:")
                        try:
                            transactions = api.get_member_transactions(member_id)
                            if transactions:
                                total_amount = 0
                                for tx in transactions:
                                    # Assuming tx is a dict with 'date', 'plan_name', 'amount'
                                    tx_date = tx.get("date", "N/A")
                                    plan_name = tx.get(
                                        "plan_name", "N/A"
                                    )  # Or 'description'
                                    amount = tx.get("amount", 0)
                                    st.write(
                                        f"- Date: {tx_date}, Plan: {plan_name}, Amount: ${amount:.2f}"
                                    )
                                    total_amount += amount
                                st.markdown("---")
                                st.subheader(f"Total Amount Paid: ${total_amount:.2f}")
                            else:
                                st.info("No transaction history found for this member.")
                        except Exception as e:
                            st.error(f"An error occurred while fetching history: {e}")

                # Delete button
                if cols[3].button("Delete", key=f"delete_{member_id}"):
                    try:
                        api.delete_member(member_id)
                        st.success(
                            f"Member {member_name} (ID: {member_id}) deleted successfully."
                        )
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(
                            f"Error deleting member {member_name} (ID: {member_id}): {e}"
                        )
        else:
            st.info("No members found.")


def render_plans_tab():
    st.header("Plan Management")
    # Placeholder content
    st.write("Content for plan management will go here.")


def render_reporting_tab():
    st.header("Reporting")
    # Placeholder content
    st.write("Content for reporting will go here.")


st.set_page_config(layout="wide")
st.title("Kranos MMA Reporter v2.0")  # Update title if desired

# New tab structure
tab_memberships, tab_members, tab_plans, tab_reporting = st.tabs(
    ["Memberships", "Members", "Plans", "Reporting"]
)

with tab_memberships:
    render_memberships_tab()

with tab_members:
    render_members_tab()

with tab_plans:
    render_plans_tab()

with tab_reporting:
    render_reporting_tab()
