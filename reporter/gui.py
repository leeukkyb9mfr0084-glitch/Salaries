import customtkinter
from typing import Optional, List # For type hinting, List can be replaced by list in Python 3.9+
from tkinter import StringVar # Explicitly import StringVar
from datetime import datetime, date # Explicitly import datetime and date
from customtkinter import CTkFrame, CTkLabel, CTkEntry, CTkButton, CTkOptionMenu, CTkFont, CTkScrollableFrame
from tkcalendar import DateEntry
from reporter import database_manager


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
            success = database_manager.add_member_to_db(name, phone)
            if success:
                return True, "Member added successfully! Join date will be set with first activity."
            else:
                return False, "Failed to add member. Phone number may already exist."
        except Exception as e:
            return False, f"An error occurred: {str(e)}"

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
                success = database_manager.update_plan(plan_id, plan_name, duration_days)
                message = "Plan updated successfully!" if success else "Failed to update plan. Name might exist."
            else:  # Adding new plan
                new_plan_id = database_manager.add_plan(plan_name, duration_days)
                if new_plan_id:
                    success = True
                message = "Plan added successfully!" if success else "Failed to add plan. Name might exist."

            if success:
                updated_plans = database_manager.get_all_plans_with_inactive()
            return success, message, updated_plans
        except Exception as e:
            return False, f"An error occurred: {str(e)}", None

    def toggle_plan_status_action(self, plan_id: int, current_status: bool) -> tuple[bool, str, list | None]:
        """Activates or deactivates a plan."""
        new_status = not current_status
        success = database_manager.set_plan_active_status(plan_id, new_status)
        updated_plans = None
        message = ""
        if success:
            message = f"Plan status changed to {'Active' if new_status else 'Inactive'}."
            updated_plans = database_manager.get_all_plans_with_inactive()
        else:
            message = "Failed to update plan status."
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
            if amount_paid < 0:
                return False, "Error: Amount Paid cannot be negative."
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

            if success:
                return True, f"{membership_type} membership added successfully!"
            else:
                # This path might be taken if add_transaction itself returns False (e.g., DB constraint)
                return False, "Failed to add membership. Check logs or input."
        except Exception as e:
            # Log the exception e for debugging purposes if possible
            return False, f"An error occurred: {str(e)}"

    def generate_pending_renewals_action(self) -> tuple[bool, str, list | None]:
        """Fetches pending renewals for the current month."""
        from datetime import date
        import calendar

        today = date.today()
        current_date_str = today.strftime('%Y-%m-%d')
        month_name = calendar.month_name[today.month]
        year = today.year

        try:
            renewals = database_manager.get_pending_renewals(current_date_str)
            if renewals:
                return True, f"Found {len(renewals)} pending renewals for {month_name} {year}:", renewals
            else:
                return True, f"No pending renewals found for {month_name} {year}.", []
        except Exception as e:
            return False, f"Error generating report: {str(e)}", None

    def generate_finance_report_action(self) -> tuple[bool, str, float | None]:
        """Fetches and returns the finance report for the previous month."""
        from datetime import date, timedelta
        import calendar

        today = date.today()
        first_day_current_month = today.replace(day=1)
        last_day_previous_month = first_day_current_month - timedelta(days=1)
        prev_month = last_day_previous_month.month
        prev_year = last_day_previous_month.year
        prev_month_name = calendar.month_name[prev_month]

        try:
            total_revenue = database_manager.get_finance_report(prev_year, prev_month)
            if total_revenue is not None:
                return True, f"Total revenue for {prev_month_name} {prev_year}: ${total_revenue:.2f}", total_revenue
            else:
                return False, f"Could not generate finance report for {prev_month_name} {prev_year}. Check logs.", None
        except Exception as e:
            return False, f"Error generating finance report: {str(e)}", None

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


