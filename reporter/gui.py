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
        # Import here to avoid circular imports if database_manager needs gui elements later (unlikely for now)
        from reporter.database_manager import add_member_to_db, get_all_members
        from customtkinter import CTkScrollableFrame, CTkEntry, CTkLabel, CTkButton, CTkFont

        # Configure grid layout for the tab
        # tab.grid_columnconfigure(0, weight=1) # For the add member frame
        # tab.grid_columnconfigure(1, weight=2) # For the display members frame
        # tab.grid_rowconfigure(0, weight=1) # For Add Member and Add Group Membership
        # tab.grid_rowconfigure(1, weight=1) # For Display All Members (if it spans rows or is separate)

        # Let's use a main frame that then gets split
        main_management_frame = customtkinter.CTkFrame(tab)
        main_management_frame.pack(expand=True, fill="both", padx=5, pady=5)
        main_management_frame.grid_columnconfigure(0, weight=1) # Left column for forms
        main_management_frame.grid_columnconfigure(1, weight=1) # Right column for display
        main_management_frame.grid_rowconfigure(0, weight=0)    # Add Member form
        main_management_frame.grid_rowconfigure(1, weight=0)    # Add Group Membership form
        main_management_frame.grid_rowconfigure(2, weight=1)    # Spacer or if display frame is only at bottom

        # --- Column 0: Input Forms ---
        forms_frame = customtkinter.CTkFrame(main_management_frame, fg_color="transparent")
        forms_frame.grid(row=0, column=0, rowspan=3, padx=5, pady=5, sticky="nsew")
        forms_frame.grid_columnconfigure(0, weight=1)

        # 1. Frame for Adding New Members
        add_member_frame = customtkinter.CTkFrame(forms_frame)
        add_member_frame.grid(row=0, column=0, padx=5, pady=5, sticky="new") # new = North East West
        add_member_frame.grid_columnconfigure(1, weight=1)

        add_member_title = CTkLabel(add_member_frame, text="Add New Member", font=CTkFont(weight="bold"))
        add_member_title.grid(row=0, column=0, columnspan=2, padx=10, pady=(10,15))

        name_label = CTkLabel(add_member_frame, text="Name:")
        name_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.name_entry = CTkEntry(add_member_frame)
        self.name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        phone_label = CTkLabel(add_member_frame, text="Phone:")
        phone_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.phone_entry = CTkEntry(add_member_frame)
        self.phone_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        save_button = CTkButton(add_member_frame, text="Save Member", command=self.save_member_action)
        save_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

        self.member_status_label = CTkLabel(add_member_frame, text="", text_color="red")
        self.member_status_label.grid(row=4, column=0, columnspan=2, padx=10, pady=5)

        # --- Add Group Membership Frame ---
        self.setup_group_membership_frame(forms_frame) # Pass the parent 'forms_frame'
        # self.group_membership_frame will be gridded in setup_group_membership_frame

        # --- Column 1: Display Area ---
        # Frame for Displaying Existing Members (Right side of main_management_frame)
        display_frame = customtkinter.CTkFrame(main_management_frame)
        display_frame.grid(row=0, column=1, rowspan=3, padx=5, pady=5, sticky="nsew")
        display_frame.grid_rowconfigure(1, weight=1) # Make scrollable frame expand
        display_frame.grid_columnconfigure(0, weight=1)

        display_title = CTkLabel(display_frame, text="All Members", font=CTkFont(weight="bold"))
        display_title.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.members_scrollable_frame = CTkScrollableFrame(display_frame)
        self.members_scrollable_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")

        self.display_all_members() # Initial population of members list
        self.populate_member_dropdown() # Populate for group membership form
        self.populate_plan_dropdown()   # Populate for group membership form

        # --- Membership History Frame (Below All Members) ---
        history_title = CTkLabel(display_frame, text="Membership History", font=CTkFont(weight="bold"))
        history_title.grid(row=2, column=0, padx=10, pady=(10,0), sticky="ew") # Placed below members list

        self.membership_history_frame = CTkScrollableFrame(display_frame)
        self.membership_history_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        display_frame.grid_rowconfigure(3, weight=1) # Allow history frame to expand a bit

        self.selected_member_id = None # To store the ID of the currently selected member
        self.selected_member_label_widget = None # To store the widget of the selected member label for visual feedback
        self.display_membership_history(None) # Initial placeholder message


    def setup_reporting_tab(self, tab):
        """Configures the UI for the Reporting tab."""
        from customtkinter import CTkFrame, CTkButton, CTkLabel, CTkScrollableFrame, CTkFont
        from reporter.database_manager import get_pending_renewals
        from datetime import datetime

        # Configure grid layout for the tab
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=0) # Frame for button
        tab.grid_rowconfigure(1, weight=0) # Frame for status label
        tab.grid_rowconfigure(2, weight=1) # Frame for results

        # Frame for Pending Renewals
        renewals_frame = CTkFrame(tab)
        renewals_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        renewals_frame.grid_columnconfigure(0, weight=1) # Allow button to center or expand if needed

        renewals_title = CTkLabel(renewals_frame, text="Pending Renewals Report", font=CTkFont(weight="bold"))
        renewals_title.pack(pady=(5,10))

        generate_button = CTkButton(renewals_frame, text="Generate Pending Renewals for Current Month",
                                    command=self.generate_pending_renewals_action)
        generate_button.pack(pady=5)

        self.pending_renewals_status_label = CTkLabel(tab, text="") # Status label for renewals
        self.pending_renewals_status_label.grid(row=1, column=0, padx=10, pady=(0,5), sticky="ew")

        self.pending_renewals_frame = CTkScrollableFrame(tab)
        self.pending_renewals_frame.grid(row=2, column=0, padx=10, pady=(0,10), sticky="nsew")

        # --- Frame for Monthly Finance Report (below Pending Renewals) ---
        finance_report_frame = CTkFrame(tab)
        finance_report_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        finance_report_frame.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=0) # Adjust weight as needed, or let it be small

        finance_title = CTkLabel(finance_report_frame, text="Monthly Finance Report", font=CTkFont(weight="bold"))
        finance_title.pack(pady=(5,10))

        generate_finance_button = CTkButton(finance_report_frame, text="Generate Last Month's Finance Report",
                                            command=self.generate_finance_report_action)
        generate_finance_button.pack(pady=5)

        self.finance_report_label = CTkLabel(finance_report_frame, text="Finance report will appear here.", font=CTkFont(size=14))
        self.finance_report_label.pack(pady=10)


    def generate_finance_report_action(self):
        """Fetches and displays the finance report for the previous month."""
        from reporter.database_manager import get_finance_report # Keep import local
        from datetime import date, timedelta
        import calendar

        today = date.today()
        # Calculate first day of current month
        first_day_current_month = today.replace(day=1)
        # Calculate last day of previous month
        last_day_previous_month = first_day_current_month - timedelta(days=1)

        prev_month = last_day_previous_month.month
        prev_year = last_day_previous_month.year

        prev_month_name = calendar.month_name[prev_month]

        try:
            total_revenue = get_finance_report(prev_year, prev_month)
            if total_revenue is not None: # get_finance_report returns 0.0 or None on error
                self.finance_report_label.configure(
                    text=f"Total revenue for {prev_month_name} {prev_year}: ${total_revenue:.2f}",
                    text_color="green" if total_revenue > 0 else "orange" # Or system default
                )
            else: # Error case from get_finance_report
                 self.finance_report_label.configure(
                    text=f"Could not generate finance report for {prev_month_name} {prev_year}.",
                    text_color="red"
                )
        except Exception as e:
            self.finance_report_label.configure(
                text=f"Error generating finance report: {e}",
                text_color="red"
            )


    def generate_pending_renewals_action(self):
        """Fetches and displays pending renewals for the current month."""
        from reporter.database_manager import get_pending_renewals # Keep import local
        from datetime import date
        import calendar

        # Clear previous results
        for widget in self.pending_renewals_frame.winfo_children():
            widget.destroy()

        today = date.today()
        current_date_str = today.strftime('%Y-%m-%d')

        month_name = calendar.month_name[today.month]
        year = today.year

        try:
            renewals = get_pending_renewals(current_date_str)
            if renewals:
                self.pending_renewals_status_label.configure(
                    text=f"Found {len(renewals)} pending renewals for {month_name} {year}:",
                    text_color="green" # Or system default
                )
                for i, record in enumerate(renewals):
                    # record: (client_name, phone, plan_name, end_date)
                    client_name, phone, plan_name, end_date = record
                    detail_text = f"Name: {client_name} | Phone: {phone}\nPlan: {plan_name} | Ends: {end_date}"

                    record_label = customtkinter.CTkLabel(self.pending_renewals_frame, text=detail_text, anchor="w", justify="left")
                    record_label.pack(padx=5, pady=3, fill="x", expand=True)
                    if i < len(renewals) - 1:
                        sep = customtkinter.CTkFrame(self.pending_renewals_frame, height=1, fg_color="gray70")
                        sep.pack(fill="x", padx=5, pady=2)
            else:
                self.pending_renewals_status_label.configure(
                    text=f"No pending renewals found for {month_name} {year}.",
                    text_color="orange" # Or system default
                )
        except Exception as e:
            self.pending_renewals_status_label.configure(
                text=f"Error generating report: {e}",
                text_color="red"
            )

    def setup_group_membership_frame(self, parent_frame):
        """Sets up the UI for adding group memberships."""
        from reporter.database_manager import get_all_plans, add_group_membership_to_db, get_all_members
        from customtkinter import CTkOptionMenu, CTkEntry, CTkLabel, CTkButton, CTkFont
        from datetime import datetime

        group_membership_frame = customtkinter.CTkFrame(parent_frame)
        group_membership_frame.grid(row=1, column=0, padx=5, pady=10, sticky="new") # Place below add_member_frame
        group_membership_frame.grid_columnconfigure(1, weight=1)
        self.group_membership_frame = group_membership_frame # Store reference if needed elsewhere

        title = CTkLabel(group_membership_frame, text="Add Group Membership", font=CTkFont(weight="bold"))
        title.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 15))

        # Member Dropdown
        member_label = CTkLabel(group_membership_frame, text="Select Member:")
        member_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.membership_member_dropdown_var = customtkinter.StringVar(value="Select Member")
        self.membership_member_dropdown = CTkOptionMenu(group_membership_frame, variable=self.membership_member_dropdown_var, values=[])
        self.membership_member_dropdown.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.member_name_to_id = {} # To store mapping of display names to member_ids

        # Plan Dropdown
        plan_label = CTkLabel(group_membership_frame, text="Select Plan:")
        plan_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.membership_plan_dropdown_var = customtkinter.StringVar(value="Select Plan")
        self.membership_plan_dropdown = CTkOptionMenu(group_membership_frame, variable=self.membership_plan_dropdown_var, values=[])
        self.membership_plan_dropdown.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        self.plan_name_to_id = {} # To store mapping of display names to plan_ids

        # Payment Date Entry
        payment_date_label = CTkLabel(group_membership_frame, text="Payment Date (YYYY-MM-DD):")
        payment_date_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.payment_date_entry = CTkEntry(group_membership_frame)
        self.payment_date_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        self.payment_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))

        # Start Date Entry
        start_date_label = CTkLabel(group_membership_frame, text="Start Date (YYYY-MM-DD):")
        start_date_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.start_date_entry = CTkEntry(group_membership_frame)
        self.start_date_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        self.start_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))

        # Amount Paid Entry
        amount_paid_label = CTkLabel(group_membership_frame, text="Amount Paid:")
        amount_paid_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.amount_paid_entry = CTkEntry(group_membership_frame)
        self.amount_paid_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        # Payment Method Entry
        payment_method_label = CTkLabel(group_membership_frame, text="Payment Method:")
        payment_method_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.payment_method_entry = CTkEntry(group_membership_frame)
        self.payment_method_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        # Save Button
        save_gm_button = CTkButton(group_membership_frame, text="Save Membership", command=self.save_group_membership_action)
        save_gm_button.grid(row=7, column=0, columnspan=2, padx=10, pady=10)

        # Status Label
        self.group_membership_status_label = CTkLabel(group_membership_frame, text="", text_color="red")
        self.group_membership_status_label.grid(row=8, column=0, columnspan=2, padx=10, pady=5)

    def populate_member_dropdown(self):
        from reporter.database_manager import get_all_members
        members = get_all_members()
        self.member_name_to_id = {f"{m[1]} (ID: {m[0]})": m[0] for m in members} # Name (ID: id) : id
        member_names = list(self.member_name_to_id.keys())
        if not member_names:
            member_names = ["No members available"]
            self.membership_member_dropdown_var.set(member_names[0])
        else:
             self.membership_member_dropdown_var.set(member_names[0] if member_names else "Select Member")
        self.membership_member_dropdown.configure(values=member_names)

    def populate_plan_dropdown(self):
        from reporter.database_manager import get_all_plans
        plans = get_all_plans() # (plan_id, plan_name, duration_days)
        self.plan_name_to_id = {p[1]: p[0] for p in plans} # plan_name : plan_id
        plan_names = list(self.plan_name_to_id.keys())
        if not plan_names:
            plan_names = ["No plans available"]
            self.membership_plan_dropdown_var.set(plan_names[0])
        else:
            self.membership_plan_dropdown_var.set(plan_names[0] if plan_names else "Select Plan")
        self.membership_plan_dropdown.configure(values=plan_names)

    def save_group_membership_action(self):
        from reporter.database_manager import add_group_membership_to_db
        from datetime import datetime

        selected_member_name = self.membership_member_dropdown_var.get()
        selected_plan_name = self.membership_plan_dropdown_var.get()

        member_id = self.member_name_to_id.get(selected_member_name)
        plan_id = self.plan_name_to_id.get(selected_plan_name)

        payment_date_str = self.payment_date_entry.get().strip()
        start_date_str = self.start_date_entry.get().strip()
        amount_paid_str = self.amount_paid_entry.get().strip()
        payment_method = self.payment_method_entry.get().strip()

        # Validation
        if not member_id or selected_member_name == "No members available" or selected_member_name == "Select Member":
            self.group_membership_status_label.configure(text="Please select a member.", text_color="red")
            return
        if not plan_id or selected_plan_name == "No plans available" or selected_plan_name == "Select Plan":
            self.group_membership_status_label.configure(text="Please select a plan.", text_color="red")
            return
        if not payment_date_str or not start_date_str or not amount_paid_str or not payment_method:
            self.group_membership_status_label.configure(text="All fields must be filled.", text_color="red")
            return

        try:
            datetime.strptime(payment_date_str, '%Y-%m-%d')
            datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            self.group_membership_status_label.configure(text="Invalid date format. Use YYYY-MM-DD.", text_color="red")
            return

        try:
            amount_paid = float(amount_paid_str)
            if amount_paid < 0:
                self.group_membership_status_label.configure(text="Amount paid cannot be negative.", text_color="red")
                return
        except ValueError:
            self.group_membership_status_label.configure(text="Invalid amount. Must be a number.", text_color="red")
            return

        try:
            success = add_group_membership_to_db(
                member_id, plan_id, payment_date_str, start_date_str, amount_paid, payment_method
            )
            if success:
                self.group_membership_status_label.configure(text="Group membership added successfully!", text_color="green")
                # Clear relevant fields
                self.payment_date_entry.delete(0, 'end')
                self.payment_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
                self.start_date_entry.delete(0, 'end')
                self.start_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
                self.amount_paid_entry.delete(0, 'end')
                self.payment_method_entry.delete(0, 'end')
                # Potentially refresh a list of memberships if displayed, not currently implemented
            else:
                self.group_membership_status_label.configure(text="Failed to add group membership. Check logs.", text_color="red")
        except Exception as e:
            self.group_membership_status_label.configure(text=f"An error occurred: {e}", text_color="red")

    def display_all_members(self):
        """Clears and re-populates the scrollable frame with member data. Makes member labels clickable."""
        from reporter.database_manager import get_all_members # Keep import local if preferred

        for widget in self.members_scrollable_frame.winfo_children():
            widget.destroy()

        members = get_all_members()
        if not members:
            no_members_label = customtkinter.CTkLabel(self.members_scrollable_frame, text="No members found.")
            no_members_label.pack(padx=10, pady=10)
            # Also clear history if no members are present or selection is lost
            if self.selected_member_id: # If a member was selected, but now there are no members
                self.selected_member_id = None
                if self.selected_member_label_widget:
                    self.selected_member_label_widget.configure(fg_color="transparent") # Reset previous selection
                    self.selected_member_label_widget = None
                self.display_membership_history(None)
            return

        for i, member_data in enumerate(members):
            member_id, client_name, phone, join_date = member_data
            detail_text = f"ID: {member_id} | Name: {client_name} | Phone: {phone} | Joined: {join_date}"

            member_label_frame = customtkinter.CTkFrame(self.members_scrollable_frame, fg_color="transparent")
            member_label_frame.pack(fill="x", expand=True)

            member_label = customtkinter.CTkLabel(member_label_frame, text=detail_text, anchor="w", cursor="hand2")
            member_label.pack(padx=5, pady=2, fill="x", expand=True)

            # Store member_id with the label and make it clickable
            # Using a lambda that captures member_id and the widget itself
            member_label.bind("<Button-1>", lambda event, m_id=member_id, lbl=member_label: self.handle_member_selection(event, m_id, lbl))

            # Visual indication for selected member
            if self.selected_member_id == member_id:
                member_label.configure(fg_color="gray20") # Highlight selected
                self.selected_member_label_widget = member_label # Update the stored selected widget

            if i < len(members) - 1:
                sep = customtkinter.CTkFrame(self.members_scrollable_frame, height=1, fg_color="gray70")
                sep.pack(fill="x", padx=5, pady=2)

        # If the previously selected member is no longer in the list (e.g. deleted - though not implemented yet)
        # we should clear the history.
        if self.selected_member_id and not any(m[0] == self.selected_member_id for m in members):
            self.selected_member_id = None
            self.selected_member_label_widget = None # No need to reset color as it's gone
            self.display_membership_history(None)


    def handle_member_selection(self, event, member_id, label_widget):
        """Handles click on a member label to display their history."""
        if self.selected_member_label_widget:
            # Reset previous selection's appearance if it's different from current
            if self.selected_member_label_widget != label_widget:
                self.selected_member_label_widget.configure(fg_color="transparent") # Default CTkLabel background
            else: # Clicked on already selected member, do nothing or toggle? For now, just refresh.
                pass

        self.selected_member_id = member_id
        self.selected_member_label_widget = label_widget
        label_widget.configure(fg_color="gray20") # Highlight selected (CTk uses gray values for theme colors)

        self.display_membership_history(member_id)

    def display_membership_history(self, member_id):
        """Displays membership history for the given member_id."""
        from reporter.database_manager import get_memberships_for_member # Keep import local

        for widget in self.membership_history_frame.winfo_children():
            widget.destroy()

        if member_id is None:
            no_history_label = customtkinter.CTkLabel(self.membership_history_frame, text="Select a member to see their history.")
            no_history_label.pack(padx=10, pady=10)
            return

        history_records = get_memberships_for_member(member_id)
        if not history_records:
            no_records_label = customtkinter.CTkLabel(self.membership_history_frame, text="No membership history found for this member.")
            no_records_label.pack(padx=10, pady=10)
            return

        for i, record in enumerate(history_records):
            # record format: (plan_name, payment_date, start_date, end_date, amount_paid, payment_method, membership_id)
            plan_name, payment_date, start_date, end_date, amount_paid, payment_method, _ = record
            history_text = (f"Plan: {plan_name} | Paid: {amount_paid:.2f} ({payment_method})\n"
                            f"From: {start_date} To: {end_date} (Paid on: {payment_date})")

            history_label = customtkinter.CTkLabel(self.membership_history_frame, text=history_text, anchor="w", justify="left")
            history_label.pack(padx=5, pady=3, fill="x", expand=True)

            if i < len(history_records) - 1:
                sep = customtkinter.CTkFrame(self.membership_history_frame, height=1, fg_color="gray70")
                sep.pack(fill="x", padx=5, pady=2)


    def save_member_action(self):
        """Handles the save member button click event."""
        from reporter.database_manager import add_member_to_db # Keep import local if preferred

        name = self.name_entry.get().strip()
        phone = self.phone_entry.get().strip()

        if not name or not phone:
            self.member_status_label.configure(text="Name and Phone cannot be empty.", text_color="red")
            return

        # Basic phone validation (e.g., digits only, specific length - can be enhanced)
        if not phone.isdigit():
            self.member_status_label.configure(text="Phone number must contain only digits.", text_color="red")
            return

        try:
            success = add_member_to_db(name, phone)
            if success:
                self.member_status_label.configure(text="Member added successfully!", text_color="green")
                self.name_entry.delete(0, 'end')
                self.phone_entry.delete(0, 'end')
                self.display_all_members() # Refresh the list of all members
                self.populate_member_dropdown() # Refresh the member dropdown in group membership form
            else:
                # This case is now more specific to duplicate phone from database_manager
                self.member_status_label.configure(text="Failed to add member. Phone may already exist.", text_color="red")
        except Exception as e:
            # Catch any other unexpected errors from DB manager
            self.member_status_label.configure(text=f"An error occurred: {e}", text_color="red")


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
