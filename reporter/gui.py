import customtkinter
from tkinter import StringVar # Explicitly import StringVar
from datetime import datetime # Explicitly import datetime
from customtkinter import CTkFrame, CTkLabel, CTkEntry, CTkButton, CTkOptionMenu, CTkFont, CTkScrollableFrame


class App(customtkinter.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        self.setup_membership_tab(self.tab_view.tab("Membership Management"))

        # --- Plan Management Tab ---
        self.setup_plan_management_tab(plan_management_tab) # Setup for the new tab

    def populate_pt_member_dropdown(self):
        """Populates the PT booking member dropdown with all members."""
        # This method assumes self.member_name_to_id is populated by populate_member_dropdown
        # which is called during setup_membership_tab.
        # If this assumption changes, self.member_name_to_id might need its own population logic here.
        from reporter.database_manager import get_all_members # Local import

        all_members = get_all_members()
        if not all_members:
            self.pt_member_dropdown.configure(values=["No members found"])
            self.pt_member_dropdown_var.set("No members found")
            return

        # Using the same naming convention as populate_member_dropdown for consistency,
        # but this dropdown will use "Name (Phone)" for display to be more user-friendly
        # in the context of PT bookings, as member ID is less relevant here.
        # self.member_name_to_id should already be populated.
        # If not, or if a different mapping is needed (e.g. name_phone to id), it should be created here.

        # For PT booking, let's display "Name (Phone)" and map this string to member_id
        # This requires a slightly different approach than the group membership's "Name (ID: id)"
        # We can reuse self.member_name_to_id if it's populated with a general "display_string" -> id,
        # or create a specific one for this dropdown.
        # For now, let's assume self.populate_member_dropdown() in setup_membership_tab
        # has already populated self.member_name_to_id with "Name (ID: id)" : id.
        # We will use the same self.member_name_to_id for retrieving ID upon saving.

        member_display_values = []
        # We need to ensure self.member_name_to_id is populated before this runs.
        # It's populated by self.populate_member_dropdown called in setup_membership_tab.
        # The keys of self.member_name_to_id are "Name (ID: id)".
        # We can use these directly or re-fetch members if a different format is strictly needed.
        # For simplicity, let's use the existing self.member_name_to_id keys for the dropdown.

        member_display_values = list(self.member_name_to_id.keys())

        if not member_display_values:
            member_display_values = ["No members loaded"] # Should ideally not happen if populate_member_dropdown ran

        self.pt_member_dropdown.configure(values=member_display_values)
        if member_display_values and member_display_values[0] != "No members loaded":
            self.pt_member_dropdown_var.set(member_display_values[0]) # Default to first member
        elif member_display_values: # Handles "No members loaded" case
            self.pt_member_dropdown_var.set(member_display_values[0])
        else: # Fallback if list is somehow empty after checks
            self.pt_member_dropdown_var.set("Error loading members")

    def setup_pt_booking_frame(self, parent_frame):
        """Sets up the frame for adding personal training bookings."""
        self.pt_booking_frame = CTkFrame(parent_frame, corner_radius=0, fg_color="transparent")
        # self.pt_booking_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10) # Using pack instead
        self.pt_booking_frame.pack(fill="x", expand=False, padx=20, pady=(10,0))


        CTkLabel(self.pt_booking_frame, text="Add Personal Training Booking", font=CTkFont(size=16, weight="bold")).pack(pady=(0,10), anchor="w")

        # Member selection
        CTkLabel(self.pt_booking_frame, text="Select Member:").pack(anchor="w")
        self.pt_member_dropdown_var = StringVar()
        self.pt_member_dropdown = CTkOptionMenu(self.pt_booking_frame, variable=self.pt_member_dropdown_var, values=["Loading..."])
        self.pt_member_dropdown.pack(fill="x", pady=(0,5))

        # Start Date
        CTkLabel(self.pt_booking_frame, text="Start Date (YYYY-MM-DD):").pack(anchor="w")
        self.pt_start_date_entry = CTkEntry(self.pt_booking_frame, placeholder_text="YYYY-MM-DD")
        self.pt_start_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.pt_start_date_entry.pack(fill="x", pady=(0,5))

        # Number of Sessions
        CTkLabel(self.pt_booking_frame, text="Number of Sessions:").pack(anchor="w")
        self.pt_sessions_entry = CTkEntry(self.pt_booking_frame, placeholder_text="e.g., 10")
        self.pt_sessions_entry.pack(fill="x", pady=(0,5))

        # Amount Paid
        CTkLabel(self.pt_booking_frame, text="Amount Paid:").pack(anchor="w")
        self.pt_amount_paid_entry = CTkEntry(self.pt_booking_frame, placeholder_text="e.g., 500.00")
        self.pt_amount_paid_entry.pack(fill="x", pady=(0,10))

        # Save Button
        self.save_pt_booking_button = CTkButton(self.pt_booking_frame, text="Save PT Booking", command=self.save_pt_booking_action)
        self.save_pt_booking_button.pack(fill="x", pady=(0,5))

        # Status Label
        self.pt_booking_status_label = CTkLabel(self.pt_booking_frame, text="", font=CTkFont(size=12))
        self.pt_booking_status_label.pack(anchor="w")

    def save_pt_booking_action(self):
        """Handles the save PT booking button click event with validation."""
        from reporter import database_manager # For add_pt_booking
        from datetime import datetime

        selected_member_display = self.pt_member_dropdown_var.get()
        start_date_str = self.pt_start_date_entry.get().strip()
        sessions_str = self.pt_sessions_entry.get().strip()
        amount_paid_str = self.pt_amount_paid_entry.get().strip()

        # --- Input Validation ---
        # Validate member selection
        if not selected_member_display or selected_member_display in ["Loading...", "No members found", "No members loaded", "Error loading members"]:
            self.pt_booking_status_label.configure(text="Error: Please select a valid member.", text_color="red")
            return

        # Retrieve member_id using the (potentially shared) member_name_to_id map
        # This map is populated by populate_member_dropdown and stores "Name (ID: id)" -> id
        member_id = self.member_name_to_id.get(selected_member_display)
        if not member_id:
            self.pt_booking_status_label.configure(text="Error: Could not find member ID. Please refresh.", text_color="red")
            return

        # Check that all fields are filled
        if not start_date_str or not sessions_str or not amount_paid_str:
            self.pt_booking_status_label.configure(text="Error: All fields must be filled.", text_color="red")
            return

        # Validate start_date_str format (YYYY-MM-DD)
        try:
            datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            self.pt_booking_status_label.configure(text="Error: Invalid Start Date format. Use YYYY-MM-DD.", text_color="red")
            return

        # Validate sessions_str is a positive integer
        try:
            sessions = int(sessions_str)
            if sessions <= 0:
                self.pt_booking_status_label.configure(text="Error: Number of Sessions must be a positive integer.", text_color="red")
                return
        except ValueError:
            self.pt_booking_status_label.configure(text="Error: Number of Sessions must be an integer.", text_color="red")
            return

        # Validate amount_paid_str is a positive number
        try:
            amount_paid = float(amount_paid_str)
            if amount_paid <= 0:
                self.pt_booking_status_label.configure(text="Error: Amount Paid must be a positive number.", text_color="red")
                return
        except ValueError:
            self.pt_booking_status_label.configure(text="Error: Amount Paid must be a valid number.", text_color="red")
            return

        # If validation passes, call database_manager.add_pt_booking
        try:
            success = database_manager.add_pt_booking(member_id, start_date_str, sessions, amount_paid)
            if success:
                self.pt_booking_status_label.configure(text="Success: PT Booking added.", text_color="green")
                # Clear input fields on success
                self.pt_start_date_entry.delete(0, "end")
                self.pt_start_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
                self.pt_sessions_entry.delete(0, "end")
                self.pt_amount_paid_entry.delete(0, "end")
                # Optionally reset dropdown, or leave as is for quick re-entry for same member
                # self.pt_member_dropdown_var.set(list(self.member_name_to_id.keys())[0]) # Reset to first member
            else:
                self.pt_booking_status_label.configure(text="Error: Failed to save PT Booking. Check logs.", text_color="red")
        except Exception as e:
            self.pt_booking_status_label.configure(text=f"Error: An unexpected error occurred: {e}", text_color="red")


        # --- Reporting Tab ---
        self.setup_reporting_tab(self.tab_view.tab("Reporting"))

    def setup_membership_tab(self, tab):
        """Configures the UI for the Membership Management tab."""
        # Import database functions locally within methods where they are needed
        # to avoid potential circular imports and keep dependencies clear.
        from reporter.database_manager import get_all_members # add_member_to_db is used in an action method
        # CTk* elements are now imported globally

        # Configure grid layout for the tab
        # tab.grid_columnconfigure(0, weight=1) # For the add member frame
        # tab.grid_columnconfigure(1, weight=2) # For the display members frame
        # tab.grid_rowconfigure(0, weight=1) # For Add Member and Add Group Membership
        # tab.grid_rowconfigure(1, weight=1) # For Display All Members (if it spans rows or is separate)

        # Main frame for the membership management tab, divides into forms and display areas.
        main_management_frame = customtkinter.CTkFrame(tab)
        main_management_frame.pack(expand=True, fill="both", padx=5, pady=5)
        main_management_frame.grid_columnconfigure(0, weight=1) # Column for input forms
        main_management_frame.grid_columnconfigure(1, weight=1) # Column for displaying member data
        main_management_frame.grid_rowconfigure(0, weight=0)    # Row for Add Member form
        main_management_frame.grid_rowconfigure(1, weight=0)    # Row for Add Group Membership form
        main_management_frame.grid_rowconfigure(2, weight=1)    # Spacer row, allows display frame to expand if needed

        # --- Column 0: Input Forms ---
        # This frame will contain all individual input forms (Add Member, Add Group Membership)
        forms_frame = customtkinter.CTkFrame(main_management_frame, fg_color="transparent")
        forms_frame.grid(row=0, column=0, rowspan=3, padx=5, pady=5, sticky="nsew") # Spans multiple rows in parent grid
        forms_frame.grid_columnconfigure(0, weight=1) # Ensure forms within this frame can expand horizontally

        # 1. Frame for Adding New Members
        # This section creates the UI elements for adding a new member.
        add_member_frame = customtkinter.CTkFrame(forms_frame)
        add_member_frame.grid(row=0, column=0, padx=5, pady=5, sticky="new") # Aligns to North-East-West
        add_member_frame.grid_columnconfigure(1, weight=1) # Allows entry fields to expand

        add_member_title = CTkLabel(add_member_frame, text="Add New Member", font=CTkFont(weight="bold"))
        add_member_title.grid(row=0, column=0, columnspan=2, padx=10, pady=(10,15))

        name_label = CTkLabel(add_member_frame, text="Name:")
        name_label.grid(row=1, column=0, padx=10, pady=5, sticky="w") # Aligns label to the west (left)
        self.name_entry = CTkEntry(add_member_frame) # Entry field for member's name
        self.name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew") # Expands East-West (horizontally)

        phone_label = CTkLabel(add_member_frame, text="Phone:")
        phone_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.phone_entry = CTkEntry(add_member_frame) # Entry field for member's phone
        self.phone_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        save_button = CTkButton(add_member_frame, text="Save Member", command=self.save_member_action)
        save_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10) # Spans two columns for centering

        self.member_status_label = CTkLabel(add_member_frame, text="", text_color="red") # Displays status/errors
        self.member_status_label.grid(row=4, column=0, columnspan=2, padx=10, pady=5)

        # --- Add Group Membership Frame ---
        # This frame is set up by a separate method for better organization.
        self.setup_group_membership_frame(forms_frame) # Pass the 'forms_frame' as parent

        # --- Add Personal Training Booking Frame ---
        # This frame is set up by a separate method.
        self.setup_pt_booking_frame(forms_frame) # Pass the 'forms_frame' as parent


        # --- Column 1: Display Area ---
        # This frame is for displaying member lists and membership history.
        display_frame = customtkinter.CTkFrame(main_management_frame)
        display_frame.grid(row=0, column=1, rowspan=3, padx=5, pady=5, sticky="nsew") # Spans rows and fills space
        display_frame.grid_rowconfigure(1, weight=1) # Allows the members_scrollable_frame to expand vertically
        display_frame.grid_rowconfigure(3, weight=1) # Allows the membership_history_frame to expand vertically
        display_frame.grid_columnconfigure(0, weight=1) # Allows content within to expand horizontally

        # Title for the "All Members" list
        display_title = CTkLabel(display_frame, text="All Members", font=CTkFont(weight="bold"))
        display_title.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Scrollable frame to display the list of all members
        self.members_scrollable_frame = CTkScrollableFrame(display_frame)
        self.members_scrollable_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")

        # --- Membership History Frame (Below All Members) ---
        history_title = CTkLabel(display_frame, text="Membership History", font=CTkFont(weight="bold"))
        history_title.grid(row=2, column=0, padx=10, pady=(10,0), sticky="ew") # Placed below members list

        # Scrollable frame to display history for a selected member
        self.membership_history_frame = CTkScrollableFrame(display_frame)
        self.membership_history_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

        # Initialize data displays
        self.display_all_members()      # Populate the list of all members
        self.populate_member_dropdown() # Populate dropdown for group membership form
        self.populate_plan_dropdown()   # Populate dropdown for group membership form
        self.populate_pt_member_dropdown() # Populate dropdown for PT booking form

        self.display_membership_history(None) # Show placeholder message in history view

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
        self.save_plan_button = CTkButton(self.plan_form_frame, text="Save Plan", command=self.save_plan_action)
        self.save_plan_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

        # Status Label for plan operations
        self.plan_status_label = CTkLabel(self.plan_form_frame, text="", font=CTkFont(size=12))
        self.plan_status_label.grid(row=4, column=0, columnspan=2, padx=10, pady=5)

        # --- Frame for Displaying Plans ---
        self.plans_display_frame = CTkScrollableFrame(tab)
        self.plans_display_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Initial load of plans
        self.load_plans_display()

    def load_plans_display(self):
        """Loads and displays all plans in the plans_display_frame."""
        from reporter import database_manager # Local import
        # Clear existing widgets
        for widget in self.plans_display_frame.winfo_children():
            widget.destroy()

        plans = database_manager.get_all_plans_with_inactive() # Fetch all plans

        if not plans:
            CTkLabel(self.plans_display_frame, text="No plans found.").pack(padx=10, pady=10)
            return

        for i, plan_data in enumerate(plans):
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
                                       command=lambda p_id=plan_id, current_status=is_active: self.toggle_plan_status_action(p_id, current_status))
            toggle_button.pack(side="right", padx=5)

            if i < len(plans) - 1:
                sep = CTkFrame(self.plans_display_frame, height=1, fg_color="gray70")
                sep.pack(fill="x", padx=5, pady=2)

    def save_plan_action(self):
        """Saves a new plan or updates an existing one."""
        from reporter import database_manager # Local import

        plan_name = self.plan_name_entry.get().strip()
        duration_str = self.plan_duration_entry.get().strip()
        plan_id_to_update = self.current_plan_id_var.get()

        if not plan_name or not duration_str:
            self.plan_status_label.configure(text="Error: Plan Name and Duration cannot be empty.", text_color="red")
            return

        try:
            duration_days = int(duration_str)
            if duration_days <= 0:
                self.plan_status_label.configure(text="Error: Duration must be a positive integer.", text_color="red")
                return
        except ValueError:
            self.plan_status_label.configure(text="Error: Duration must be a valid integer.", text_color="red")
            return

        success = False
        if plan_id_to_update: # Editing existing plan
            plan_id = int(plan_id_to_update)
            success = database_manager.update_plan(plan_id, plan_name, duration_days)
            message = "Plan updated successfully!" if success else "Failed to update plan. Name might exist."
        else: # Adding new plan
            # When adding a new plan, it's active by default (as per database_manager.add_plan)
            new_plan_id = database_manager.add_plan(plan_name, duration_days) # is_active defaults to True
            if new_plan_id:
                success = True
            message = "Plan added successfully!" if success else "Failed to add plan. Name might exist."

        if success:
            self.plan_status_label.configure(text=message, text_color="green")
            self.clear_plan_form()
            self.load_plans_display()
            self.populate_plan_dropdown() # Update plan dropdown in membership tab
        else:
            self.plan_status_label.configure(text=message, text_color="red")

    def edit_plan_action(self, plan_id, name, duration):
        """Populates the plan form for editing."""
        self.current_plan_id_var.set(str(plan_id))
        self.plan_name_entry.delete(0, "end")
        self.plan_name_entry.insert(0, name)
        self.plan_duration_entry.delete(0, "end")
        self.plan_duration_entry.insert(0, str(duration))
        self.plan_status_label.configure(text="") # Clear status

    def toggle_plan_status_action(self, plan_id, current_status):
        """Activates or deactivates a plan."""
        from reporter import database_manager # Local import
        new_status = not current_status
        success = database_manager.set_plan_active_status(plan_id, new_status)
        if success:
            self.plan_status_label.configure(text=f"Plan status changed to {'Active' if new_status else 'Inactive'}.", text_color="green")
            self.load_plans_display()
            self.populate_plan_dropdown() # Update plan dropdown in membership tab
        else:
            self.plan_status_label.configure(text="Failed to update plan status.", text_color="red")

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
                                    command=self.generate_pending_renewals_action)
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
                                            command=self.generate_finance_report_action)
        generate_finance_button.pack(pady=5)

        # Label to display the finance report result or status messages
        self.finance_report_label = CTkLabel(finance_report_frame, text="Finance report will appear here.", font=CTkFont(size=14))
        self.finance_report_label.pack(pady=10)


    def generate_finance_report_action(self):
        """Fetches and displays the finance report for the previous month."""
        # Local import for database interaction
        from reporter.database_manager import get_finance_report
        from datetime import date, timedelta
        import calendar # For getting month name

        self.finance_report_label.configure(text="Generating report...", text_color="blue") # Intermediate status

        today = date.today()
        # Calculate the first day of the current month
        first_day_current_month = today.replace(day=1)
        # Calculate the last day of the previous month by subtracting one day from the first day of the current month
        last_day_previous_month = first_day_current_month - timedelta(days=1)

        # Extract year and month from the last day of the previous month
        prev_month = last_day_previous_month.month
        prev_year = last_day_previous_month.year

        prev_month_name = calendar.month_name[prev_month] # Get the name of the month

        try:
            total_revenue = get_finance_report(prev_year, prev_month)
            if total_revenue is not None: # Check if report generation was successful (None indicates error)
                self.finance_report_label.configure(
                    text=f"Total revenue for {prev_month_name} {prev_year}: ${total_revenue:.2f}",
                    text_color="green" if total_revenue > 0 else "orange" # Green for revenue, orange for zero
                )
            else: # Error case from get_finance_report (e.g., database error)
                 self.finance_report_label.configure(
                    text=f"Could not generate finance report for {prev_month_name} {prev_year}. Check logs.",
                    text_color="red"
                )
        except Exception as e: # Catch any other unexpected exceptions
            self.finance_report_label.configure(
                text=f"Error generating finance report: {str(e)}",
                text_color="red"
            )


    def generate_pending_renewals_action(self):
        """Fetches and displays pending renewals for the current month."""
        # Local import for database interaction
        from reporter.database_manager import get_pending_renewals
        from datetime import date
        import calendar # For getting month name

        # Clear previous results from the scrollable frame
        for widget in self.pending_renewals_frame.winfo_children():
            widget.destroy()
        self.pending_renewals_status_label.configure(text="Generating report...", text_color="blue") # Intermediate status


        today = date.today()
        current_date_str = today.strftime('%Y-%m-%d') # Format date as YYYY-MM-DD for the DB query

        month_name = calendar.month_name[today.month] # Get current month name for display
        year = today.year # Get current year for display

        try:
            renewals = get_pending_renewals(current_date_str) # Fetch data from database manager
            if renewals:
                self.pending_renewals_status_label.configure(
                    text=f"Found {len(renewals)} pending renewals for {month_name} {year}:",
                    text_color="green" # Success color (or system default)
                )
                # Display each renewal record
                for i, record in enumerate(renewals):
                    # record format: (client_name, phone, plan_name, end_date)
                    client_name, phone, plan_name, end_date = record
                    detail_text = f"Name: {client_name} | Phone: {phone}\nPlan: {plan_name} | Ends: {end_date}"

                    record_label = customtkinter.CTkLabel(self.pending_renewals_frame, text=detail_text, anchor="w", justify="left")
                    record_label.pack(padx=5, pady=3, fill="x", expand=True)
                    # Add a separator line between records, except for the last one
                    if i < len(renewals) - 1:
                        sep = customtkinter.CTkFrame(self.pending_renewals_frame, height=1, fg_color="gray70") # Visual separator
                        sep.pack(fill="x", padx=5, pady=2)
            else:
                self.pending_renewals_status_label.configure(
                    text=f"No pending renewals found for {month_name} {year}.",
                    text_color="orange" # Informative color for no results (or system default)
                )
        except Exception as e: # Catch any errors during report generation
            self.pending_renewals_status_label.configure(
                text=f"Error generating report: {str(e)}",
                text_color="red"
            )

    def setup_group_membership_frame(self, parent_frame):
        """Sets up the UI for adding group memberships."""
        # Local imports for UI elements and database functions
        # from reporter.database_manager import get_all_plans, add_group_membership_to_db, get_all_members # Used in actions or populating
        # CTk* elements and datetime are now imported globally

        # Frame to contain all elements for adding a group membership
        group_membership_frame = customtkinter.CTkFrame(parent_frame)
        group_membership_frame.grid(row=1, column=0, padx=5, pady=10, sticky="new") # Position below add_member_frame
        group_membership_frame.grid_columnconfigure(1, weight=1) # Allow entry fields to expand
        self.group_membership_frame = group_membership_frame # Store reference if needed

        title = CTkLabel(group_membership_frame, text="Add Group Membership", font=CTkFont(weight="bold"))
        title.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 15))

        # Member Dropdown: Allows selection of an existing member
        member_label = CTkLabel(group_membership_frame, text="Select Member:")
        member_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.membership_member_dropdown_var = customtkinter.StringVar(value="Select Member") # Control variable for dropdown
        self.membership_member_dropdown = CTkOptionMenu(group_membership_frame, variable=self.membership_member_dropdown_var, values=[])
        self.membership_member_dropdown.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.member_name_to_id = {} # Dictionary to map displayed member names to their IDs

        # Plan Dropdown: Allows selection of a membership plan
        plan_label = CTkLabel(group_membership_frame, text="Select Plan:")
        plan_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.membership_plan_dropdown_var = customtkinter.StringVar(value="Select Plan") # Control variable for dropdown
        self.membership_plan_dropdown = CTkOptionMenu(group_membership_frame, variable=self.membership_plan_dropdown_var, values=[])
        self.membership_plan_dropdown.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        self.plan_name_to_id = {} # Dictionary to map displayed plan names to their IDs

        # Payment Date Entry: For recording the date of payment
        payment_date_label = CTkLabel(group_membership_frame, text="Payment Date (YYYY-MM-DD):")
        payment_date_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.payment_date_entry = CTkEntry(group_membership_frame)
        self.payment_date_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        self.payment_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d')) # Default to today's date

        # Start Date Entry: For recording the membership start date
        start_date_label = CTkLabel(group_membership_frame, text="Start Date (YYYY-MM-DD):")
        start_date_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.start_date_entry = CTkEntry(group_membership_frame)
        self.start_date_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        self.start_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d')) # Default to today's date

        # Amount Paid Entry: For recording the amount paid
        amount_paid_label = CTkLabel(group_membership_frame, text="Amount Paid:")
        amount_paid_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.amount_paid_entry = CTkEntry(group_membership_frame)
        self.amount_paid_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        # Payment Method Entry: For recording the method of payment
        payment_method_label = CTkLabel(group_membership_frame, text="Payment Method:")
        payment_method_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.payment_method_entry = CTkEntry(group_membership_frame)
        self.payment_method_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        # Save Button: Triggers the action to save the group membership
        save_gm_button = CTkButton(group_membership_frame, text="Save Membership", command=self.save_group_membership_action)
        save_gm_button.grid(row=7, column=0, columnspan=2, padx=10, pady=10)

        # Status Label: Displays feedback or error messages for this form
        self.group_membership_status_label = CTkLabel(group_membership_frame, text="", text_color="red")
        self.group_membership_status_label.grid(row=8, column=0, columnspan=2, padx=10, pady=5)

    def populate_member_dropdown(self):
        """Populates the member selection dropdown with data from the database."""
        from reporter.database_manager import get_all_members # Local import
        members = get_all_members()
        # Create a mapping from a display string "Name (ID: id)" to the member's ID
        self.member_name_to_id = {f"{m[1]} (ID: {m[0]})": m[0] for m in members}
        member_names_display = list(self.member_name_to_id.keys())

        if not member_names_display:
            member_names_display = ["No members available"] # Placeholder if no members
            self.membership_member_dropdown_var.set(member_names_display[0])
        else:
            # Set default selection to the first member or a generic prompt
            self.membership_member_dropdown_var.set(member_names_display[0])
        # Update the dropdown menu with the new list of names
        self.membership_member_dropdown.configure(values=member_names_display)

    def populate_plan_dropdown(self):
        """Populates the plan selection dropdown with data from the database."""
        from reporter.database_manager import get_all_plans # Local import
        plans = get_all_plans() # Fetches (plan_id, plan_name, duration_days)
        # Create a mapping from plan name to plan ID
        self.plan_name_to_id = {p[1]: p[0] for p in plans}
        plan_names_display = list(self.plan_name_to_id.keys())

        if not plan_names_display:
            plan_names_display = ["No plans available"] # Placeholder if no plans
            self.membership_plan_dropdown_var.set(plan_names_display[0])
        else:
            # Set default selection to the first plan or a generic prompt
            self.membership_plan_dropdown_var.set(plan_names_display[0])
        # Update the dropdown menu with the new list of plan names
        self.membership_plan_dropdown.configure(values=plan_names_display)

    def save_group_membership_action(self):
        """Handles the save group membership button click event with validation."""
        from reporter.database_manager import add_group_membership_to_db # Local import
        from datetime import datetime

        # Get selected values from dropdowns
        selected_member_display_name = self.membership_member_dropdown_var.get()
        selected_plan_name = self.membership_plan_dropdown_var.get()

        # Retrieve corresponding IDs using the mappings
        member_id = self.member_name_to_id.get(selected_member_display_name)
        plan_id = self.plan_name_to_id.get(selected_plan_name)

        # Get values from entry fields
        payment_date_str = self.payment_date_entry.get().strip()
        start_date_str = self.start_date_entry.get().strip()
        amount_paid_str = self.amount_paid_entry.get().strip()
        payment_method = self.payment_method_entry.get().strip()

        # --- Input Validation ---
        # Validate member selection
        if not member_id or selected_member_display_name == "No members available" or selected_member_display_name == "Select Member":
            self.group_membership_status_label.configure(text="Error: Please select a valid member.", text_color="red")
            return
        # Validate plan selection
        if not plan_id or selected_plan_name == "No plans available" or selected_plan_name == "Select Plan":
            self.group_membership_status_label.configure(text="Error: Please select a valid plan.", text_color="red")
            return
        # Validate presence of all date and text fields
        if not payment_date_str or not start_date_str or not amount_paid_str or not payment_method:
            self.group_membership_status_label.configure(text="Error: All fields must be filled.", text_color="red")
            return

        # Validate date formats
        try:
            datetime.strptime(payment_date_str, '%Y-%m-%d')
            datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            self.group_membership_status_label.configure(text="Error: Invalid date format. Use YYYY-MM-DD.", text_color="red")
            return

        # Validate amount paid (must be a positive number)
        try:
            amount_paid = float(amount_paid_str)
            if amount_paid <= 0: # Amount should be greater than zero
                self.group_membership_status_label.configure(text="Error: Amount paid must be a positive value.", text_color="red")
                return
        except ValueError:
            self.group_membership_status_label.configure(text="Error: Invalid amount. Must be a number.", text_color="red")
            return

        # Attempt to add to database
        try:
            success = add_group_membership_to_db(
                member_id, plan_id, payment_date_str, start_date_str, amount_paid, payment_method
            )
            if success:
                self.group_membership_status_label.configure(text="Group membership added successfully!", text_color="green")
                # Clear input fields after successful submission
                self.payment_date_entry.delete(0, 'end')
                self.payment_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d')) # Reset to today
                self.start_date_entry.delete(0, 'end')
                self.start_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d')) # Reset to today
                self.amount_paid_entry.delete(0, 'end')
                self.payment_method_entry.delete(0, 'end')
                # Refresh membership history if the current selected member is the one this was added for
                if self.selected_member_id == member_id:
                    self.display_membership_history(member_id)
            else:
                # This could be due to database constraints or other issues caught in database_manager
                self.group_membership_status_label.configure(text="Failed to add group membership. Check logs or input.", text_color="red")
        except Exception as e: # Catch any other unexpected errors
            self.group_membership_status_label.configure(text=f"An error occurred: {str(e)}", text_color="red")

    def display_all_members(self):
        """Clears and re-populates the scrollable frame with member data. Makes member labels clickable."""
        from reporter.database_manager import get_all_members # Local import

        # Clear existing widgets in the frame before repopulating
        for widget in self.members_scrollable_frame.winfo_children():
            widget.destroy()

        members = get_all_members() # Fetch all members from the database
        if not members:
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
        if self.selected_member_id and not any(m[0] == self.selected_member_id for m in members):
            self.selected_member_id = None
            self.selected_member_label_widget = None # It's already gone from display, so no need to change color
            self.display_membership_history(None)


    def handle_member_selection(self, event, member_id, label_widget):
        """Handles click on a member label to display their membership history and highlight selection."""
        # If a different member was previously selected, reset its appearance
        if self.selected_member_label_widget and self.selected_member_label_widget != label_widget:
            self.selected_member_label_widget.configure(fg_color="transparent") # Reset to default background

        # Update the selected member ID and the widget reference
        self.selected_member_id = member_id
        self.selected_member_label_widget = label_widget
        # Highlight the newly selected member's label
        label_widget.configure(fg_color="gray20") # Use a theme-appropriate highlight color

        # Display the membership history for the selected member
        self.display_membership_history(member_id)

    def display_membership_history(self, member_id):
        """Displays all activity (group memberships and PT bookings) for the given member_id."""
        from reporter.database_manager import get_all_activity_for_member # Updated function import

        # Clear any existing history records from the frame
        for widget in self.membership_history_frame.winfo_children():
            widget.destroy()

        if member_id is None:
            no_history_label = customtkinter.CTkLabel(self.membership_history_frame, text="Select a member to see their activity history.")
            no_history_label.pack(padx=10, pady=10)
            return

        history_records = get_all_activity_for_member(member_id)
        if not history_records:
            no_records_label = customtkinter.CTkLabel(self.membership_history_frame, text="No activity history found for this member.")
            no_records_label.pack(padx=10, pady=10)
            return

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


    def save_member_action(self):
        """Handles the save member button click event with input validation."""
        from reporter.database_manager import add_member_to_db # Local import

        name = self.name_entry.get().strip() # Get name and remove leading/trailing whitespace
        phone = self.phone_entry.get().strip() # Get phone and remove leading/trailing whitespace

        # --- Input Validation ---
        # Check for empty fields
        if not name or not phone:
            self.member_status_label.configure(text="Error: Name and Phone cannot be empty.", text_color="red")
            return

        # Basic phone validation: must contain only digits.
        # More complex validation (e.g., length, specific country codes) could be added here.
        if not phone.isdigit():
            self.member_status_label.configure(text="Error: Phone number must contain only digits.", text_color="red")
            return
        # Example: Validate phone length (e.g., 10 digits) - uncomment and adjust as needed
        # if len(phone) != 10:
        #     self.member_status_label.configure(text="Error: Phone number must be 10 digits.", text_color="red")
        #     return

        # Attempt to add member to the database
        try:
            # Call add_member_to_db without join_date; it will default to NULL in the DB
            # The join_date will be updated when the first activity is recorded.
            success = add_member_to_db(name, phone)
            if success:
                self.member_status_label.configure(text="Member added successfully! Join date will be set with first activity.", text_color="green")
                # Clear input fields after successful submission
                self.name_entry.delete(0, 'end')
                self.phone_entry.delete(0, 'end')
                # Refresh the list of all members displayed in the GUI
                self.display_all_members()
                # Refresh the member dropdown in the group membership form
                self.populate_member_dropdown()
            else:
                # This typically means the phone number already exists (due to UNIQUE constraint in DB)
                self.member_status_label.configure(text="Failed to add member. Phone number may already exist.", text_color="red")
            # Refresh the PT member dropdown as well, in case a new member was intended for PT
            self.populate_pt_member_dropdown()
        except Exception as e: # Catch any other unexpected errors from the database manager
            self.member_status_label.configure(text=f"An error occurred: {str(e)}", text_color="red")


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
