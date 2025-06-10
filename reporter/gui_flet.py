import flet as ft
from typing import Optional, List
from datetime import datetime, date
from reporter import database_manager # This might need adjustment if database_manager path changes
import pandas as pd
from openpyxl.styles import Font, Border, Side, Alignment, PatternFill
from openpyxl.utils import get_column_letter
import calendar

class GuiController:
    def save_member_action(self, name: str, phone: str) -> tuple[bool, str]:
        """Handles the save member action with input validation."""
        # --- Input Validation ---
        if not name or not phone:
            return False, "Error: Name and Phone cannot be empty."

        if not phone.isdigit():
            return False, "Error: Phone number must contain only digits."
        # Example: Validate phone length (e.g., 10 digits) - can be added if needed
        # if len(phone) != 10:
        #     return False, "Error: Phone number must be 10 digits."

        try:
            # database_manager.add_member_to_db now returns -> Tuple[bool, str]
            success, message = database_manager.add_member_to_db(name, phone)
            # Use the returned success and message directly
            return success, message
        except Exception as e:
            # This catch block might be redundant if database_manager handles all its specific errors
            # and returns (False, error_message). However, it can catch unexpected errors.
            return False, f"An unexpected error occurred: {str(e)}"

    def save_plan_action(self, plan_name: str, duration_str: str, plan_id_to_update: str) -> tuple[bool, str, list | None]:
        """Saves a new plan or updates an existing one."""
        if not plan_name or not duration_str:
            return False, "Error: Plan Name and Duration cannot be empty.", None

        try:
            duration_days = int(duration_str)
            if duration_days <= 0:
                return False, "Error: Duration must be a positive integer.", None
        except ValueError:
            return False, "Error: Duration must be a valid integer.", None

        success = False
        message = ""
        updated_plans = None

        try:
            if plan_id_to_update:  # Editing existing plan
                plan_id = int(plan_id_to_update)
                # database_manager.update_plan now returns -> Tuple[bool, str]
                db_success, db_message = database_manager.update_plan(plan_id, plan_name, duration_days)
                success = db_success
                message = db_message
            else:  # Adding new plan
                # database_manager.add_plan now returns -> Tuple[bool, str, Optional[int]]
                db_success, db_message, returned_plan_id = database_manager.add_plan(plan_name, duration_days)
                success = db_success
                message = db_message
                # returned_plan_id is available if needed, e.g., for logging or immediate use,
                # but current logic just relies on success status.

            if success:
                updated_plans = database_manager.get_all_plans_with_inactive()
            return success, message, updated_plans
        except Exception as e:
            # Catch unexpected errors during the controller logic (e.g., int conversion if not validated)
            return False, f"An unexpected error occurred in save_plan_action: {str(e)}", None

    def toggle_plan_status_action(self, plan_id: int, current_status: bool) -> tuple[bool, str, list | None]:
        """Activates or deactivates a plan."""
        new_status = not current_status
        # database_manager.set_plan_active_status now returns -> Tuple[bool, str]
        db_success, db_message = database_manager.set_plan_active_status(plan_id, new_status)
        success = db_success
        message = db_message # Use the message from the database manager
        updated_plans = None

        if success:
            # Optionally, you could still use a custom success message or augment db_message
            # For now, directly using db_message. If a custom success message is preferred:
            # message = f"Plan status changed to {'Active' if new_status else 'Inactive'}."
            updated_plans = database_manager.get_all_plans_with_inactive()
        # If not successful, db_message already contains the error.
        return success, message, updated_plans

    def save_membership_action(self, membership_type: str, member_id: int | None,
                               start_date_str: str, amount_paid_str: str,
                               selected_plan_id: int | None = None,
                               payment_date_str: str | None = None,
                               payment_method: str | None = None,
                               sessions_str: str | None = None) -> tuple[bool, str]:
        """Handles the save membership action with validation based on membership type."""
        from datetime import datetime # Moved import

        # --- Basic Validation ---
        if not member_id: # Simplified check, assuming member_id is directly passed
            return False, "Error: Please select a valid member."

        if not start_date_str:
            return False, "Error: Start Date cannot be empty."
        try:
            datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            return False, "Error: Invalid Start Date format. Use YYYY-MM-DD."

        try:
            amount_paid = float(amount_paid_str)
            if amount_paid <= 0: # Changed from < to <=
                return False, "Error: Amount Paid must be a positive number."
        except ValueError:
            return False, "Error: Invalid Amount Paid. Must be a number."

        success = False
        try:
            if membership_type == "Group Class":
                if not selected_plan_id: # Simplified check
                    return False, "Error: Please select a valid plan."
                if not payment_date_str:
                    return False, "Error: Payment Date cannot be empty for Group Class."
                try:
                    datetime.strptime(payment_date_str, '%Y-%m-%d')
                except ValueError:
                    return False, "Error: Invalid Payment Date format. Use YYYY-MM-DD."
                if not payment_method: # Ensure payment_method is not None or empty
                    return False, "Error: Payment Method cannot be empty for Group Class."

                success = database_manager.add_transaction(
                    transaction_type="Group Class",
                    member_id=member_id,
                    plan_id=selected_plan_id,
                    payment_date=payment_date_str,
                    start_date=start_date_str,
                    amount_paid=amount_paid,
                    payment_method=payment_method
                )
            elif membership_type == "Personal Training":
                if not sessions_str:
                    return False, "Error: Number of Sessions cannot be empty for PT."
                try:
                    sessions = int(sessions_str)
                    if sessions <= 0:
                        return False, "Error: Number of Sessions must be a positive integer."
                except ValueError:
                    return False, "Error: Number of Sessions must be an integer."

                # For PT, payment_date is the start_date, payment_method is N/A by default
                success = database_manager.add_transaction(
                    transaction_type="Personal Training",
                    member_id=member_id,
                    plan_id=None, # No plan_id for PT
                    payment_date=start_date_str,
                    start_date=start_date_str,
                    amount_paid=amount_paid,
                    payment_method="N/A", # Default or could be an argument if needed
                    sessions=sessions
                )
            else:
                return False, "Error: Unknown membership type selected."

            # success from database_manager.add_transaction is (bool, message)
            if success[0]: # If the first element (boolean) is True
                return True, f"{membership_type} membership added successfully!"
            else:
                # Return the specific error message from database_manager
                return False, success[1]
        except Exception as e:
            # Log the exception e for debugging purposes if possible
            return False, f"An error occurred: {str(e)}"

    def generate_custom_pending_renewals_action(self, year: int, month: int) -> tuple[bool, str, list | None]:
        """Fetches pending renewals for a specific year and month."""
        import calendar # For month name in message

        try:
            # The database_manager.get_pending_renewals is expected to handle its own exceptions
            # and return an empty list if there's a DB error or no results.
            renewals = database_manager.get_pending_renewals(year, month)

            month_name = calendar.month_name[month]

            # get_pending_renewals returns a list. An empty list means no renewals or a DB error handled by it.
            if renewals:
                return True, f"Found {len(renewals)} pending renewals for {month_name} {year}.", renewals
            else:
                # This covers both "no renewals found" and cases where get_pending_renewals had an issue and returned [].
                # The message from get_pending_renewals (if any, via print to stderr) would indicate DB error.
                # For the GUI, just report that no data was retrieved for the period.
                return True, f"No pending renewals found for {month_name} {year}.", []

        except Exception as e:
            # Catch any unexpected errors during the process
            month_name_str = str(month)
            try:
                month_name_str = calendar.month_name[month]
            except IndexError: # Should not happen if month is 1-12 as validated by App method
                pass
            return False, f"Error generating renewals report for {month_name_str} {year}: {str(e)}", None

    def generate_pending_renewals_action(self) -> tuple[bool, str, list | None]:
        """Fetches pending renewals for the current month."""
        from datetime import date
        import calendar

        today = date.today()
        # current_date_str = today.strftime('%Y-%m-%d') # Old way
        current_year = today.year
        current_month = today.month
        month_name = calendar.month_name[current_month]

        try:
            # Call the updated database_manager.get_pending_renewals with year and month
            renewals = database_manager.get_pending_renewals(year=current_year, month=current_month)
            if renewals: # renewals is a list, empty list means no data or DB error handled by get_pending_renewals
                return True, f"Found {len(renewals)} pending renewals for {month_name} {current_year}.", renewals
            else:
                return True, f"No pending renewals found for {month_name} {current_year}.", []
        except Exception as e:
            return False, f"Error generating report for current month: {str(e)}", None

    def generate_finance_report_excel_action(self, year: int, month: int, save_path: str) -> tuple[bool, str]:
        """
        Generates an Excel finance report for the given month and year.
        The report includes a summary sheet and a detailed transactions sheet.
        Applies styling to the report.
        """
        # pandas, openpyxl.styles, openpyxl.utils, calendar are imported at the top of the file.

        try:
            transactions_data = database_manager.get_transactions_for_month(year, month)

            month_name_str = calendar.month_name[month]

            if not transactions_data:
                return True, f"No transaction data found for {month_name_str} {year}. Report not generated."

            df_columns = [
                "Transaction ID", "Client Name", "Payment Date", "Start Date", "End Date",
                "Amount Paid", "Type", "Plan/Sessions", "Payment Method"
            ]
            df = pd.DataFrame(transactions_data, columns=df_columns)

            df["Amount Paid"] = pd.to_numeric(df["Amount Paid"], errors='coerce').fillna(0)
            df["Payment Date"] = pd.to_datetime(df["Payment Date"], errors='coerce').dt.strftime('%Y-%m-%d')
            df["Start Date"] = pd.to_datetime(df["Start Date"], errors='coerce').dt.strftime('%Y-%m-%d')
            # df["End Date"] can be 'N/A' or other non-date strings from DB if not NULL
            # Avoid direct conversion for "End Date" unless data cleaning is robust or it's always a valid date/NULL
            # df["End Date"] = pd.to_datetime(df["End Date"], errors='coerce').dt.strftime('%Y-%m-%d')


            total_revenue = df["Amount Paid"].sum()
            total_transactions = len(df)

            summary_data = {
                "Metric": ["Total Revenue", "Total Transactions"],
                "Value": [total_revenue, total_transactions]
            }
            summary_df = pd.DataFrame(summary_data)

            with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
                summary_df.to_excel(writer, sheet_name="Summary", index=False, startrow=2)
                df.to_excel(writer, sheet_name="Detailed Transactions", index=False, startrow=1) # data starts at row 2 after header

                workbook = writer.book
                summary_sheet = writer.sheets["Summary"]
                details_sheet = writer.sheets["Detailed Transactions"]

                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
                title_font = Font(bold=True, size=16)
                border_style = Side(style="thin", color="000000")
                thin_border = Border(left=border_style, right=border_style, top=border_style, bottom=border_style)

                summary_sheet.cell(row=1, column=1, value=f"Finance Summary - {month_name_str} {year}").font = title_font
                for col_num, column_title in enumerate(summary_df.columns, 1):
                    cell = summary_sheet.cell(row=3, column=col_num)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.border = thin_border
                for row_idx_offset, _ in enumerate(summary_df.index): # Iterate based on DataFrame index
                    for col_idx, _ in enumerate(summary_df.columns):
                        summary_sheet.cell(row=row_idx_offset + 4, column=col_idx + 1).border = thin_border

                summary_sheet.column_dimensions['A'].width = 25
                summary_sheet.column_dimensions['B'].width = 15
                summary_sheet.cell(row=4, column=2).number_format = '"$"#,##0.00'

                details_sheet.cell(row=1, column=1, value=f"Detailed Transactions - {month_name_str} {year}").font = title_font
                for col_num, column_title in enumerate(df.columns, 1):
                    cell = details_sheet.cell(row=2, column=col_num)
                    cell.value = column_title
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.border = thin_border
                    column_letter = get_column_letter(col_num)
                    try: # Handle potential empty series in max_len calculation
                        max_len = max(df[column_title].astype(str).map(len).max(), len(str(column_title))) + 2
                    except (TypeError, ValueError): # If column is empty or all NaT/NaN
                        max_len = len(str(column_title)) + 2
                    details_sheet.column_dimensions[column_letter].width = max_len if max_len < 50 else 50

                for row_idx_offset, _ in enumerate(df.index): # Iterate based on DataFrame index
                    for col_idx, _ in enumerate(df.columns):
                        details_sheet.cell(row=row_idx_offset + 3, column=col_idx + 1).border = thin_border

                amount_paid_col_letter = get_column_letter(df_columns.index("Amount Paid") + 1)
                for row_num in range(3, details_sheet.max_row + 1):
                     details_sheet[f'{amount_paid_col_letter}{row_num}'].number_format = '"$"#,##0.00'

            return True, f"Finance report generated successfully: {save_path}"

        except ImportError:
            return False, "Error: pandas or openpyxl library not found. Please ensure they are installed."
        except Exception as e:
            return False, f"An error occurred during report generation: {str(e)}"

    def get_book_status_action(self, year: int, month: int) -> str:
        """
        Constructs month_key, calls database_manager.get_book_status, and returns a user-friendly message.
        """
        try:
            month_key = f"{year:04d}-{month:02d}"
            status = database_manager.get_book_status(month_key)
            return f"Status for {month_key}: {status.upper()}"
        except Exception as e:
            return f"Error getting book status: {str(e)}"

    def close_books_action(self, year: int, month: int) -> tuple[bool, str]:
        """
        Constructs month_key, calls database_manager.set_book_status to "closed", and returns status.
        """
        try:
            month_key = f"{year:04d}-{month:02d}"
            success = database_manager.set_book_status(month_key, "closed")
            if success:
                return True, f"Books for {month_key} closed successfully."
            else:
                return False, f"Failed to close books for {month_key}."
        except Exception as e:
            return False, f"Error closing books for {month_key}: {str(e)}"

    def open_books_action(self, year: int, month: int) -> tuple[bool, str]:
        """
        Constructs month_key, calls database_manager.set_book_status to "open", and returns status.
        """
        try:
            month_key = f"{year:04d}-{month:02d}"
            success = database_manager.set_book_status(month_key, "open")
            if success:
                return True, f"Books for {month_key} re-opened successfully."
            else:
                return False, f"Failed to re-open books for {month_key}."
        except Exception as e:
            return False, f"Error re-opening books for {month_key}: {str(e)}"

    def get_filtered_members(self, name_filter: Optional[str], phone_filter: Optional[str]) -> list:
        """Fetches members based on name and/or phone filters."""
        return database_manager.get_all_members(name_filter=name_filter, phone_filter=phone_filter)

    def get_filtered_transaction_history(self, name_filter: Optional[str], phone_filter: Optional[str], join_date_filter: Optional[str]) -> list:
        """Fetches transaction history based on name, phone, and/or join date filters."""
        return database_manager.get_transactions_with_member_details(
            name_filter=name_filter,
            phone_filter=phone_filter,
            join_date_filter=join_date_filter
        )

    def get_active_plans(self) -> list:
        """Fetches all active plans."""
        return database_manager.get_all_plans()

    def get_all_plans_with_inactive(self) -> list:
        """Fetches all plans, including inactive ones."""
        return database_manager.get_all_plans_with_inactive()

    def get_all_activity_for_member(self, member_id: int) -> list:
        """Fetches all activity records for a given member_id."""
        return database_manager.get_all_activity_for_member(member_id)

    def deactivate_member_action(self, member_id: int) -> tuple[bool, str]:
        """Handles the action of deactivating a member."""
        try:
            # database_manager.deactivate_member now returns -> Tuple[bool, str]
            success, message = database_manager.deactivate_member(member_id)
            # Use the returned success and message directly
            return success, message
        except Exception as e:
            # This catch block can handle unexpected errors.
            return False, f"An unexpected error occurred while deactivating the member: {str(e)}"

    def delete_transaction_action(self, transaction_id: int) -> tuple[bool, str]:
        """Calls database_manager.delete_transaction and returns status."""
        try:
            success, message = database_manager.delete_transaction(transaction_id) # <-- Changed this line
            if success:
                return True, "Transaction deleted successfully."
            else:
                return False, message # <-- Changed this line
        except Exception as e:
            return False, f"An error occurred while deleting the transaction: {str(e)}"

    def delete_plan_action(self, plan_id: int) -> tuple[bool, str]:
        """Calls database_manager.delete_plan and returns its result or an error status."""
        try:
            # delete_plan itself returns a tuple (bool, str)
            success, message = database_manager.delete_plan(plan_id)
            return success, message
        except Exception as e:
            return False, f"An error occurred while deleting the plan: {str(e)}"