class App(customtkinter.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.controller = GuiController() # Instantiating controller

        # Initialize selection state variables to None
        self.selected_member_id = None
        self.selected_member_label_widget = None

        self.title("Kranos MMA Reporter")
        self.geometry("800x600")

        # Create Tabview
        self.tab_view = customtkinter.CTkTabview(self)
        self.tab_view.pack(expand=True, fill="both", padx=10, pady=10)

        # Add tabs
        self.tab_view.add("Membership Management")
        self.tab_view.add("Plan Management") # New Tab
        self.tab_view.add("Reporting")

        # Add placeholder content to tabs
        membership_tab = self.tab_view.tab("Membership Management")
        plan_management_tab = self.tab_view.tab("Plan Management") # New Tab
        reporting_tab = self.tab_view.tab("Reporting")

        # --- Membership Management Tab ---
        membership_tab = self.tab_view.tab("Membership Management")
        # self.membership_sub_tabview is created here but will be gridded in setup_membership_tab

        self.setup_membership_tab(membership_tab) # Pass the main tab

        # --- Plan Management Tab ---
        self.setup_plan_management_tab(plan_management_tab) # Setup for the new tab

        # --- Membership History Tab ---
        history_tab = self.tab_view.add("Membership History")
        self.setup_membership_history_tab(history_tab)

    # def populate_pt_member_dropdown(self): # REMOVED
    #     pass
    # def setup_pt_booking_frame(self, parent_frame): # REMOVED
    #    pass
    # def save_pt_booking_action(self): # REMOVED
    #     pass

    # --- Reporting Tab ---
        self.setup_reporting_tab(self.tab_view.tab("Reporting"))

    def setup_membership_history_tab(self, tab):
        """Configures the UI for the Membership History tab."""
        from reporter.database_manager import get_transactions_with_member_details # Local import

        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1) # Allow scrollable frame to expand

        # Main frame for the history tab
        history_main_frame = CTkFrame(tab, fg_color="transparent")
        history_main_frame.pack(expand=True, fill="both", padx=5, pady=5)
        history_main_frame.grid_columnconfigure(0, weight=1)
        history_main_frame.grid_rowconfigure(1, weight=1) # For the scrollable display area

        # Filter Controls Frame
        filter_controls_frame = CTkFrame(history_main_frame)
        filter_controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        # Configure columns for filter_controls_frame to distribute space
        filter_controls_frame.grid_columnconfigure(0, weight=1) # Name filter
        filter_controls_frame.grid_columnconfigure(1, weight=1) # Phone filter
        filter_controls_frame.grid_columnconfigure(2, weight=1) # Date filter
        filter_controls_frame.grid_columnconfigure(3, weight=0) # Filter button
        filter_controls_frame.grid_columnconfigure(4, weight=0) # Clear button

        # Name Filter
        CTkLabel(filter_controls_frame, text="Filter by Name:").grid(row=0, column=0, padx=(0,5), pady=5, sticky="w")
        self.history_name_filter_entry = CTkEntry(filter_controls_frame, placeholder_text="Name")
        self.history_name_filter_entry.grid(row=1, column=0, padx=(0,5), pady=5, sticky="ew")

        # Phone Filter
        CTkLabel(filter_controls_frame, text="Filter by Phone:").grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.history_phone_filter_entry = CTkEntry(filter_controls_frame, placeholder_text="Phone")
        self.history_phone_filter_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Join Date Filter
        CTkLabel(filter_controls_frame, text="Filter by Join Date:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.history_join_date_picker = DateEntry(filter_controls_frame,
                                                  date_pattern='y-mm-dd',
                                                  font=CTkFont(size=12),
                                                  borderwidth=2)
        # No default date for filter, allow it to be empty.
        # The DateEntry widget itself will be empty by default.
        self.history_join_date_picker.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

        # Filter Button
        self.history_filter_button = CTkButton(filter_controls_frame, text="Filter", command=self.apply_history_filters)
        self.history_filter_button.grid(row=1, column=3, padx=5, pady=5)

        # Clear Filters Button
        self.history_clear_button = CTkButton(filter_controls_frame, text="Clear", command=self.clear_history_filters)
        self.history_clear_button.grid(row=1, column=4, padx=5, pady=5)

        # Display Area for Transaction Records
        self.history_scrollable_frame = CTkScrollableFrame(history_main_frame)
        self.history_scrollable_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")

        initial_transactions = self.controller.get_filtered_transaction_history(None, None, None) # Initial data load
        self.refresh_membership_history_display(initial_transactions)

    def refresh_membership_history_display(self, transactions: list):
        """Refreshes the transaction history display with the provided transactions list."""
        # from reporter.database_manager import get_transactions_with_member_details # No longer needed here

        # name_filter = self.history_name_filter_entry.get().strip() if hasattr(self, 'history_name_filter_entry') else None
        # phone_filter = self.history_phone_filter_entry.get().strip() if hasattr(self, 'history_phone_filter_entry') else None
        #
        # join_date_str = ""
        # if hasattr(self, 'history_join_date_picker'):
        #     join_date_str = self.history_join_date_picker.get() # This gets the string representation
        #
        # join_date_filter = join_date_str.strip() if join_date_str else None
        #
        #
        # # Clear empty strings to None for database function
        # name_filter = name_filter if name_filter else None
        # phone_filter = phone_filter if phone_filter else None
        # join_date_filter = join_date_filter if join_date_filter else None
        #
        # transactions = get_transactions_with_member_details(
        #     name_filter=name_filter,
        #     phone_filter=phone_filter,
        #     join_date_filter=join_date_filter
        # )

        for widget in self.history_scrollable_frame.winfo_children():
            widget.destroy()

        if not transactions:
            CTkLabel(self.history_scrollable_frame, text="No transaction records found.").pack(pady=10)
            return

        for i, record in enumerate(transactions):
            # record structure: (t.*, m.client_name, m.phone, m.join_date)
            # Assuming t.* includes: transaction_id, member_id, transaction_type, plan_id,
            # payment_date, start_date, end_date, amount_paid, payment_method, sessions
            # Indices for m.client_name, m.phone, m.join_date will be after transaction table columns.
            # Let's assume transaction table has 10 columns (0-9), so client_name is 10, phone is 11, join_date is 12

            transaction_id, member_id, transaction_type, plan_id, payment_date, start_date, end_date, amount_paid, payment_method, sessions, client_name, phone, join_date = record

            detail_text = f"Name: {client_name} (Ph: {phone}, Joined: {join_date})\n" \
                          f"Type: {transaction_type} | Amount: ${amount_paid:.2f} | Paid: {payment_date}\n" \
                          f"Active: {start_date} to {end_date if end_date else 'N/A'}"
            if transaction_type == "Group Class":
                # Fetch plan name if needed, or assume plan_id is sufficient for now
                detail_text += f" | Plan ID: {plan_id}"
                if payment_method: detail_text += f" | Method: {payment_method}"
            elif transaction_type == "Personal Training":
                detail_text += f" | Sessions: {sessions if sessions else 'N/A'}"

            record_label = CTkLabel(self.history_scrollable_frame, text=detail_text, anchor="w", justify="left")
            record_label.pack(padx=5, pady=3, fill="x", expand=True)
            if i < len(transactions) - 1:
                sep = CTkFrame(self.history_scrollable_frame, height=1, fg_color="gray70")
                sep.pack(fill="x", padx=5, pady=2)

    def apply_history_filters(self):
        """Applies the filters from the history tab and refreshes the display."""
        name_filter = self.history_name_filter_entry.get().strip()
        phone_filter = self.history_phone_filter_entry.get().strip()
        join_date_str = self.history_join_date_picker.get()

        # Set filters to None if they are empty strings
        name_filter = name_filter if name_filter else None
        phone_filter = phone_filter if phone_filter else None
        join_date_filter = join_date_str.strip() if join_date_str else None

        filtered_transactions = self.controller.get_filtered_transaction_history(name_filter, phone_filter, join_date_filter)
        self.refresh_membership_history_display(filtered_transactions)

    def clear_history_filters(self):
        """Clears all filter entries in the history tab and refreshes the display."""
        if hasattr(self, 'history_name_filter_entry'): self.history_name_filter_entry.delete(0, "end")
        if hasattr(self, 'history_phone_filter_entry'): self.history_phone_filter_entry.delete(0, "end")
        if hasattr(self, 'history_join_date_picker'):
            self.history_join_date_picker.delete(0, "end")

        all_transactions = self.controller.get_filtered_transaction_history(None, None, None)
        self.refresh_membership_history_display(all_transactions)

    def setup_membership_tab(self, tab):
        """Configures the UI for the Membership Management tab."""
        # Import database functions locally within methods where they are needed
        # to avoid potential circular imports and keep dependencies clear.
        from reporter.database_manager import get_all_members # add_member_to_db is used in an action method
        # CTk* elements are now imported globally

        # Top-level frame for the Membership Management tab
        # This frame will be split into two columns:
        # Column 0: Sub-tabs for "Add Member", "Add Membership"
        # Column 1: Display area for "All Members" and "Membership History"
        top_level_frame = customtkinter.CTkFrame(tab, fg_color="transparent")
        top_level_frame.pack(expand=True, fill="both") # Fill the entire 'tab'
        top_level_frame.grid_columnconfigure(0, weight=1) # Column for sub-tabs (e.g., Add Member)
        top_level_frame.grid_columnconfigure(1, weight=2) # Column for display area (e.g., All Members list), give more space
        top_level_frame.grid_rowconfigure(0, weight=1)    # Single row to contain both columns

        # ADD THESE LINES HERE
        self.membership_sub_tabview = customtkinter.CTkTabview(top_level_frame)
        self.add_member_sub_tab = self.membership_sub_tabview.add("Add Member")
        self.add_membership_sub_tab = self.membership_sub_tabview.add("Add Membership")

        # Grid the self.membership_sub_tabview (created in __init__) into column 0 of top_level_frame
        # Its master is 'tab' (the main "Membership Management" tab from CTkTabview).
        self.membership_sub_tabview.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")


        # --- "Add Member" Sub-tab Content (goes into self.add_member_sub_tab) ---
        # self.add_member_sub_tab is a tab (a frame) within self.membership_sub_tabview.

        # Frame for Adding New Members, this is the main content of the "Add Member" sub-tab
        self.add_member_frame = customtkinter.CTkFrame(self.add_member_sub_tab) # Parent is the "Add Member" sub-tab
        self.add_member_frame.pack(expand=True, fill="both", padx=10, pady=10) # Use pack to fill the sub-tab

        # Configure grid for content within add_member_frame (e.g., labels, entries)
        self.add_member_frame.grid_columnconfigure(1, weight=1) # Allows entry fields to expand

        add_member_title = CTkLabel(self.add_member_frame, text="Add New Member", font=CTkFont(weight="bold"))
        add_member_title.grid(row=0, column=0, columnspan=2, padx=10, pady=(10,15))

        name_label = CTkLabel(self.add_member_frame, text="Name:")
        name_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.name_entry = CTkEntry(self.add_member_frame)
        self.name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        phone_label = CTkLabel(self.add_member_frame, text="Phone:")
        phone_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.phone_entry = CTkEntry(self.add_member_frame)
        self.phone_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        save_button = CTkButton(self.add_member_frame, text="Save Member", command=self.on_save_member_click)
        save_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

        self.member_status_label = CTkLabel(self.add_member_frame, text="", text_color="red")
        self.member_status_label.grid(row=4, column=0, columnspan=2, padx=10, pady=5)

        # --- Add Group Membership & PT Booking Frames ---
        # These will be moved to the "Add Membership" sub-tab (self.add_membership_sub_tab) in Task 2.
        # For now, their direct setup calls from here are commented out.
        # The methods setup_group_membership_frame and setup_pt_booking_frame still exist
        # but are not called from setup_membership_tab for now.
        # self.setup_group_membership_frame(self.add_membership_sub_tab) # Example for next task
        # self.setup_pt_booking_frame(self.add_membership_sub_tab) # Example for next task

        # --- "Add Membership" Sub-tab Content (goes into self.add_membership_sub_tab) ---
        self.add_membership_frame = customtkinter.CTkFrame(self.add_membership_sub_tab)
        self.add_membership_frame.pack(expand=True, fill="both", padx=10, pady=10)
        self.add_membership_frame.grid_columnconfigure(1, weight=1) # For entry widgets to expand

        # Title for the "Add Membership" form
        add_membership_title = CTkLabel(self.add_membership_frame, text="Add or Update Membership", font=CTkFont(weight="bold"))
        add_membership_title.grid(row=0, column=0, columnspan=2, padx=10, pady=(10,15))

        # Membership Type Dropdown
        self.membership_type_label = CTkLabel(self.add_membership_frame, text="Membership Type:") # Made it self. for potential access
        self.membership_type_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.membership_type_var = StringVar(value="Group Class")
        self.membership_type_dropdown = CTkOptionMenu(self.add_membership_frame,
                                                      variable=self.membership_type_var,
                                                      values=["Group Class", "Personal Training"],
                                                      command=self.on_membership_type_change)
        self.membership_type_dropdown.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # --- Unified Form Fields ---
        self.current_form_row = 2 # Start gridding new fields from this row (tracks the next available row)

        # Member Dropdown
        self.member_label = CTkLabel(self.add_membership_frame, text="Select Member:")
        self.member_label.grid(row=self.current_form_row, column=0, padx=10, pady=5, sticky="w")
        self.membership_member_dropdown_var = customtkinter.StringVar(value="Select Member")
        self.membership_member_dropdown = CTkOptionMenu(self.add_membership_frame, variable=self.membership_member_dropdown_var, values=["Loading..."])
        self.membership_member_dropdown.grid(row=self.current_form_row, column=1, padx=10, pady=5, sticky="ew")
        self.member_name_to_id = {}
        self.current_form_row += 1

        # Plan Dropdown (for Group Class) - Store its row for show/hide
        self.plan_label = CTkLabel(self.add_membership_frame, text="Select Plan:")
        self.membership_plan_dropdown_var = customtkinter.StringVar(value="Select Plan")
        self.membership_plan_dropdown = CTkOptionMenu(self.add_membership_frame, variable=self.membership_plan_dropdown_var, values=["Loading..."])
        self.plan_name_to_id = {}
        self.current_plan_row = self.current_form_row # Actual row this will occupy when visible
        # Initial gridding for plan_label and membership_plan_dropdown will be handled by on_membership_type_change
        self.current_form_row += 1

        # Number of Sessions Entry (for Personal Training) - Store its row for show/hide
        self.sessions_label = CTkLabel(self.add_membership_frame, text="Number of Sessions:")
        self.pt_sessions_entry = CTkEntry(self.add_membership_frame, placeholder_text="e.g., 10")
        self.current_sessions_row = self.current_plan_row # PT sessions will occupy the same row as GC Plan
        # Initial gridding for sessions_label and pt_sessions_entry will be handled by on_membership_type_change
        # Note: current_form_row is not incremented here if they share a row. If they need separate rows, adjust.

        # Payment Date Entry - Store its row for show/hide
        self.payment_date_label = CTkLabel(self.add_membership_frame, text="Payment Date:")
        self.payment_date_picker = DateEntry(self.add_membership_frame,
                                             date_pattern='y-mm-dd',
                                             font=CTkFont(size=12), # Basic font styling
                                             borderwidth=2)
        self.payment_date_picker.set_date(date.today())
        self.current_payment_date_row = self.current_form_row
        # Initial gridding for payment_date_label and payment_date_picker handled by on_membership_type_change
        self.current_form_row += 1

        # Start Date Entry (Always Visible)
        self.start_date_label = CTkLabel(self.add_membership_frame, text="Start Date:")
        self.start_date_label.grid(row=self.current_form_row, column=0, padx=10, pady=5, sticky="w")
        self.start_date_picker = DateEntry(self.add_membership_frame,
                                           date_pattern='y-mm-dd',
                                           font=CTkFont(size=12),
                                           borderwidth=2)
        self.start_date_picker.set_date(date.today())
        self.start_date_picker.grid(row=self.current_form_row, column=1, padx=10, pady=5, sticky="ew")
        self.current_form_row += 1

        # Amount Paid Entry (Always Visible)
        self.amount_paid_label = CTkLabel(self.add_membership_frame, text="Amount Paid:")
        self.amount_paid_label.grid(row=self.current_form_row, column=0, padx=10, pady=5, sticky="w")
        self.amount_paid_entry = CTkEntry(self.add_membership_frame, placeholder_text="e.g., 1500.00")
        self.amount_paid_entry.grid(row=self.current_form_row, column=1, padx=10, pady=5, sticky="ew")
        self.current_form_row += 1

        # Payment Method Entry - Store its row for show/hide
        self.payment_method_label = CTkLabel(self.add_membership_frame, text="Payment Method:")
        self.payment_method_entry = CTkEntry(self.add_membership_frame, placeholder_text="e.g., GPay, Cash")
        self.current_payment_method_row = self.current_form_row
        # Initial gridding for payment_method_label and payment_method_entry handled by on_membership_type_change
        self.current_form_row += 1

        # Save Button
        self.save_membership_button = CTkButton(self.add_membership_frame, text="Save Membership", command=self.on_save_membership_click)
        self.save_membership_button.grid(row=self.current_form_row, column=0, columnspan=2, padx=10, pady=20)
        self.current_form_row += 1

        # Status Label
        self.membership_status_label = CTkLabel(self.add_membership_frame, text="", text_color="red") # Renamed
        self.membership_status_label.grid(row=self.current_form_row, column=0, columnspan=2, padx=10, pady=5)

        # Call on_membership_type_change to set initial visibility of fields
        self.on_membership_type_change(self.membership_type_var.get())


        # --- Column 1: Display Area (within top_level_frame) ---
        # This frame is for displaying member lists and membership history.
        # It's parented to top_level_frame and placed in column 1.
        display_frame = customtkinter.CTkFrame(top_level_frame)
        display_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew") # Gridded into column 1 of top_level_frame

        # Configure grid for content within display_frame
        display_frame.grid_rowconfigure(1, weight=0) # For filter_controls_frame
        display_frame.grid_rowconfigure(2, weight=1) # Allows members_scrollable_frame to expand
        display_frame.grid_rowconfigure(4, weight=1) # Allows membership_history_frame to expand
        display_frame.grid_columnconfigure(0, weight=1) # Allows content within to expand horizontally

        # Title for the "All Members" list
        display_title = CTkLabel(display_frame, text="All Members", font=CTkFont(weight="bold"))
        display_title.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Filter Controls Frame
        filter_controls_frame = CTkFrame(display_frame)
        filter_controls_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")
        filter_controls_frame.grid_columnconfigure((0, 1), weight=1) # Name and Phone entry expand
        filter_controls_frame.grid_columnconfigure((2, 3), weight=0) # Buttons take their own space

        self.name_filter_entry = CTkEntry(filter_controls_frame, placeholder_text="Filter by Name")
        self.name_filter_entry.grid(row=0, column=0, padx=(0,5), pady=5, sticky="ew")

        self.phone_filter_entry = CTkEntry(filter_controls_frame, placeholder_text="Filter by Phone")
        self.phone_filter_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.filter_button = CTkButton(filter_controls_frame, text="Filter", command=self.apply_member_filters)
        self.filter_button.grid(row=0, column=2, padx=5, pady=5)

        self.clear_button = CTkButton(filter_controls_frame, text="Clear", command=self.clear_member_filters)
        self.clear_button.grid(row=0, column=3, padx=(5,0), pady=5)

        # Scrollable frame to display the list of all members
        self.members_scrollable_frame = CTkScrollableFrame(display_frame)
        self.members_scrollable_frame.grid(row=2, column=0, padx=10, pady=(0,10), sticky="nsew")

        # --- Membership History Frame (Below All Members) ---
        history_title = CTkLabel(display_frame, text="Membership History", font=CTkFont(weight="bold"))
        history_title.grid(row=3, column=0, padx=10, pady=(10,0), sticky="ew")

        # Scrollable frame to display history for a selected member
        self.membership_history_frame = CTkScrollableFrame(display_frame)
        self.membership_history_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")

        # Initialize data displays
        # self.display_all_members() # This will be called via clear_member_filters or apply_member_filters
        initial_members = self.controller.get_filtered_members(None, None) # Initial load
        self.display_all_members(initial_members)
        self.populate_member_dropdown() # Populate the unified member dropdown
        self.populate_plan_dropdown()   # Populate plan dropdown (used by Group Class)
        # self.populate_pt_member_dropdown() # REMOVE THIS CALL - PT dropdown is gone

        self.display_membership_history([], None) # Show placeholder message in history view

    def apply_member_filters(self):
        """Applies filters to the member list display."""
        name_query = self.name_filter_entry.get().strip()
        phone_query = self.phone_filter_entry.get().strip()
        filtered_members = self.controller.get_filtered_members(name_query if name_query else None, phone_query if phone_query else None)
        self.display_all_members(filtered_members)

    def clear_member_filters(self):
        """Clears active member filters and refreshes the list."""
        self.name_filter_entry.delete(0, "end")
        self.phone_filter_entry.delete(0, "end")
        all_members = self.controller.get_filtered_members(None, None)
        self.display_all_members(all_members)

    def setup_plan_management_tab(self, tab):
        """Configures the UI for the Plan Management tab."""
        from reporter import database_manager # Local import for DB functions

        tab.grid_columnconfigure(0, weight=1) # Configure grid for the tab
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(0, weight=1)

        # --- Frame for Add/Edit Plan ---
        self.plan_form_frame = CTkFrame(tab)
        self.plan_form_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.plan_form_frame.grid_columnconfigure(1, weight=1)

        CTkLabel(self.plan_form_frame, text="Add/Edit Plan", font=CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # Plan ID (hidden, for editing)
        self.current_plan_id_var = StringVar(value="") # To store ID of plan being edited

        # Plan Name
        CTkLabel(self.plan_form_frame, text="Plan Name:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.plan_name_entry = CTkEntry(self.plan_form_frame)
        self.plan_name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # Duration
        CTkLabel(self.plan_form_frame, text="Duration (days):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.plan_duration_entry = CTkEntry(self.plan_form_frame)
        self.plan_duration_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # Save Plan Button
        self.save_plan_button = CTkButton(self.plan_form_frame, text="Save Plan", command=self.on_save_plan_click)
        self.save_plan_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

        # Status Label for plan operations
        self.plan_status_label = CTkLabel(self.plan_form_frame, text="", font=CTkFont(size=12))
        self.plan_status_label.grid(row=4, column=0, columnspan=2, padx=10, pady=5)

        # --- Frame for Displaying Plans ---
        self.plans_display_frame = CTkScrollableFrame(tab)
        self.plans_display_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Initial load of plans
        initial_plans = self.controller.get_all_plans_with_inactive()
        self.load_plans_display(initial_plans)

    def load_plans_display(self, plans_list: list):
        """Loads and displays all plans in the plans_display_frame using the provided list."""
        # from reporter import database_manager # No longer needed here
        # Clear existing widgets
        for widget in self.plans_display_frame.winfo_children():
            widget.destroy()

        # plans = database_manager.get_all_plans_with_inactive() # Fetch all plans
        if not plans_list:
            CTkLabel(self.plans_display_frame, text="No plans found.").pack(padx=10, pady=10)
            return

        for i, plan_data in enumerate(plans_list):
            plan_id, name, duration, is_active = plan_data
            status_text = "Active" if is_active else "Inactive"

            plan_item_frame = CTkFrame(self.plans_display_frame, fg_color="transparent")
            plan_item_frame.pack(fill="x", expand=True, pady=2)

            info_text = f"Name: {name} | Duration: {duration} days | Status: {status_text}"
            CTkLabel(plan_item_frame, text=info_text, anchor="w").pack(side="left", padx=5, expand=True, fill="x")

            edit_button = CTkButton(plan_item_frame, text="Edit", width=60,
                                     command=lambda p_id=plan_id, p_name=name, p_duration=duration: self.edit_plan_action(p_id, p_name, p_duration))
            edit_button.pack(side="right", padx=5)

            toggle_text = "Deactivate" if is_active else "Activate"
            toggle_button = CTkButton(plan_item_frame, text=toggle_text, width=90,
                                       command=lambda p_id=plan_id, current_stat=is_active: self.on_toggle_plan_status_click(p_id, current_stat))
            toggle_button.pack(side="right", padx=5)

            if i < len(plans_list) - 1:
                sep = CTkFrame(self.plans_display_frame, height=1, fg_color="gray70")
                sep.pack(fill="x", padx=5, pady=2)

    def on_save_plan_click(self):
        """Handles the click event for saving a plan."""
        plan_name = self.plan_name_entry.get().strip()
        duration_str = self.plan_duration_entry.get().strip()
        plan_id_to_update = self.current_plan_id_var.get()

        success, message, updated_plans = self.controller.save_plan_action(plan_name, duration_str, plan_id_to_update)

        self.plan_status_label.configure(text=message, text_color="green" if success else "red")

        if success:
            self.clear_plan_form()
            if updated_plans is not None: # Should always be a list on success
                self.load_plans_display(updated_plans)
            self.populate_plan_dropdown()

    def on_toggle_plan_status_click(self, plan_id: int, current_status: bool):
        """Handles the click event for toggling a plan's active status."""
        success, message, updated_plans = self.controller.toggle_plan_status_action(plan_id, current_status)
        self.plan_status_label.configure(text=message, text_color="green" if success else "red")

        if success:
            if updated_plans is not None: # Should always be a list on success
                self.load_plans_display(updated_plans)
            self.populate_plan_dropdown()

    def edit_plan_action(self, plan_id, name, duration):
        """Populates the plan form for editing."""
        self.current_plan_id_var.set(str(plan_id))
        self.plan_name_entry.delete(0, "end")
        self.plan_name_entry.insert(0, name)
        self.plan_duration_entry.delete(0, "end")
        self.plan_duration_entry.insert(0, str(duration))
        self.plan_status_label.configure(text="") # Clear status

    def clear_plan_form(self):
        """Clears the plan add/edit form."""
        self.current_plan_id_var.set("")
        self.plan_name_entry.delete(0, "end")
        self.plan_duration_entry.delete(0, "end")
        self.plan_status_label.configure(text="")


    def setup_reporting_tab(self, tab):
        """Configures the UI for the Reporting tab."""
        # Import UI elements and database functions locally
        # from reporter.database_manager import get_pending_renewals # Used in action method
        # from datetime import datetime # Not strictly needed here, but good for context
        # CTk* elements are now imported globally

        # Configure grid layout for the reporting tab
        tab.grid_columnconfigure(0, weight=1) # Single column that expands
        tab.grid_rowconfigure(0, weight=0)    # Row for Pending Renewals title and button
        tab.grid_rowconfigure(1, weight=0)    # Row for Pending Renewals status label
        tab.grid_rowconfigure(2, weight=1)    # Row for Pending Renewals scrollable results
        tab.grid_rowconfigure(3, weight=0)    # Row for Finance Report section
        # tab.grid_rowconfigure(4, weight=0) # Potentially for finance report results/status if not packed

        # --- Frame for Pending Renewals ---
        # This section sets up the UI for generating and displaying pending membership renewals.
        renewals_frame = CTkFrame(tab) # Main container for this report section
        renewals_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        renewals_frame.grid_columnconfigure(0, weight=1) # Allows content to center or expand

        renewals_title = CTkLabel(renewals_frame, text="Pending Renewals Report", font=CTkFont(weight="bold"))
        renewals_title.pack(pady=(5,10)) # pack is used here for simpler vertical layout

        generate_button = CTkButton(renewals_frame, text="Generate Pending Renewals for Current Month",
                                    command=self.on_generate_pending_renewals_click)
        generate_button.pack(pady=5)

        # Status label to provide feedback on the renewals report generation
        self.pending_renewals_status_label = CTkLabel(tab, text="")
        self.pending_renewals_status_label.grid(row=1, column=0, padx=10, pady=(0,5), sticky="ew")

        # Scrollable frame to display the list of pending renewals
        self.pending_renewals_frame = CTkScrollableFrame(tab)
        self.pending_renewals_frame.grid(row=2, column=0, padx=10, pady=(0,10), sticky="nsew")

        # --- Frame for Monthly Finance Report (below Pending Renewals) ---
        # This section sets up the UI for generating and displaying the monthly finance report.
        finance_report_frame = CTkFrame(tab) # Main container for this report section
        finance_report_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        finance_report_frame.grid_columnconfigure(0, weight=1) # Allows content to center or expand

        finance_title = CTkLabel(finance_report_frame, text="Monthly Finance Report", font=CTkFont(weight="bold"))
        finance_title.pack(pady=(5,10))

        generate_finance_button = CTkButton(finance_report_frame, text="Generate Last Month's Finance Report",
                                            command=self.on_generate_finance_report_click)
        generate_finance_button.pack(pady=5)

        # Label to display the finance report result or status messages
        self.finance_report_label = CTkLabel(finance_report_frame, text="Finance report will appear here.", font=CTkFont(size=14))
        self.finance_report_label.pack(pady=10)


    # def setup_group_membership_frame(self, parent_frame): # Method removed
    #     pass
    # def setup_pt_booking_frame(self, parent_frame): # Method removed
    #    pass


    def on_membership_type_change(self, selection):
        """Shows/hides form fields based on selected membership type."""
        # Ensure all widgets are treated as instance variables (e.g., self.plan_label)
        if selection == "Group Class":
            self.plan_label.grid(row=self.current_plan_row, column=0, padx=10, pady=5, sticky="w")
            self.membership_plan_dropdown.grid(row=self.current_plan_row, column=1, padx=10, pady=5, sticky="ew")

            self.payment_date_label.grid(row=self.current_payment_date_row, column=0, padx=10, pady=5, sticky="w")
            self.payment_date_picker.grid(row=self.current_payment_date_row, column=1, padx=10, pady=5, sticky="ew")

            self.payment_method_label.grid(row=self.current_payment_method_row, column=0, padx=10, pady=5, sticky="w")
            self.payment_method_entry.grid(row=self.current_payment_method_row, column=1, padx=10, pady=5, sticky="ew")

            # Hide PT specific fields
            if hasattr(self, 'sessions_label'): self.sessions_label.grid_remove()
            if hasattr(self, 'pt_sessions_entry'): self.pt_sessions_entry.grid_remove()

        elif selection == "Personal Training":
            if hasattr(self, 'plan_label'): self.plan_label.grid_remove()
            if hasattr(self, 'membership_plan_dropdown'): self.membership_plan_dropdown.grid_remove()

            # Payment date might be hidden or considered same as start date for PT
            if hasattr(self, 'payment_date_label'): self.payment_date_label.grid_remove()
            if hasattr(self, 'payment_date_picker'): self.payment_date_picker.grid_remove()

            if hasattr(self, 'payment_method_label'): self.payment_method_label.grid_remove()
            if hasattr(self, 'payment_method_entry'): self.payment_method_entry.grid_remove()

            # Show PT specific fields
            self.sessions_label.grid(row=self.current_sessions_row, column=0, padx=10, pady=5, sticky="w")
            self.pt_sessions_entry.grid(row=self.current_sessions_row, column=1, padx=10, pady=5, sticky="ew")

        # Ensure common fields remain visible (they are gridded during setup and not removed here)
        # self.start_date_label.grid()
        # self.start_date_entry.grid()
        # self.amount_paid_label.grid()
        # self.amount_paid_entry.grid()

    def populate_member_dropdown(self):
        """Populates the member selection dropdown with data from the database using the controller.
        This dropdown is now used in the unified 'Add Membership' form."""
        # from reporter.database_manager import get_all_members # No longer needed
        members = self.controller.get_filtered_members(None, None)
        self.member_name_to_id = {f"{m[1]} (ID: {m[0]})": m[0] for m in members}
        member_names_display = list(self.member_name_to_id.keys())

        # Ensure the dropdown variable and widget are initialized (should be done in setup_membership_tab)
        if not hasattr(self, 'membership_member_dropdown_var'):
            self.membership_member_dropdown_var = customtkinter.StringVar()
        if not hasattr(self, 'membership_member_dropdown'):
             # This should not happen if setup is correct
            print("Error: membership_member_dropdown not initialized before populating.")
            return

        if not member_names_display:
            member_names_display = ["No members available"]
            self.membership_member_dropdown_var.set(member_names_display[0])
        else:
            # Set default selection to the first member or a generic prompt if list is not empty
            self.membership_member_dropdown_var.set(member_names_display[0])
        self.membership_member_dropdown.configure(values=member_names_display)


    def populate_plan_dropdown(self):
        """Populates the plan selection dropdown with active plan data from the database via the controller."""
        # from reporter.database_manager import get_all_plans # No longer needed
        plans = self.controller.get_active_plans() # Fetches (plan_id, plan_name, duration_days)
        self.plan_name_to_id = {f"{p[1]} | {p[2]} days": p[0] for p in plans}
        plan_names_display = list(self.plan_name_to_id.keys())

        if not plan_names_display:
            plan_names_display = ["No plans available"] # Placeholder if no plans
            self.membership_plan_dropdown_var.set(plan_names_display[0])
        else:
            # Set default selection to the first plan or a generic prompt
            self.membership_plan_dropdown_var.set(plan_names_display[0])
        # Update the dropdown menu with the new list of plan names
        self.membership_plan_dropdown.configure(values=plan_names_display)

    def display_all_members(self, members_list: list):
        """Clears and re-populates the scrollable frame with member data using the provided list. Makes member labels clickable."""
        # from reporter.database_manager import get_all_members # No longer needed here

        # Check if the previously selected label widget still exists; if not, clear the reference
        if self.selected_member_label_widget and not self.selected_member_label_widget.winfo_exists():
            self.selected_member_id = None
            self.selected_member_label_widget = None

        # Clear existing widgets in the frame before repopulating
        for widget in self.members_scrollable_frame.winfo_children():
            widget.destroy()

        # members = get_all_members(name_filter=name_filter, phone_filter=phone_filter) # Fetch members with filter
        if not members_list:
            # Display a message if no members are found
            no_members_label = customtkinter.CTkLabel(self.members_scrollable_frame, text="No members found.")
            no_members_label.pack(padx=10, pady=10)
            # If a member was selected, but now the list is empty (e.g., if deletion was possible)
            if self.selected_member_id:
                self.selected_member_id = None
                if self.selected_member_label_widget:
                    # Reset the appearance of the previously selected label (if any)
                    self.selected_member_label_widget.configure(fg_color="transparent")
                    self.selected_member_label_widget = None
                self.display_membership_history(None) # Clear history display
            return

        # Iterate through members and create labels for each
        for i, member_data in enumerate(members):
            member_id, client_name, phone, join_date = member_data
            detail_text = f"ID: {member_id} | Name: {client_name} | Phone: {phone} | Joined: {join_date}"

            # Using a frame for each member label to help with layout and potential future additions (e.g., buttons per member)
            member_label_frame = customtkinter.CTkFrame(self.members_scrollable_frame, fg_color="transparent")
            member_label_frame.pack(fill="x", expand=True)

            member_label = customtkinter.CTkLabel(member_label_frame, text=detail_text, anchor="w", cursor="hand2") # 'hand2' cursor on hover
            member_label.pack(padx=5, pady=2, fill="x", expand=True)

            # Bind a click event to each member label.
            # A lambda function is used to pass the specific member_id and the label widget itself to the handler.
            member_label.bind("<Button-1>", lambda event, m_id=member_id, lbl=member_label: self.handle_member_selection(event, m_id, lbl))

            # If this member is the currently selected one, highlight their label
            if self.selected_member_id == member_id:
                member_label.configure(fg_color="gray20") # Highlight color
                self.selected_member_label_widget = member_label # Store this label as the selected one

            # Add a visual separator between member entries, except for the last one
            if i < len(members) - 1:
                sep = customtkinter.CTkFrame(self.members_scrollable_frame, height=1, fg_color="gray70")
                sep.pack(fill="x", padx=5, pady=2)

        # If the previously selected member is no longer in the (updated) list,
        # reset selection and clear history. This is relevant if members could be deleted.
        if self.selected_member_id and not any(m[0] == self.selected_member_id for m in members_list):
            self.selected_member_id = None
            self.selected_member_label_widget = None # It's already gone from display, so no need to change color
            self.display_membership_history(None)


    def handle_member_selection(self, event, member_id, label_widget):
        """Handles click on a member label to display their membership history and highlight selection."""
        if self.selected_member_label_widget and self.selected_member_label_widget != label_widget:
            if self.selected_member_label_widget.winfo_exists():
                self.selected_member_label_widget.configure(fg_color="transparent")
            else:
                self.selected_member_label_widget = None

        self.selected_member_id = member_id
        self.selected_member_label_widget = label_widget
        label_widget.configure(fg_color="gray20")

        history_data = self.controller.get_all_activity_for_member(member_id)
        self.display_membership_history(history_data, member_id)

    def display_membership_history(self, history_records: list, member_id: Optional[int] = None):
        """Displays all activity for the given member_id using the provided history_records."""
        # from reporter.database_manager import get_all_activity_for_member # No longer needed here

        for widget in self.membership_history_frame.winfo_children():
            widget.destroy()

        if not history_records:
            if member_id is not None: # A specific member was selected, but they have no history
                message_text = "No activity history found for this member."
            else: # No member selected, or initial state
                message_text = "Select a member to see their activity history."
            no_history_label = customtkinter.CTkLabel(self.membership_history_frame, text=message_text)
            no_history_label.pack(padx=10, pady=10)
            return

        # history_records = get_all_activity_for_member(member_id) # Logic moved
        for i, record in enumerate(history_records):
            # New tuple structure:
            # (activity_type, name_or_description, payment_date, start_date, end_date, amount_paid, payment_method_or_sessions, activity_id)
            activity_type, name_or_description, payment_date, start_date, end_date, amount_paid, payment_method_or_sessions, _ = record

            history_text = ""
            if activity_type == 'Group Class':
                history_text = (f"Type: {activity_type} - Plan: {name_or_description} | Paid: {amount_paid:.2f} ({payment_method_or_sessions})\n"
                                f"From: {start_date} To: {end_date if end_date else 'N/A'} (Paid on: {payment_date})")
            elif activity_type == 'Personal Training':
                history_text = (f"Type: {activity_type} - Sessions: {payment_method_or_sessions} | Paid: {amount_paid:.2f}\n"
                                f"Date: {start_date} (Paid on: {payment_date})")
            else:
                history_text = "Unknown activity type."

            history_label = customtkinter.CTkLabel(self.membership_history_frame, text=history_text, anchor="w", justify="left")
            history_label.pack(padx=5, pady=3, fill="x", expand=True)

            if i < len(history_records) - 1:
                sep = customtkinter.CTkFrame(self.membership_history_frame, height=1, fg_color="gray70")
                sep.pack(fill="x", padx=5, pady=2)

    def on_generate_pending_renewals_click(self):
        """Handles click for generating pending renewals report."""
        success, message, renewals_data = self.controller.generate_pending_renewals_action()

        # Determine color: green for success, orange for "no renewals", red for error
        color = "green"
        if not success:
            color = "red"
        elif not renewals_data: # Success but no data
            color = "orange"

        self.pending_renewals_status_label.configure(text=message, text_color=color)

        # Clear previous results from the scrollable frame
        for widget in self.pending_renewals_frame.winfo_children():
            widget.destroy()

        if success and renewals_data:
            for i, record in enumerate(renewals_data):
                client_name, phone, plan_name, end_date = record
                detail_text = f"Name: {client_name} | Phone: {phone}\nPlan: {plan_name} | Ends: {end_date}"
                record_label = customtkinter.CTkLabel(self.pending_renewals_frame, text=detail_text, anchor="w", justify="left")
                record_label.pack(padx=5, pady=3, fill="x", expand=True)
                if i < len(renewals_data) - 1:
                    sep = customtkinter.CTkFrame(self.pending_renewals_frame, height=1, fg_color="gray70")
                    sep.pack(fill="x", padx=5, pady=2)
        elif success and not renewals_data: # No renewals found
            CTkLabel(self.pending_renewals_frame, text="No renewals to display.").pack(pady=10)
        elif not success: # Error case
            CTkLabel(self.pending_renewals_frame, text="Error generating report. Check status message above.").pack(pady=10)

    def on_generate_finance_report_click(self):
        """Handles click for generating monthly finance report."""
        success, message, total_revenue = self.controller.generate_finance_report_action()

        if success:
            # Message already contains formatted revenue or "no data" type info
            # total_revenue being None after success might mean no transactions, which isn't an error but zero revenue
            color = "green"
            if total_revenue is None or total_revenue == 0: # Assuming controller returns 0 for no revenue
                 color = "orange"
            self.finance_report_label.configure(text=message, text_color=color)
        else: # Not successful
            self.finance_report_label.configure(text=message, text_color="red")

    def on_save_membership_click(self):
        """Handles the click event for the 'Save Membership' button."""
        membership_type = self.membership_type_var.get()
        selected_member_display_name = self.membership_member_dropdown_var.get()
        # Ensure member_id is None if default/placeholder is selected, otherwise get the ID.
        if selected_member_display_name in ["Select Member", "Loading...", "No members available"]:
            member_id = None
        else:
            member_id = self.member_name_to_id.get(selected_member_display_name)

        start_date_str = ""
        try:
            # Ensure get_date() is called only if a date is actually set,
            # or handle cases where it might return None or an empty string if not set by user.
            # For DateEntry, get() returns the string, get_date() returns a datetime.date object.
            start_date_obj = self.start_date_picker.get_date()
            start_date_str = start_date_obj.strftime('%Y-%m-%d')
        except ValueError: # This might occur if the DateEntry field is manipulated to be invalid
            self.membership_status_label.configure(text="Error: Invalid Start Date.", text_color="red")
            return
        except AttributeError: # If get_date() returns None (e.g. if field was cleared and not handled by DateEntry)
            self.membership_status_label.configure(text="Error: Start Date not selected.", text_color="red")
            return


        amount_paid_str = self.amount_paid_entry.get().strip()

        plan_id = None
        payment_date_str = None
        payment_method = None
        sessions_str = None

        if membership_type == "Group Class":
            selected_plan_display_name = self.membership_plan_dropdown_var.get()
            # Ensure plan_id is None if default/placeholder is selected
            if selected_plan_display_name in ["Select Plan", "Loading...", "No plans available"]:
                plan_id = None
            else:
                plan_id = self.plan_name_to_id.get(selected_plan_display_name)

            try:
                payment_date_obj = self.payment_date_picker.get_date()
                payment_date_str = payment_date_obj.strftime('%Y-%m-%d')
            except ValueError:
                self.membership_status_label.configure(text="Error: Invalid Payment Date.", text_color="red")
                return
            except AttributeError:
                self.membership_status_label.configure(text="Error: Payment Date not selected.", text_color="red")
                return
            payment_method = self.payment_method_entry.get().strip()
        elif membership_type == "Personal Training":
            payment_date_str = start_date_str
            payment_method = "N/A"
            sessions_str = self.pt_sessions_entry.get().strip()
        else:
            self.membership_status_label.configure(text="Error: Unknown membership type selected.", text_color="red")
            return

        # Now call the controller action
        success, message = self.controller.save_membership_action(
            membership_type=membership_type,
            member_id=member_id,
            start_date_str=start_date_str,
            amount_paid_str=amount_paid_str,
            selected_plan_id=plan_id,
            payment_date_str=payment_date_str,
            payment_method=payment_method,
            sessions_str=sessions_str
        )

        self.membership_status_label.configure(text=message, text_color="green" if success else "red")

        if success:
            self.start_date_picker.set_date(date.today())
            self.amount_paid_entry.delete(0, 'end')

            if membership_type == "Group Class":
                self.payment_date_picker.set_date(date.today())
                self.payment_method_entry.delete(0, 'end')
                if self.plan_name_to_id and list(self.plan_name_to_id.keys()): # Check if keys exist
                    self.membership_plan_dropdown_var.set(list(self.plan_name_to_id.keys())[0])
            elif membership_type == "Personal Training":
                self.pt_sessions_entry.delete(0, 'end')

            if self.member_name_to_id and list(self.member_name_to_id.keys()): # Check if keys exist
                 self.membership_member_dropdown_var.set(list(self.member_name_to_id.keys())[0])

            if self.selected_member_id == member_id: # Check if the affected member is currently selected
                updated_history = self.controller.get_all_activity_for_member(member_id)
                self.display_membership_history(updated_history, member_id)

    def on_save_member_click(self):
        """Handles the click event of the 'Save Member' button."""
        name = self.name_entry.get().strip()
        phone = self.phone_entry.get().strip()

        success, message = self.controller.save_member_action(name, phone)

        self.member_status_label.configure(text=message, text_color="green" if success else "red")

        if success:
            self.name_entry.delete(0, 'end')
            self.phone_entry.delete(0, 'end')

            # Refresh the list of all members displayed in the GUI
            updated_members = self.controller.get_filtered_members(None, None)
            self.display_all_members(updated_members)

            # Refresh the member dropdown in the membership forms
            self.populate_member_dropdown()
            # Note: populate_pt_member_dropdown was removed, so no need to call it.


if __name__ == '__main__':
    # This part is for testing gui.py directly if needed
    # For the full application, main.py should be run.

    # Ensure database and tables exist for direct GUI testing
    from reporter.database import create_database, DB_FILE as MAIN_DB_FILE
    import os
    data_dir = os.path.dirname(MAIN_DB_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    create_database(MAIN_DB_FILE) # Create tables if they don't exist

    app = App()
    app.mainloop()
