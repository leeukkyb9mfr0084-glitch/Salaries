import flet as ft
from ..controller import GuiController
from typing import Optional, List, Callable # Added Callable
from datetime import datetime, date

class MembershipTab(ft.UserControl):
    def __init__(self, controller: GuiController, date_picker_ref: ft.DatePicker):
        super().__init__()
        self.controller = controller
        self.date_picker_ref = date_picker_ref # Store the shared DatePicker

        self.selected_member_id_flet: Optional[int] = None # Used by on_member_select_changed & display_membership_history_flet

        # For local date picking within this tab
        self._active_date_target_text_control: Optional[ft.Text] = None
        self._active_date_target_attr: Optional[str] = None # To store 'selected_start_date_local' or 'selected_payment_date_local'
        self._selected_start_date_local: Optional[date] = None
        self._selected_payment_date_local: Optional[date] = None

        # UI Controls for Membership Management Tab
        self.member_name_input = ft.TextField(label="Name")
        self.member_phone_input = ft.TextField(label="Phone")
        self.add_member_button = ft.ElevatedButton(text="Add Member", on_click=self.on_add_member_click)
        self.member_form_feedback_text = ft.Text("") # Feedback for add member form

        self.membership_type_dropdown = ft.Dropdown(
            label="Membership Type",
            options=[ft.dropdown.Option("Group Class"), ft.dropdown.Option("Personal Training")],
            on_change=self.on_membership_type_change_flet
        )
        self.membership_member_dropdown = ft.Dropdown(label="Select Member", options=[])
        self.membership_plan_dropdown = ft.Dropdown(label="Select Plan", options=[]) # Visible for Group Class
        self.membership_sessions_input = ft.TextField(label="Number of Sessions") # Visible for PT

        self.membership_start_date_picker_button = ft.ElevatedButton(
            text="Pick Start Date",
            on_click=lambda e: self._open_local_date_picker(e, "_selected_start_date_local", self.membership_start_date_text)
        )
        self.membership_start_date_text = ft.Text("Start Date: Not Selected")

        self.membership_payment_date_picker_button = ft.ElevatedButton(
            text="Pick Payment Date",
            on_click=lambda e: self._open_local_date_picker(e, "_selected_payment_date_local", self.membership_payment_date_text)
        )
        self.membership_payment_date_text = ft.Text("Payment Date: Not Selected") # Visible for Group Class

        self.membership_amount_paid_input = ft.TextField(label="Amount Paid")
        self.membership_payment_method_input = ft.TextField(label="Payment Method") # Visible for Group Class
        self.save_membership_button = ft.ElevatedButton(text="Save Membership", on_click=self.on_save_membership_click)
        self.membership_form_feedback_text = ft.Text("") # Feedback for add membership form

        # Tables and related controls
        self.members_table_flet = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Name")),
                ft.DataColumn(ft.Text("Phone")),
                ft.DataColumn(ft.Text("Join Date")),
            ],
            rows=[],
            on_select_changed=self.on_member_select_changed
        )
        self.member_specific_history_table_flet = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Type")),
                ft.DataColumn(ft.Text("Plan/Details")),
                ft.DataColumn(ft.Text("Paid Date")),
                ft.DataColumn(ft.Text("Start Date")),
                ft.DataColumn(ft.Text("End Date")),
                ft.DataColumn(ft.Text("Amount ($)")),
                ft.DataColumn(ft.Text("Method/Sessions")),
            ],
            rows=[]
        )
        self.delete_member_button_flet = ft.ElevatedButton(
            text="Deactivate Selected Member",
            on_click=self.on_delete_selected_member_click_flet
        )
        self.member_actions_feedback_text = ft.Text("") # Feedback for delete/deactivate actions


    # --- Methods for Local Date Picker Handling ---
    def _open_local_date_picker(self, e, target_attr_name: str, target_text_control: ft.Text):
        self._active_date_target_attr = target_attr_name
        self._active_date_target_text_control = target_text_control

        # Temporarily assign handlers to the shared date_picker_ref
        self.date_picker_ref.on_change = self._handle_local_date_change
        self.date_picker_ref.on_dismiss = self._handle_local_date_dismiss

        if self.page: # Ensure page context is available
             self.date_picker_ref.pick_date()
        else:
            print("DEBUG: MembershipTab._open_local_date_picker - self.page not available yet.")


    def _handle_local_date_change(self, e):
        selected_date_val = self.date_picker_ref.value.date() if self.date_picker_ref.value else None

        if self._active_date_target_attr and selected_date_val:
            setattr(self, self._active_date_target_attr, selected_date_val) # e.g., self._selected_start_date_local = selected_date_val
            if self._active_date_target_text_control:
                # Extract the prefix part of the text (e.g., "Start Date: ")
                prefix = self._active_date_target_text_control.value.split(":")[0] + ": "
                self._active_date_target_text_control.value = f"{prefix}{selected_date_val.strftime('%Y-%m-%d')}"
        elif self._active_date_target_text_control : # No date selected or cleared
             prefix = self._active_date_target_text_control.value.split(":")[0] + ": "
             self._active_date_target_text_control.value = f"{prefix}Not Selected"
             if self._active_date_target_attr: # Also clear the stored date attribute
                 setattr(self, self._active_date_target_attr, None)

        if self._active_date_target_text_control and self._active_date_target_text_control.page:
            self._active_date_target_text_control.update()

        # Clean up: Reset target and handlers on the shared picker (optional, or do in dismiss)
        # self._active_date_target_attr = None
        # self._active_date_target_text_control = None
        # self.date_picker_ref.on_change = None # Or restore original if any
        # self.date_picker_ref.on_dismiss = None # Or restore original if any
        # self.update()

    def _handle_local_date_dismiss(self, e):
        # Clean up targets
        self._active_date_target_attr = None
        self._active_date_target_text_control = None
        # Optionally restore original handlers if FletAppView had defaults for its own use
        # For now, assuming FletAppView will re-set them if it uses the picker directly.
        # self.date_picker_ref.on_change = self.controller.on_date_picker_change # This would require controller to hold FletAppView's methods
        # self.date_picker_ref.on_dismiss = self.controller.on_date_picker_dismiss
        # print("DEBUG: MembershipTab._handle_local_date_dismiss called")
        # self.update()


    # --- Moved Event Handlers and Helper Methods from FletAppView ---
    def on_add_member_click(self, e):
        name = self.member_name_input.value
        phone = self.member_phone_input.value

        success, message = self.controller.save_member_action(name, phone)

        self.member_form_feedback_text.value = message
        if success:
            self.member_form_feedback_text.color = ft.colors.GREEN
            self.member_name_input.value = ""
            self.member_phone_input.value = ""
            self.display_all_members_flet()
            self.populate_member_dropdowns_flet()
        else:
            self.member_form_feedback_text.color = ft.colors.RED

        if self.member_name_input.page: self.member_name_input.update()
        if self.member_phone_input.page: self.member_phone_input.update()
        if self.member_form_feedback_text.page: self.member_form_feedback_text.update()
        self.update()

    def display_all_members_flet(self, members_list: Optional[list] = None):
        if members_list is None:
            members_list = self.controller.get_filtered_members(None, None)

        self.members_table_flet.rows.clear()
        if members_list:
            for member_data in members_list:
                row = ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(member_data[0]))), # ID
                    ft.DataCell(ft.Text(str(member_data[1]))), # Name
                    ft.DataCell(ft.Text(str(member_data[2]))), # Phone
                    ft.DataCell(ft.Text(str(member_data[3]))), # Join Date
                ])
                self.members_table_flet.rows.append(row)

        if self.members_table_flet.page: self.members_table_flet.update()
        # self.update() # Might not be needed if table updates itself

    def on_member_select_changed(self, e: ft.ControlEvent):
        selected_index_str = e.data
        if selected_index_str:
            try:
                selected_index = int(selected_index_str)
                if 0 <= selected_index < len(self.members_table_flet.rows):
                    selected_row = self.members_table_flet.rows[selected_index]
                    member_id_cell = selected_row.cells[0]
                    if isinstance(member_id_cell.content, ft.Text):
                        self.selected_member_id_flet = int(member_id_cell.content.value)
                    else:
                        self.selected_member_id_flet = None
                else:
                    self.selected_member_id_flet = None
            except ValueError:
                self.selected_member_id_flet = None
            except Exception: # General exception
                self.selected_member_id_flet = None
        else:
            self.selected_member_id_flet = None

        self.display_membership_history_flet(self.selected_member_id_flet)
        # self.update() # display_membership_history_flet will update its own table

    def display_membership_history_flet(self, member_id: Optional[int]):
        self.member_specific_history_table_flet.rows.clear()
        if member_id is None:
            placeholder_text = "Select a member to view their activity."
            self.member_specific_history_table_flet.rows.append(
                ft.DataRow(cells=[ft.DataCell(ft.Text(placeholder_text), colspan=len(self.member_specific_history_table_flet.columns))])
            )
        else:
            history_records = self.controller.get_all_activity_for_member(member_id)
            if not history_records:
                placeholder_text = "No activity history found for this member."
                self.member_specific_history_table_flet.rows.append(
                    ft.DataRow(cells=[ft.DataCell(ft.Text(placeholder_text), colspan=len(self.member_specific_history_table_flet.columns))])
                )
            else:
                for record in history_records:
                    cells = [
                        ft.DataCell(ft.Text(str(record[0] if record[0] is not None else "N/A"))), # Type
                        ft.DataCell(ft.Text(str(record[1] if record[1] is not None else "N/A"))), # Plan/Details
                        ft.DataCell(ft.Text(str(record[2] if record[2] is not None else "N/A"))), # Paid Date
                        ft.DataCell(ft.Text(str(record[3] if record[3] is not None else "N/A"))), # Start Date
                        ft.DataCell(ft.Text(str(record[4] if record[4] is not None else "N/A"))), # End Date
                    ]
                    amount_paid_val = record[5]
                    amount_text = f"{amount_paid_val:.2f}" if isinstance(amount_paid_val, (int, float)) else (str(amount_paid_val) if amount_paid_val is not None else "0.00")
                    cells.append(ft.DataCell(ft.Text(amount_text)))
                    cells.append(ft.DataCell(ft.Text(str(record[6] if record[6] is not None else "N/A")))) # Method/Sessions
                    self.member_specific_history_table_flet.rows.append(ft.DataRow(cells=cells))

        if self.member_specific_history_table_flet.page: self.member_specific_history_table_flet.update()
        # self.update()

    def populate_member_dropdowns_flet(self):
        members = self.controller.get_filtered_members(None, None)
        options = [ft.dropdown.Option(key=str(m[0]), text=f"{m[1]} (ID: {m[0]})") for m in members if m[4]] # Only active

        current_value = self.membership_member_dropdown.value
        self.membership_member_dropdown.options = options
        if options:
            if current_value and any(opt.key == current_value for opt in options):
                self.membership_member_dropdown.value = current_value
            # else: self.membership_member_dropdown.value = options[0].key # Don't auto-select first one
        else:
            self.membership_member_dropdown.value = None

        if self.membership_member_dropdown.page: self.membership_member_dropdown.update()

    def on_membership_type_change_flet(self, e):
        selection = self.membership_type_dropdown.value
        is_group_class = selection == "Group Class"

        self.membership_plan_dropdown.visible = is_group_class
        self.membership_payment_date_picker_button.visible = is_group_class
        self.membership_payment_date_text.visible = is_group_class
        self.membership_payment_method_input.visible = is_group_class
        self.membership_sessions_input.visible = not is_group_class

        if self.page: # Ensure page exists before updating controls
            if self.membership_plan_dropdown.page: self.membership_plan_dropdown.update()
            if self.membership_payment_date_picker_button.page: self.membership_payment_date_picker_button.update()
            if self.membership_payment_date_text.page: self.membership_payment_date_text.update()
            if self.membership_payment_method_input.page: self.membership_payment_method_input.update()
            if self.membership_sessions_input.page: self.membership_sessions_input.update()
            self.update()

    def on_save_membership_click(self, e):
        membership_type = self.membership_type_dropdown.value
        member_id_str = self.membership_member_dropdown.value
        member_id = int(member_id_str) if member_id_str else None

        start_date_str = self._selected_start_date_local.strftime('%Y-%m-%d') if self._selected_start_date_local else None
        amount_paid_str = self.membership_amount_paid_input.value

        plan_id = None
        payment_date_str = None
        payment_method = None
        sessions_str = None

        if membership_type == "Group Class":
            plan_id_str = self.membership_plan_dropdown.value
            plan_id = int(plan_id_str) if plan_id_str else None
            payment_date_str = self._selected_payment_date_local.strftime('%Y-%m-%d') if self._selected_payment_date_local else None
            payment_method = self.membership_payment_method_input.value
        elif membership_type == "Personal Training":
            sessions_str = self.membership_sessions_input.value
            payment_date_str = start_date_str # PT payment date is the start date
            payment_method = "N/A"

        success, message = self.controller.save_membership_action(
            membership_type, member_id, start_date_str, amount_paid_str,
            plan_id, payment_date_str, payment_method, sessions_str
        )

        self.membership_form_feedback_text.value = message
        if success:
            self.membership_form_feedback_text.color = ft.colors.GREEN
            self.membership_amount_paid_input.value = ""
            self.membership_payment_method_input.value = ""
            self.membership_sessions_input.value = ""

            self._selected_start_date_local = None
            self.membership_start_date_text.value = "Start Date: Not Selected"
            self._selected_payment_date_local = None
            self.membership_payment_date_text.value = "Payment Date: Not Selected"

            # Refresh relevant parts of UI
            # self.controller.refresh_membership_history_display_flet() # This is in FletAppView, need to call it via controller if exists
            # For now, assume FletAppView handles full history refresh if needed, or this tab doesn't show it.
            if member_id is not None and self.selected_member_id_flet == member_id:
                self.display_membership_history_flet(member_id)
        else:
            self.membership_form_feedback_text.color = ft.colors.RED

        if self.membership_form_feedback_text.page: self.membership_form_feedback_text.update()
        if self.membership_amount_paid_input.page: self.membership_amount_paid_input.update()
        if self.membership_payment_method_input.page: self.membership_payment_method_input.update()
        if self.membership_sessions_input.page: self.membership_sessions_input.update()
        if self.membership_start_date_text.page: self.membership_start_date_text.update()
        if self.membership_payment_date_text.page: self.membership_payment_date_text.update()
        self.update()

    def on_delete_selected_member_click_flet(self, e):
        if self.selected_member_id_flet is None:
            self.member_actions_feedback_text.value = "No member selected to deactivate."
            self.member_actions_feedback_text.color = ft.colors.ORANGE
            if self.member_actions_feedback_text.page: self.member_actions_feedback_text.update()
            return

        member_name = "Unknown Member"
        if self.members_table_flet and self.members_table_flet.rows:
            for row in self.members_table_flet.rows:
                if row.cells and len(row.cells) > 1 and isinstance(row.cells[0].content, ft.Text) and isinstance(row.cells[1].content, ft.Text):
                    try:
                        if int(row.cells[0].content.value) == self.selected_member_id_flet:
                            member_name = row.cells[1].content.value
                            break
                    except ValueError: continue

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Deactivate Member"),
            content=ft.Text(f"Are you sure you want to deactivate member '{member_name}' (ID: {self.selected_member_id_flet})?"),
            actions=[
                ft.TextButton("Yes, Deactivate", on_click=lambda ev: self._perform_delete_member_action(True, self.selected_member_id_flet)),
                ft.TextButton("No, Cancel", on_click=lambda ev: self._perform_delete_member_action(False, self.selected_member_id_flet)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if self.page:
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()

    def _perform_delete_member_action(self, confirmed: bool, member_id: int):
        if self.page.dialog:
            self.page.dialog.open = False
            if self.page: self.page.update()

        if confirmed:
            success, message = self.controller.deactivate_member_action(member_id)
            self.member_actions_feedback_text.value = message
            self.member_actions_feedback_text.color = ft.colors.GREEN if success else ft.colors.RED
            if success:
                self.display_all_members_flet()
                self.populate_member_dropdowns_flet()
                if self.selected_member_id_flet == member_id:
                    self.selected_member_id_flet = None
                    self.display_membership_history_flet(None)
        else:
            self.member_actions_feedback_text.value = "Member deactivation cancelled."
            self.member_actions_feedback_text.color = ft.colors.ORANGE

        if self.member_actions_feedback_text.page: self.member_actions_feedback_text.update()
        # self.update() # General update might be needed

    # Placeholder for apply_member_filters_flet - not moving yet as it might be global or specific
    def apply_member_filters_flet(self, e):
        # This would interact with filter input fields not yet defined in this class
        # For now, this is a NOP. If specific filters for this tab are needed, they'd be added.
        print("DEBUG: apply_member_filters_flet (in MembershipTab) - Placeholder")
        pass

    # Placeholder for clear_member_filters_flet
    def clear_member_filters_flet(self, e):
        # This would clear filter input fields not yet defined in this class
        self.display_all_members_flet(self.controller.get_filtered_members(None, None))
        print("DEBUG: clear_member_filters_flet (in MembershipTab) - Placeholder, cleared to all members")
        # self.update()

    def _get_membership_status_flet(self, end_date_str: Optional[str]) -> str:
        """Helper to determine membership status. Copied from FletAppView, might not be used if history table is different."""
        if not end_date_str or end_date_str.lower() == "n/a" or end_date_str.strip() == "":
            return "N/A"
        try:
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            return "Active" if end_date_obj >= date.today() else "Inactive"
        except ValueError:
            return "Invalid Date"

    def populate_plan_dropdowns_flet(self):
        """Populates the membership_plan_dropdown with active plans. Copied from FletAppView."""
        plans = self.controller.get_active_plans()  # Fetches (id, name, duration)
        options = [ft.dropdown.Option(key=str(p[0]), text=f"{p[1]} ({p[2]} days)") for p in plans]

        current_value = self.membership_plan_dropdown.value
        self.membership_plan_dropdown.options = options
        if options:
            if current_value and any(opt.key == current_value for opt in options):
                self.membership_plan_dropdown.value = current_value
            # else: self.membership_plan_dropdown.value = options[0].key # Don't auto-select
        else:
            self.membership_plan_dropdown.value = None

        if self.membership_plan_dropdown.page: self.membership_plan_dropdown.update()


    # --- Build Method ---
    def build(self):
        # Initial data population calls
        self.display_all_members_flet()
        self.populate_member_dropdowns_flet()
        self.populate_plan_dropdowns_flet() # Ensure plans are loaded for the dropdown
        self.on_membership_type_change_flet(None) # Set initial visibility of form fields

        # Define the layout for the Membership Management Tab
        member_form_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Add New Member", weight=ft.FontWeight.BOLD),
                    self.member_name_input,
                    self.member_phone_input,
                    self.add_member_button,
                    self.member_form_feedback_text, # For add member
                    ft.Divider(),
                    ft.Text("Add New Membership", weight=ft.FontWeight.BOLD),
                    self.membership_type_dropdown,
                    self.membership_member_dropdown,
                    self.membership_plan_dropdown,
                    self.membership_sessions_input,
                    ft.Row([self.membership_start_date_picker_button, self.membership_start_date_text]),
                    ft.Row([self.membership_payment_date_picker_button, self.membership_payment_date_text]),
                    self.membership_amount_paid_input,
                    self.membership_payment_method_input,
                    self.save_membership_button,
                    self.membership_form_feedback_text, # For add membership
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=10 # Added spacing
            ),
            expand=1,
            bgcolor=ft.colors.BLUE_GREY_200, # Consistent with original
            padding=10,
            alignment=ft.alignment.top_center,
        )

        table_area_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("All Members", weight=ft.FontWeight.BOLD),
                    self.members_table_flet,
                    ft.Divider(),
                    ft.Text("Selected Member Activity", weight=ft.FontWeight.BOLD),
                    self.member_specific_history_table_flet,
                    self.delete_member_button_flet,
                    self.member_actions_feedback_text,
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True, # Ensure this column expands within its parent container
                spacing=10
            ),
            expand=2, # Consistent with original
            bgcolor=ft.colors.BLUE_GREY_300, # Consistent with original
            padding=10,
            alignment=ft.alignment.top_center
        )

        # Return the root control for this tab
        return ft.Row(
            controls=[
                member_form_container,
                table_area_container,
            ],
            vertical_alignment=ft.CrossAxisAlignment.START # Align to top
        )

    # Optional: did_mount or will_unmount for UserControl
    def did_mount(self):
        # print("DEBUG: MembershipTab did_mount")
        # Initial population calls can also go here if they depend on self.page being available
        # For now, they are in build, which should be fine as controls are created there.
        # self.page.update() # If any updates are needed once mounted.
        pass