def main(page: ft.Page):
    page.title = "Kranos MMA Reporter"
    page.theme_mode = ft.ThemeMode.DARK

    controller = GuiController()

    tabs = ft.Tabs(
        tabs=[
            ft.Tab(
                text="Membership Management",
                content=ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text("Form Placeholder"),
                            expand=1,
                            bgcolor=ft.colors.BLUE_GREY_200,
                            padding=10,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(
                            content=ft.Text("Table Placeholder"),
                            expand=2,
                            bgcolor=ft.colors.BLUE_GREY_300,
                            padding=10,
                            alignment=ft.alignment.center,
                        ),
                    ]
                )
            ),
            ft.Tab(
                text="Membership History",
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Text("Filters Placeholder"),
                            expand=1,
                            bgcolor=ft.colors.GREEN_200,
                            padding=10,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(
                            content=ft.Text("Data Table Placeholder"),
                            expand=4,
                            bgcolor=ft.colors.GREEN_300,
                            padding=10,
                            alignment=ft.alignment.center,
                        ),
                    ]
                )
            ),
            ft.Tab(
                text="Plan Management",
                content=ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text("Plan Form Placeholder"),
                            expand=1,
                            bgcolor=ft.colors.AMBER_200,
                            padding=10,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(
                            content=ft.Text("Plan Table Placeholder"),
                            expand=2,
                            bgcolor=ft.colors.AMBER_300,
                            padding=10,
                            alignment=ft.alignment.center,
                        ),
                    ]
                )
            ),
            ft.Tab(
                text="Reporting",
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Text("Renewals Report Placeholder"),
                            expand=1,
                            bgcolor=ft.colors.TEAL_200,
                            padding=10,
                            alignment=ft.alignment.center,
                        ),
                        ft.Container(
                            content=ft.Text("Finance Report Placeholder"),
                            expand=1,
                            bgcolor=ft.colors.TEAL_300,
                            padding=10,
                            alignment=ft.alignment.center,
                        ),
                    ]
                )
            ),
            ft.Tab(
                text="Settings",
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Text("Settings Placeholder"),
                            expand=True,
                            bgcolor=ft.colors.ORANGE_200,
                            padding=10,
                            alignment=ft.alignment.center,
                        )
                    ]
                )
            ),
        ]
    )

    page.add(tabs)
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
