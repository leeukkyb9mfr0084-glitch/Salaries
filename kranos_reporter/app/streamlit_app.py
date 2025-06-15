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
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching active plans: {e}")
        return []


def fetch_all_plans_details():
    """Fetches all plans with full details from the API."""
    url = f"{API_BASE_URL}/plans/all"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching all plan details: {e}")
        return []


def fetch_renewal_report(days_ahead):
    url = f"{API_BASE_URL}/reports/renewal?days_ahead={days_ahead}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.HTTPError as http_err:
        error_detail = (
            response.json().get("error", str(http_err))
            if response.content
            else str(http_err)
        )
        return None, f"HTTP error: {error_detail}"
    except Exception as e:
        return None, f"Request error: {e}"


def fetch_monthly_report_data(month, year):
    url = f"{API_BASE_URL}/reports/monthly?month={month}&year={year}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.HTTPError as http_err:
        error_detail = (
            response.json().get("error", str(http_err))
            if response.content
            else str(http_err)
        )
        return None, f"HTTP error: {error_detail}"
    except Exception as e:
        return None, f"Request error: {e}"


def render_reporting_tab():
    st.header("Reporting")
    report_col1, report_col2 = st.columns(2)
    with report_col1:
        st.subheader("Monthly Financial Report")
        current_time = datetime.now()
        month_names = [datetime(2000, m, 1).strftime("%B") for m in range(1, 13)]
        selected_month_name = st.selectbox(
            "Month:",
            options=month_names,
            index=current_time.month - 1,
            key="monthly_report_month",
        )
        selected_year = st.number_input(
            "Year:",
            min_value=current_time.year - 10,
            max_value=current_time.year + 5,
            value=current_time.year,
            step=1,
            key="monthly_report_year",
        )
        if st.button("Generate Monthly Report"):
            selected_month_number = month_names.index(selected_month_name) + 1
            with st.spinner(
                f"Fetching monthly report for {selected_month_name} {selected_year}..."
            ):
                report_data, error = fetch_monthly_report_data(
                    selected_month_number, selected_year
                )
            if error:
                st.error(error)
            elif report_data and isinstance(report_data, dict):
                transactions_list = report_data.get("transactions", [])
                total_revenue = report_data.get("total_revenue", 0.0)
                if not transactions_list and total_revenue == 0.0:
                    st.info(
                        f"No transactions found for {selected_month_name} {selected_year}."
                    )
                else:
                    st.metric(
                        label="Total Revenue for Selected Month",
                        value=f"₹{total_revenue:,.2f}",
                    )
                    if transactions_list:
                        try:
                            transactions_df = pd.DataFrame(transactions_list)
                            st.dataframe(transactions_df)
                            st.download_button(
                                label="Download Monthly Report as CSV",
                                data=transactions_df.to_csv(index=False).encode(
                                    "utf-8"
                                ),
                                file_name=f"monthly_report_{selected_year}_{selected_month_name}.csv",
                                mime="text/csv",
                                key="download_monthly_report_csv",
                            )
                        except Exception as e:
                            st.error(
                                f"An error occurred while processing transaction data: {e}"
                            )
                    else:
                        st.info(
                            f"No individual transactions to display for {selected_month_name} {selected_year}, but total revenue is recorded."
                        )
            elif report_data is None and not error:
                st.info(
                    f"No transactions found for {selected_month_name} {selected_year}."
                )
            else:
                st.error("An unknown error occurred or data is malformed.")
    with report_col2:
        st.subheader("Upcoming Membership Renewals")
        days_ahead = st.number_input(
            "Days Ahead for Renewal Report:",
            min_value=1,
            max_value=365,
            value=30,
            step=1,
            help="Enter the number of days (from today) to look for upcoming renewals.",
        )
        if st.button("Generate Renewal Report"):
            with st.spinner(
                f"Fetching renewal report for the next {days_ahead} days..."
            ):
                report_data, error = fetch_renewal_report(days_ahead)
            if error:
                st.error(error)
            elif report_data is not None:
                if not report_data:
                    st.info("No members found for renewal in the specified period.")
                else:
                    try:
                        df = pd.DataFrame(report_data)
                        expected_cols = [
                            "member_name",
                            "member_phone",
                            "member_email",
                            "plan_name",
                            "plan_end_date",
                        ]
                        cols_to_display = [
                            col for col in expected_cols if col in df.columns
                        ]
                        st.dataframe(df[cols_to_display])
                        if not df.empty:
                            st.download_button(
                                label="Download Report as CSV",
                                data=df.to_csv(index=False).encode("utf-8"),
                                file_name=f"renewal_report_{days_ahead}_days.csv",
                                mime="text/csv",
                                key="download_renewal_report_csv",
                            )
                    except Exception as e:
                        st.error(f"An error occurred while processing report data: {e}")
            else:
                st.error("An unknown error occurred while fetching the report.")


