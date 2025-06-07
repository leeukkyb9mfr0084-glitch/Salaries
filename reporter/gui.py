import customtkinter

class App(customtkinter.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title("Kranos MMA Reporter")
        self.geometry("800x600")

        # Create Tabview
        self.tab_view = customtkinter.CTkTabview(self)
        self.tab_view.pack(expand=True, fill="both", padx=10, pady=10)

        # Add tabs
        self.tab_view.add("Membership Management")
        self.tab_view.add("Reporting")

        # Add placeholder content to tabs
        membership_tab = self.tab_view.tab("Membership Management")
        reporting_tab = self.tab_view.tab("Reporting")

        # --- Membership Management Tab ---
        self.setup_membership_tab(self.tab_view.tab("Membership Management"))

        # --- Reporting Tab ---
        self.setup_reporting_tab(self.tab_view.tab("Reporting"))

    def setup_membership_tab(self, tab):
        """Configures the UI for the Membership Management tab."""
        # Import database functions locally within methods where they are needed
        # to avoid potential circular imports and keep dependencies clear.
        from reporter.database_manager import get_all_members # add_member_to_db is used in an action method
        from customtkinter import CTkScrollableFrame, CTkEntry, CTkLabel, CTkButton, CTkFont

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

        # State variables for tracking selected member
        self.selected_member_id = None # Stores the ID of the currently selected member
        self.selected_member_label_widget = None # Stores the label widget of the selected member for visual feedback
        self.display_membership_history(None) # Show placeholder message in history view


    def setup_reporting_tab(self, tab):
        """Configures the UI for the Reporting tab."""
        # Import UI elements and database functions locally
        from customtkinter import CTkFrame, CTkButton, CTkLabel, CTkScrollableFrame, CTkFont
        # from reporter.database_manager import get_pending_renewals # Used in action method
        from datetime import datetime # Not strictly needed here, but good for context

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
        from customtkinter import CTkOptionMenu, CTkEntry, CTkLabel, CTkButton, CTkFont
        from datetime import datetime

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
        """Displays membership history for the given member_id in its scrollable frame."""
        from reporter.database_manager import get_memberships_for_member # Local import

        # Clear any existing history records from the frame
        for widget in self.membership_history_frame.winfo_children():
            widget.destroy()

        # If no member_id is provided (e.g., no member selected), display a placeholder message
        if member_id is None:
            no_history_label = customtkinter.CTkLabel(self.membership_history_frame, text="Select a member to see their history.")
            no_history_label.pack(padx=10, pady=10)
            return

        # Fetch membership records for the selected member
        history_records = get_memberships_for_member(member_id)
        if not history_records:
            # Display a message if no history is found for the selected member
            no_records_label = customtkinter.CTkLabel(self.membership_history_frame, text="No membership history found for this member.")
            no_records_label.pack(padx=10, pady=10)
            return

        # Display each history record
        for i, record in enumerate(history_records):
            # Record format: (plan_name, payment_date, start_date, end_date, amount_paid, payment_method, membership_id)
            plan_name, payment_date, start_date, end_date, amount_paid, payment_method, _ = record
            history_text = (f"Plan: {plan_name} | Paid: {amount_paid:.2f} ({payment_method})\n"
                            f"From: {start_date} To: {end_date} (Paid on: {payment_date})")

            history_label = customtkinter.CTkLabel(self.membership_history_frame, text=history_text, anchor="w", justify="left")
            history_label.pack(padx=5, pady=3, fill="x", expand=True)

            # Add a visual separator between history entries, except for the last one
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
            success = add_member_to_db(name, phone)
            if success:
                self.member_status_label.configure(text="Member added successfully!", text_color="green")
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