def render_plans_tab():
    st.header("Manage Plans")
    if "editing_plan_id" not in st.session_state:
        st.session_state.editing_plan_id = None
    if "plan_form_data" not in st.session_state:
        st.session_state.plan_form_data = {
            "name": "",
            "price": 0.0,
            "duration": "",
            "type": "Group Class",
        }
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(
            "Add/Edit Plan"
            if not st.session_state.editing_plan_id
            else f"Edit Plan ID: {st.session_state.editing_plan_id}"
        )
        plan_type_options = ["Group Class", "Personal Training"]
        if st.session_state.plan_form_data.get("type") not in plan_type_options:
            st.session_state.plan_form_data["type"] = plan_type_options[0]
        current_type_index = plan_type_options.index(
            st.session_state.plan_form_data.get("type")
        )
        with st.form("add_edit_plan_form", clear_on_submit=False):
            name_val = st.text_input(
                "Plan Name", value=st.session_state.plan_form_data.get("name", "")
            )
            price_val = st.number_input(
                "Price (INR)",
                min_value=0.0,
                value=st.session_state.plan_form_data.get("price", 0.0),
                step=0.01,
                format="%.2f",
            )
            duration_val = st.text_input(
                "Duration (e.g., '1 month', '3 months', '1 year')",
                value=st.session_state.plan_form_data.get("duration", ""),
            )
            type_val = st.selectbox(
                "Plan Type", options=plan_type_options, index=current_type_index
            )
            form_col1_buttons, form_col2_buttons = st.columns(2)
            with form_col1_buttons:
                save_button_label = (
                    "Update Plan" if st.session_state.editing_plan_id else "Save Plan"
                )
                if st.form_submit_button(save_button_label):
                    if not name_val:
                        st.error("Plan Name cannot be empty.")
                    elif price_val < 0:
                        st.error("Price cannot be negative.")
                    elif not duration_val:
                        st.error("Duration cannot be empty.")
                    else:
                        payload = {
                            "name": name_val,
                            "price": price_val,
                            "duration": duration_val,
                            "type": type_val,
                        }
                        try:
                            if st.session_state.editing_plan_id:
                                response = requests.put(
                                    f"{API_BASE_URL}/plans/{st.session_state.editing_plan_id}",
                                    json=payload,
                                    timeout=10,
                                )
                                response.raise_for_status()
                                st.success(f"Plan '{name_val}' updated successfully!")
                            else:
                                payload["is_active"] = True
                                response = requests.post(
                                    f"{API_BASE_URL}/plans", json=payload, timeout=10
                                )
                                response.raise_for_status()
                                st.success(
                                    f"Plan '{name_val}' added successfully! ID: {response.json().get('plan_id', 'N/A')}"
                                )
                            st.session_state.editing_plan_id = None
                            st.session_state.plan_form_data = {
                                "name": "",
                                "price": 0.0,
                                "duration": "",
                                "type": "Group Class",
                            }
                            st.rerun()
                        except requests.exceptions.HTTPError as http_err:
                            error_detail = (
                                response.json().get("error", str(http_err))
                                if response.content
                                else str(http_err)
                            )
                            st.error(f"Error saving plan: {error_detail}")
                        except requests.exceptions.RequestException as e:
                            st.error(f"Error saving plan: {e}")
            with form_col2_buttons:
                if st.form_submit_button("Clear Form", use_container_width=True):
                    st.session_state.editing_plan_id = None
                    st.session_state.plan_form_data = {
                        "name": "",
                        "price": 0.0,
                        "duration": "",
                        "type": "Group Class",
                    }
                    st.rerun()
    with col2:
        st.subheader("Existing Plans")
        all_plans = fetch_all_plans_details()
        if not all_plans:
            st.info("No plans found or API error.")
        else:
            for plan in all_plans:
                plan_id = plan.get("id", "N/A")
                with st.container():
                    st.markdown(f"**{plan.get('name', 'N/A')}** (ID: {plan_id})")
                    details_col1, details_col2, details_col3 = st.columns(3)
                    with details_col1:
                        st.text(f"Price: ₹{plan.get('price', 0.0):.2f}")
                        st.text(
                            f"Duration: {plan.get('duration', plan.get('duration_days', 'N/A'))}"
                        )
                        st.text(f"Type: {plan.get('type', 'N/A')}")
                    current_is_active = plan.get("is_active", True)
                    with details_col2:
                        new_is_active = st.checkbox(
                            "Active", value=current_is_active, key=f"active_{plan_id}"
                        )
                        if new_is_active != current_is_active:
                            try:
                                response = requests.put(
                                    f"{API_BASE_URL}/plans/{plan_id}/status",
                                    json={"is_active": new_is_active},
                                    timeout=5,
                                )
                                response.raise_for_status()
                                st.success(f"Plan {plan.get('name')} status updated!")
                                st.rerun()
                            except requests.exceptions.RequestException as e:
                                st.error(
                                    f"Failed to update status for plan {plan_id}: {e}"
                                )
                    with details_col3:
                        if st.button(
                            "Edit", key=f"edit_{plan_id}", use_container_width=True
                        ):
                            st.session_state.editing_plan_id = plan_id
                            st.session_state.plan_form_data = {
                                "name": plan.get("name", ""),
                                "price": plan.get("price", 0.0),
                                "duration": plan.get(
                                    "duration", plan.get("duration_days", "")
                                ),
                                "type": plan.get("type", "Group Class"),
                                "is_active": plan.get("is_active", True),
                            }
                            st.rerun()
                        if st.button(
                            "Delete",
                            key=f"delete_{plan_id}",
                            type="secondary",
                            use_container_width=True,
                        ):
                            try:
                                response = requests.delete(
                                    f"{API_BASE_URL}/plans/{plan_id}", timeout=5
                                )
                                response.raise_for_status()
                                st.success(
                                    f"Plan {plan.get('name')} deleted successfully!"
                                )
                                st.rerun()
                            except requests.exceptions.RequestException as e:
                                st.error(f"Failed to delete plan {plan_id}: {e}")
                    st.divider()


def main():
    st.set_page_config(page_title="Kranos MMA Reporter", layout="wide")
    st.title("Kranos MMA Reporter")
    tab_titles = ["Memberships", "Members", "Plans", "Reporting"]
    try:
        default_index = tab_titles.index("Memberships")
    except ValueError:
        default_index = 0
    selected_tab = st.sidebar.radio("Navigation", tab_titles, index=default_index)
    if selected_tab == "Memberships":
        display_memberships_tab()
    elif selected_tab == "Members":
        display_members_tab()
    elif selected_tab == "Plans":
        render_plans_tab()
    elif selected_tab == "Reporting":
        render_reporting_tab()


def display_memberships_tab():
    st.header("Manage Memberships")

    default_form_data = {
        "member_id": None,
        "plan_id": None,
        "amount_paid": 0.0,
        "payment_method": "Cash",
        "payment_date": date.today(),
        "transaction_type": "New Subscription",
        "notes": "",
    }
    for key, value in default_form_data.items():
        if f"add_membership_{key}" not in st.session_state:
            st.session_state[f"add_membership_{key}"] = value
    if "add_membership_sessions" not in st.session_state:
        st.session_state.add_membership_sessions = 10

    if "all_members_for_selectbox" not in st.session_state:
        try:
            response = requests.get(
                f"{API_BASE_URL}/members/filtered/?status=Active", timeout=5
            )
            response.raise_for_status()
            members_list_data = response.json()
            st.session_state.all_members_for_selectbox = {
                member["member_id"]: member["client_name"]
                for member in members_list_data
            }
        except Exception as e:
            st.error(f"Error fetching active members for selection: {e}")
            st.session_state.all_members_for_selectbox = {}

    if "active_plans_for_selectbox" not in st.session_state:
        plans_data = fetch_active_plans()
        st.session_state.active_plans_for_selectbox = {
            plan["id"]: plan["name"] for plan in plans_data
        }

    col1_add_membership, col2_transactions = st.columns(2)

    with col1_add_membership:
        st.subheader("Add Membership / Record Transaction")
        with st.form("add_membership_form", clear_on_submit=False):
            member_id_widget = st.selectbox(
                "Select Member:",
                options=list(st.session_state.all_members_for_selectbox.keys()),
                format_func=lambda m_id: st.session_state.all_members_for_selectbox.get(
                    m_id, "Unknown Member"
                ),
                index=(
                    0
                    if not st.session_state.all_members_for_selectbox
                    else (
                        list(st.session_state.all_members_for_selectbox.keys()).index(
                            st.session_state.add_membership_member_id
                        )
                        if st.session_state.add_membership_member_id
                        in st.session_state.all_members_for_selectbox
                        else 0
                    )
                ),
            )
            transaction_type_widget = st.selectbox(
                "Transaction Type:",
                options=[
                    "New Subscription",
                    "Renewal",
                    "Personal Training Session(s)",
                    "Other Payment",
                    "membership_fee",
                ],  # Added membership_fee
                index=[
                    "New Subscription",
                    "Renewal",
                    "Personal Training Session(s)",
                    "Other Payment",
                    "membership_fee",
                ].index(st.session_state.add_membership_transaction_type),
            )

            plan_id_widget = None
            if transaction_type_widget in [
                "New Subscription",
                "Renewal",
                "membership_fee",
            ]:
                plan_id_widget = st.selectbox(
                    "Select Plan:",
                    options=[None]
                    + list(st.session_state.active_plans_for_selectbox.keys()),
                    format_func=lambda p_id: st.session_state.active_plans_for_selectbox.get(
                        p_id, "Select a Plan"
                    ),
                    index=(
                        0
                        if not st.session_state.active_plans_for_selectbox
                        else (
                            (
                                [None]
                                + list(
                                    st.session_state.active_plans_for_selectbox.keys()
                                )
                            ).index(st.session_state.add_membership_plan_id)
                            if st.session_state.add_membership_plan_id
                            in (
                                [None]
                                + list(
                                    st.session_state.active_plans_for_selectbox.keys()
                                )
                            )
                            else 0
                        )
                    ),
                )

            amount_paid_widget = st.number_input(
                "Amount Paid (INR):",
                min_value=0.0,
                value=st.session_state.add_membership_amount_paid,
                step=0.01,
            )
            payment_method_widget = st.selectbox(
                "Payment Method:",
                options=["Cash", "Card", "Online", "Other"],
                index=["Cash", "Card", "Online", "Other"].index(
                    st.session_state.add_membership_payment_method
                ),
            )
            payment_date_widget = st.date_input(
                "Payment Date:", value=st.session_state.add_membership_payment_date
            )
            notes_widget = st.text_area(
                "Notes/Description:", value=st.session_state.add_membership_notes
            )  # Changed key to match session state

            sessions_widget = None
            if transaction_type_widget == "Personal Training Session(s)":
                sessions_widget = st.number_input(
                    "Number of Sessions (for PT):",
                    min_value=1,
                    value=st.session_state.add_membership_sessions,
                    step=1,
                )

            submit_membership_button = st.form_submit_button(
                "Save Membership Transaction"
            )

            if submit_membership_button:
                if not member_id_widget:
                    st.error("Please select a member.")
                elif (
                    transaction_type_widget
                    in ["New Subscription", "Renewal", "membership_fee"]
                    and not plan_id_widget
                ):
                    st.error(
                        f"Please select a plan for transaction type '{transaction_type_widget}'."
                    )
                else:
                    payload = {
                        "member_id": member_id_widget,
                        "plan_id": (
                            plan_id_widget
                            if transaction_type_widget
                            in ["New Subscription", "Renewal", "membership_fee"]
                            else None
                        ),
                        "transaction_type": transaction_type_widget,
                        "amount_paid": amount_paid_widget,
                        "payment_method": payment_method_widget,
                        "payment_date": payment_date_widget.isoformat(),
                        "notes": notes_widget,
                    }
                    if (
                        transaction_type_widget == "Personal Training Session(s)"
                        and sessions_widget is not None
                    ):
                        payload["notes"] = (
                            f"{notes_widget} (Sessions: {sessions_widget})".strip()
                        )

                    add_transaction_url = f"{API_BASE_URL}/transactions"
                    try:
                        response = requests.post(
                            add_transaction_url, json=payload, timeout=10
                        )
                        response.raise_for_status()
                        st.success("Membership transaction recorded successfully!")
                        # Reset form values in session state to defaults
                        for (
                            key_suffix,
                            default_val,
                        ) in (
                            default_form_data.items()
                        ):  # Use original default_form_data
                            st.session_state[f"add_membership_{key_suffix}"] = (
                                default_val
                            )
                        st.session_state.add_membership_sessions = 10
                        st.rerun()
                    except requests.exceptions.HTTPError as http_err:
                        error_detail = (
                            response.json().get("error", str(http_err))
                            if response.content
                            else str(http_err)
                        )
                        st.error(f"Error recording transaction: {error_detail}")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Error recording transaction: {e}")

    with col2_transactions:
        st.subheader("Recent Transactions & Filters")
        if "transactions_start_date_filter" not in st.session_state:
            st.session_state.transactions_start_date_filter = None
        if "transactions_end_date_filter" not in st.session_state:
            st.session_state.transactions_end_date_filter = None
        if "transactions_member_search_filter" not in st.session_state:
            st.session_state.transactions_member_search_filter = ""
        if "transactions_type_filter_select" not in st.session_state:
            st.session_state.transactions_type_filter_select = "All"

        filter_col1_trans, filter_col2_trans = st.columns(2)
        with filter_col1_trans:
            st.date_input("From Date:", key="transactions_start_date_filter")
            st.text_input(
                "Search by Member Name:", key="transactions_member_search_filter"
            )
        with filter_col2_trans:
            st.date_input("To Date:", key="transactions_end_date_filter")
            st.selectbox(
                "Transaction Type:",
                options=[
                    "All",
                    "New Subscription",
                    "Renewal",
                    "Personal Training Session(s)",
                    "Other Payment",
                    "membership_fee",
                ],
                key="transactions_type_filter_select",
            )

        params_trans_list = {}
        if st.session_state.transactions_start_date_filter:
            params_trans_list["start_date"] = (
                st.session_state.transactions_start_date_filter.strftime("%Y-%m-%d")
            )
        if st.session_state.transactions_end_date_filter:
            params_trans_list["end_date"] = (
                st.session_state.transactions_end_date_filter.strftime("%Y-%m-%d")
            )
        if st.session_state.transactions_member_search_filter:
            params_trans_list["member_name_search"] = (
                st.session_state.transactions_member_search_filter
            )
        if st.session_state.transactions_type_filter_select != "All":
            params_trans_list["transaction_type"] = (
                st.session_state.transactions_type_filter_select
            )

        try:
            response_trans_list = requests.get(
                f"{API_BASE_URL}/transactions/filtered",
                params=params_trans_list,
                timeout=10,
            )
            response_trans_list.raise_for_status()
            transactions_data_list = response_trans_list.json()
            if transactions_data_list:
                df_transactions = pd.DataFrame(transactions_data_list)
                display_cols = [
                    "member_name",
                    "plan_name",
                    "transaction_date",
                    "amount",
                    "transaction_type",
                    "payment_method",
                    "notes",
                    "membership_start_date",
                    "membership_end_date",
                ]
                existing_display_cols = [
                    col for col in display_cols if col in df_transactions.columns
                ]
                st.dataframe(df_transactions[existing_display_cols], hide_index=True)
            else:
                st.info("No transactions found matching your criteria.")
        except requests.exceptions.HTTPError as http_err:
            error_detail = (
                response_trans_list.json().get("error", str(http_err))
                if response_trans_list.content
                else str(http_err)
            )
            st.error(f"Error fetching transactions: {error_detail}")
        except Exception as e:
            st.error(f"An error occurred while fetching transactions: {e}")

    st.divider()
    st.subheader("Close Books for Month")
    current_year_cb = datetime.now().year
    current_month_cb = datetime.now().month
    month_names_cb = [datetime(2000, m, 1).strftime("%B") for m in range(1, 13)]
    default_month_index_cb = (current_month_cb - 2) if current_month_cb > 1 else 11
    selected_month_name_cb = st.selectbox(
        "Month:",
        options=month_names_cb,
        index=default_month_index_cb,
        key="close_books_month_select",
    )
    selected_month_number_cb = month_names_cb.index(selected_month_name_cb) + 1
    selected_year_cb = st.number_input(
        "Year:",
        min_value=current_year_cb - 10,
        max_value=current_year_cb,
        value=current_year_cb if current_month_cb > 1 else current_year_cb - 1,
        step=1,
        key="close_books_year_input",
    )
    if st.button(
        f"Close Books for {selected_month_name_cb} {selected_year_cb}",
        type="primary",
        key="close_books_button",
    ):
        payload_cb = {"month": selected_month_number_cb, "year": selected_year_cb}
        try:
            response_cb = requests.post(
                f"{API_BASE_URL}/books/close", json=payload_cb, timeout=15
            )
            response_cb.raise_for_status()
            st.success(response_cb.json().get("message", "Books closed successfully!"))
        except requests.exceptions.HTTPError as http_err:
            error_detail = (
                response_cb.json().get("error", str(http_err))
                if response_cb.content
                else str(http_err)
            )
            st.error(f"Error closing books: {error_detail}")
        except Exception as e:
            st.error(f"Failed to close books: {e}")


def display_members_tab():
    st.header("Manage Members")
    col1_form, col2_list = st.columns(2)

    if "member_form_data" not in st.session_state:
        st.session_state.member_form_data = {
            "name": "",
            "email": "",
            "phone": "",
            "join_date": date.today(),
            "notes": "",
            "is_active": True,
        }
    if "editing_member_id" not in st.session_state:
        st.session_state.editing_member_id = None
    if "member_form_ready_to_prefill" not in st.session_state:
        st.session_state.member_form_ready_to_prefill = False

    if "show_history_modal_member_id" not in st.session_state:
        st.session_state.show_history_modal_member_id = None
    if "member_history_data" not in st.session_state:
        st.session_state.member_history_data = None
    if "member_history_error" not in st.session_state:
        st.session_state.member_history_error = None

    with col1_form:
        form_title = (
            "Edit Member" if st.session_state.editing_member_id else "Add New Member"
        )
        st.subheader(form_title)

        if (
            st.session_state.editing_member_id
            and st.session_state.member_form_ready_to_prefill
        ):
            try:
                response = requests.get(
                    f"{API_BASE_URL}/member/{st.session_state.editing_member_id}",
                    timeout=5,
                )
                response.raise_for_status()
                member_data = response.json()
                st.session_state.member_form_data["name"] = member_data.get(
                    "client_name", ""
                )
                st.session_state.member_form_data["email"] = member_data.get(
                    "email", ""
                )
                st.session_state.member_form_data["phone"] = member_data.get(
                    "phone", ""
                )
                join_date_str = member_data.get("join_date")
                st.session_state.member_form_data["join_date"] = (
                    datetime.strptime(join_date_str, "%Y-%m-%d").date()
                    if join_date_str
                    else date.today()
                )
                st.session_state.member_form_data["notes"] = member_data.get(
                    "notes", ""
                )
                st.session_state.member_form_data["is_active"] = bool(
                    member_data.get("is_active", True)
                )
                st.session_state.member_form_ready_to_prefill = False
            except Exception as e:
                st.error(f"Error fetching member details for edit: {e}")
                st.session_state.editing_member_id = None
                st.session_state.member_form_data = {
                    "name": "",
                    "email": "",
                    "phone": "",
                    "join_date": date.today(),
                    "notes": "",
                    "is_active": True,
                }

        with st.form("member_form", clear_on_submit=False):
            name = st.text_input(
                "Name:", value=st.session_state.member_form_data.get("name", "")
            )
            email = st.text_input(
                "Email:", value=st.session_state.member_form_data.get("email", "")
            )
            phone = st.text_input(
                "Phone:", value=st.session_state.member_form_data.get("phone", "")
            )
            join_date_val = st.date_input(
                "Join Date:",
                value=st.session_state.member_form_data.get("join_date", date.today()),
            )
            notes_val = st.text_area(
                "Notes:", value=st.session_state.member_form_data.get("notes", "")
            )
            is_active_val = st.checkbox(
                "Is Active",
                value=st.session_state.member_form_data.get("is_active", True),
            )

            form_button_col1, form_button_col2 = st.columns(2)
            with form_button_col1:
                if st.form_submit_button("Save Member"):
                    if not name or not phone:
                        st.error("Name and Phone are required.")
                    else:
                        payload = {
                            "name": name,
                            "email": email,
                            "phone": phone,
                            "join_date": join_date_val.isoformat(),
                            "notes": notes_val,
                            "is_active": is_active_val,
                        }
                        try:
                            if st.session_state.editing_member_id:
                                response = requests.put(
                                    f"{API_BASE_URL}/member/{st.session_state.editing_member_id}",
                                    json=payload,
                                    timeout=10,
                                )
                                response.raise_for_status()
                                st.success(f"Member '{name}' updated successfully!")
                            else:
                                response = requests.post(
                                    f"{API_BASE_URL}/members", json=payload, timeout=10
                                )
                                response.raise_for_status()
                                st.success(
                                    f"Member '{name}' added successfully! ID: {response.json().get('member_id', 'N/A')}"
                                )
                            st.session_state.editing_member_id = None
                            st.session_state.member_form_data = {
                                "name": "",
                                "email": "",
                                "phone": "",
                                "join_date": date.today(),
                                "notes": "",
                                "is_active": True,
                            }
                            st.rerun()
                        except requests.exceptions.HTTPError as http_err:
                            error_detail = (
                                response.json().get("error", str(http_err))
                                if response.content
                                else str(http_err)
                            )
                            st.error(f"Error saving member: {error_detail}")
                        except Exception as e:
                            st.error(f"Error saving member: {e}")
            with form_button_col2:
                if st.form_submit_button("Clear Form", use_container_width=True):
                    st.session_state.editing_member_id = None
                    st.session_state.member_form_data = {
                        "name": "",
                        "email": "",
                        "phone": "",
                        "join_date": date.today(),
                        "notes": "",
                        "is_active": True,
                    }
                    st.rerun()

    with col2_list:
        st.subheader("Members List & Filters")
        search_term = st.text_input(
            "Search Member by Name/Email/Phone:", key="member_search_input"
        )
        status_filter = st.selectbox(
            "Filter by Status:",
            ["Active", "Inactive", "All"],
            key="member_status_filter",
            index=0,
        )

        params = {}
        if search_term:
            params["search_term"] = search_term
        if status_filter != "All":
            params["status"] = status_filter

        try:
            response = requests.get(
                f"{API_BASE_URL}/members/filtered/", params=params, timeout=5
            )
            response.raise_for_status()
            members_data = response.json()
            if members_data:
                df_members = pd.DataFrame(members_data)
                if "is_active" in df_members.columns:
                    df_members["is_active"] = df_members["is_active"].apply(
                        lambda x: bool(x)
                    )

                for index, member in df_members.iterrows():
                    member_id = member["member_id"]
                    with st.container():
                        name_display = member.get(
                            "client_name", member.get("name", "N/A")
                        )
                        st.markdown(f"**{name_display}** (ID: {member_id})")
                        details_cols = st.columns(2)
                        details_cols[0].text(f"Email: {member.get('email', 'N/A')}")
                        details_cols[0].text(f"Phone: {member.get('phone', 'N/A')}")
                        details_cols[1].text(
                            f"Join Date: {member.get('join_date', 'N/A')}"
                        )
                        details_cols[1].text(
                            f"Status: {'Active' if member.get('is_active') else 'Inactive'}"
                        )
                        if member.get("notes"):  # Display notes if they exist
                            with st.expander("Notes"):
                                st.text(member.get("notes"))
                        action_cols = st.columns(3)
                        if action_cols[0].button(
                            "Edit",
                            key=f"edit_member_{member_id}",
                            use_container_width=True,
                        ):
                            st.session_state.editing_member_id = member_id
                            st.session_state.member_form_ready_to_prefill = True
                            st.rerun()

                        deactivate_key = f"deactivate_member_{member_id}"
                        if st.session_state.get(
                            f"confirm_deactivate_{member_id}", False
                        ):
                            st.warning(
                                f"Are you sure you want to deactivate {name_display}?"
                            )
                            if action_cols[1].button(
                                "Confirm Deactivate",
                                key=f"confirm_deactivate_btn_{member_id}",
                                use_container_width=True,
                            ):
                                try:
                                    response = requests.put(
                                        f"{API_BASE_URL}/member/{member_id}/active_status",
                                        json={"is_active": False},
                                        timeout=5,
                                    )
                                    response.raise_for_status()
                                    st.success(f"Member {name_display} deactivated.")
                                    st.session_state[
                                        f"confirm_deactivate_{member_id}"
                                    ] = False
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to deactivate member: {e}")
                                    st.session_state[
                                        f"confirm_deactivate_{member_id}"
                                    ] = False
                            if action_cols[2].button(
                                "Cancel",
                                key=f"cancel_deactivate_{member_id}",
                                use_container_width=True,
                            ):  # Changed to use action_cols[2] for Cancel
                                st.session_state[f"confirm_deactivate_{member_id}"] = (
                                    False
                                )
                                st.rerun()
                        else:
                            if action_cols[1].button(
                                "Deactivate",
                                key=deactivate_key,
                                type="secondary",
                                use_container_width=True,
                            ):
                                st.session_state[f"confirm_deactivate_{member_id}"] = (
                                    True
                                )
                                st.rerun()

                        if action_cols[2].button(
                            "History",
                            key=f"history_member_{member_id}",
                            use_container_width=True,
                        ):
                            st.session_state.show_history_modal_member_id = member_id
                            try:
                                hist_resp = requests.get(
                                    f"{API_BASE_URL}/member/{member_id}/transactions",
                                    timeout=5,
                                )
                                hist_resp.raise_for_status()
                                st.session_state.member_history_data = hist_resp.json()
                                st.session_state.member_history_error = None
                            except Exception as e:
                                st.session_state.member_history_data = None
                                st.session_state.member_history_error = (
                                    f"Error fetching history: {e}"
                                )
                            st.rerun()
                        st.divider()
            else:
                st.info("No members found matching your criteria.")
        except Exception as e:
            st.error(f"Error fetching members: {e}")

    if st.session_state.show_history_modal_member_id:
        mid_modal = st.session_state.show_history_modal_member_id
        mname_modal = f"Member ID {mid_modal}"
        with st.container():
            st.subheader(f"Transaction History for {mname_modal}")
            if st.session_state.member_history_error:
                st.error(st.session_state.member_history_error)
            elif st.session_state.member_history_data:
                df_hist = pd.DataFrame(st.session_state.member_history_data)
                if not df_hist.empty:
                    st.dataframe(df_hist)
                    total_paid = (
                        df_hist["amount_paid"].sum()
                        if "amount_paid" in df_hist.columns
                        else 0
                    )
                    st.metric("Total Amount Paid", f"₹{total_paid:.2f}")
                else:
                    st.info("No transaction history found for this member.")
            else:
                st.info("Loading history...")
            if st.button("Close History", key=f"close_history_{mid_modal}"):
                st.session_state.show_history_modal_member_id = None
                st.session_state.member_history_data = None
                st.session_state.member_history_error = None
                st.rerun()


if __name__ == "__main__":
    main()
