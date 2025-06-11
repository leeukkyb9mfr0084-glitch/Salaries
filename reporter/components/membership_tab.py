import flet as ft
from ..gui import GuiController
from typing import Optional
from datetime import datetime, date

class MembershipTab(ft.Row):  # Changed base class
    def __init__(self, controller: GuiController, date_picker_ref: ft.DatePicker):
        super().__init__()  # Call super().__init__ for ft.Row
        self.controller = controller
        self.date_picker_ref = date_picker_ref

        self.selected_member_id_flet: Optional[int] = None

        # For local date picking
        self._active_date_target_text_control: Optional[ft.Text] = None
        self._active_date_target_attr: Optional[str] = None
        self._selected_start_date_local: Optional[date] = None
        self._selected_payment_date_local: Optional[date] = None

        # Define UI Controls directly in __init__
        self.member_name_input = ft.TextField(label="Name")
        self.member_phone_input = ft.TextField(label="Phone")
        self.add_member_button = ft.ElevatedButton(text="Add Member", on_click=self.on_add_member_click)
        self.member_form_feedback_text = ft.Text("")

        self.membership_type_dropdown = ft.Dropdown(
            label="Membership Type",
            options=[ft.dropdown.Option("Group Class"), ft.dropdown.Option("Personal Training")],
            on_change=self.on_membership_type_change_flet
        )
        self.membership_member_dropdown = ft.Dropdown(label="Select Member", options=[])
        self.membership_plan_dropdown = ft.Dropdown(label="Select Plan", options=[])
        self.membership_sessions_input = ft.TextField(label="Number of Sessions")

        self.membership_start_date_picker_button = ft.ElevatedButton(
            text="Pick Start Date",
            on_click=lambda e: self._open_local_date_picker(e, "_selected_start_date_local", self.membership_start_date_text)
        )
        self.membership_start_date_text = ft.Text("Start Date: Not Selected")

        self.membership_payment_date_picker_button = ft.ElevatedButton(
            text="Pick Payment Date",
            on_click=lambda e: self._open_local_date_picker(e, "_selected_payment_date_local", self.membership_payment_date_text)
        )
        self.membership_payment_date_text = ft.Text("Payment Date: Not Selected")

        self.membership_amount_paid_input = ft.TextField(label="Amount Paid")
        self.membership_payment_method_input = ft.TextField(label="Payment Method")
        self.save_membership_button = ft.ElevatedButton(text="Save Membership", on_click=self.on_save_membership_click)
        self.membership_form_feedback_text = ft.Text("")

        self.members_table_flet = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")), ft.DataColumn(ft.Text("Name")),
                ft.DataColumn(ft.Text("Phone")), ft.DataColumn(ft.Text("Join Date")),
            ],
            rows=[]
        )
        self.members_table_flet.on_select_changed = self.on_member_select_changed
        self.member_specific_history_table_flet = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Type")), ft.DataColumn(ft.Text("Plan/Details")),
                ft.DataColumn(ft.Text("Paid Date")), ft.DataColumn(ft.Text("Start Date")),
                ft.DataColumn(ft.Text("End Date")), ft.DataColumn(ft.Text("Amount ($)")),
                ft.DataColumn(ft.Text("Method/Sessions")),
            ],
            rows=[]
        )
        self.delete_member_button_flet = ft.ElevatedButton(
            text="Deactivate Selected Member", on_click=self.on_delete_selected_member_click_flet
        )
        self.member_actions_feedback_text = ft.Text("")

        # Define layout structure from the old build method
        member_form_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Add New Member", weight=ft.FontWeight.BOLD),
                    self.member_name_input, self.member_phone_input,
                    self.add_member_button, self.member_form_feedback_text,
                    ft.Divider(),
                    ft.Text("Add New Membership", weight=ft.FontWeight.BOLD),
                    self.membership_type_dropdown, self.membership_member_dropdown,
                    self.membership_plan_dropdown, self.membership_sessions_input,
                    ft.Row([self.membership_start_date_picker_button, self.membership_start_date_text]),
                    ft.Row([self.membership_payment_date_picker_button, self.membership_payment_date_text]),
                    self.membership_amount_paid_input, self.membership_payment_method_input,
                    self.save_membership_button, self.membership_form_feedback_text,
                ], scroll=ft.ScrollMode.AUTO, spacing=10
            ),
            expand=1, bgcolor=ft.Colors.BLUE_GREY_200, padding=10, alignment=ft.alignment.top_center,
        )

        table_area_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("All Members", weight=ft.FontWeight.BOLD),
                    self.members_table_flet,
                    ft.Divider(),
                    ft.Text("Selected Member Activity", weight=ft.FontWeight.BOLD),
                    self.member_specific_history_table_flet,
                    self.delete_member_button_flet, self.member_actions_feedback_text,
                ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=10
            ),
            expand=2, bgcolor=ft.Colors.BLUE_GREY_300, padding=10, alignment=ft.alignment.top_center
        )

        # Assign controls and properties to self (the Row)
        self.controls = [member_form_container, table_area_container]
        self.vertical_alignment = ft.CrossAxisAlignment.START
        # Any other properties of the main Row would be set here, e.g. self.expand = True

    def did_mount(self):
        # Initial data population calls moved from build() to did_mount()
        self.display_all_members_flet()
        self.populate_member_dropdowns_flet()
        self.populate_plan_dropdowns_flet()
        self.on_membership_type_change_flet(None) # Set initial visibility
        if self.page: # Ensure page is available for updates if necessary
            self.page.update()

    # --- Methods for Local Date Picker Handling ---
    def _open_local_date_picker(self, e, target_attr_name: str, target_text_control: ft.Text):
        self._active_date_target_attr = target_attr_name
        self._active_date_target_text_control = target_text_control
        self.date_picker_ref.on_change = self._handle_local_date_change
        self.date_picker_ref.on_dismiss = self._handle_local_date_dismiss
        if self.page: self.date_picker_ref.pick_date()
        else: print("DEBUG: MembershipTab._open_local_date_picker - self.page not available yet.")

    def _handle_local_date_change(self, e):
        selected_date_val = self.date_picker_ref.value.date() if self.date_picker_ref.value else None
        if self._active_date_target_attr and selected_date_val:
            setattr(self, self._active_date_target_attr, selected_date_val)
            if self._active_date_target_text_control:
                prefix = self._active_date_target_text_control.value.split(":")[0] + ": "
                self._active_date_target_text_control.value = f"{prefix}{selected_date_val.strftime('%Y-%m-%d')}"
        elif self._active_date_target_text_control :
             prefix = self._active_date_target_text_control.value.split(":")[0] + ": "
             self._active_date_target_text_control.value = f"{prefix}Not Selected"
             if self._active_date_target_attr:
                 setattr(self, self._active_date_target_attr, None)
        if self._active_date_target_text_control and self._active_date_target_text_control.page:
            self._active_date_target_text_control.update()

    def _handle_local_date_dismiss(self, e):
        self._active_date_target_attr = None
        self._active_date_target_text_control = None

    # --- Event Handlers and Helper Methods ---
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
        if members_list is None: members_list = self.controller.get_filtered_members(None, None)
        self.members_table_flet.rows.clear()
        if members_list:
            for member_data in members_list:
                self.members_table_flet.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(member_data[0]))), ft.DataCell(ft.Text(str(member_data[1]))),
                    ft.DataCell(ft.Text(str(member_data[2]))), ft.DataCell(ft.Text(str(member_data[3]))),
                ]))
        if self.members_table_flet.page: self.members_table_flet.update()

    def on_member_select_changed(self, e: ft.ControlEvent):
        selected_index_str = e.data
        if selected_index_str:
            try:
                selected_index = int(selected_index_str)
                if 0 <= selected_index < len(self.members_table_flet.rows):
                    member_id_cell = self.members_table_flet.rows[selected_index].cells[0]
                    self.selected_member_id_flet = int(member_id_cell.content.value) if isinstance(member_id_cell.content, ft.Text) else None
                else: self.selected_member_id_flet = None
            except (ValueError, Exception): self.selected_member_id_flet = None
        else: self.selected_member_id_flet = None
        self.display_membership_history_flet(self.selected_member_id_flet)

    def display_membership_history_flet(self, member_id: Optional[int]):
        self.member_specific_history_table_flet.rows.clear()
        colspan = len(self.member_specific_history_table_flet.columns)
        if member_id is None:
            text = "Select a member to view their activity."
            self.member_specific_history_table_flet.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(text), colspan=colspan)]))
        else:
            history_records = self.controller.get_all_activity_for_member(member_id)
            if not history_records:
                text = "No activity history found for this member."
                self.member_specific_history_table_flet.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(text), colspan=colspan)]))
            else:
                for record in history_records:
                    cells = [ft.DataCell(ft.Text(str(r) if r is not None else "N/A")) for r in record[:5]]
                    amount_val = record[5]
                    amount_str = f"{amount_val:.2f}" if isinstance(amount_val, (int, float)) else (str(amount_val) if amount_val is not None else "0.00")
                    cells.append(ft.DataCell(ft.Text(amount_str)))
                    cells.append(ft.DataCell(ft.Text(str(record[6]) if record[6] is not None else "N/A")))
                    self.member_specific_history_table_flet.rows.append(ft.DataRow(cells=cells))
        if self.member_specific_history_table_flet.page: self.member_specific_history_table_flet.update()

    def populate_member_dropdowns_flet(self):
        members = self.controller.get_filtered_members(None, None) # Assuming active ones
        options = [ft.dropdown.Option(key=str(m[0]), text=f"{m[1]} (ID: {m[0]})") for m in members if m[4]] # m[4] is is_active
        current_value = self.membership_member_dropdown.value
        self.membership_member_dropdown.options = options
        if options and current_value and any(opt.key == current_value for opt in options):
            self.membership_member_dropdown.value = current_value
        else: self.membership_member_dropdown.value = None
        if self.membership_member_dropdown.page: self.membership_member_dropdown.update()

    def on_membership_type_change_flet(self, e):
        is_group = self.membership_type_dropdown.value == "Group Class"
        self.membership_plan_dropdown.visible = is_group
        self.membership_payment_date_picker_button.visible = is_group
        self.membership_payment_date_text.visible = is_group
        self.membership_payment_method_input.visible = is_group
        self.membership_sessions_input.visible = not is_group
        if self.page: self.update() # Update the whole tab's layout

    def on_save_membership_click(self, e):
        member_id = int(self.membership_member_dropdown.value) if self.membership_member_dropdown.value else None
        start_date = self._selected_start_date_local.strftime('%Y-%m-%d') if self._selected_start_date_local else None
        amount_paid = self.membership_amount_paid_input.value
        plan_id, pay_date, pay_method, sessions = None, None, None, None

        if self.membership_type_dropdown.value == "Group Class":
            plan_id = int(self.membership_plan_dropdown.value) if self.membership_plan_dropdown.value else None
            pay_date = self._selected_payment_date_local.strftime('%Y-%m-%d') if self._selected_payment_date_local else None
            pay_method = self.membership_payment_method_input.value
        else: # Personal Training
            sessions = self.membership_sessions_input.value
            pay_date = start_date # PT payment date is its start date
            pay_method = "N/A"

        success, message = self.controller.save_membership_action(
            self.membership_type_dropdown.value, member_id, start_date, amount_paid,
            plan_id, pay_date, pay_method, sessions
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
            if member_id is not None and self.selected_member_id_flet == member_id:
                self.display_membership_history_flet(member_id)
        else: self.membership_form_feedback_text.color = ft.colors.RED

        controls_to_update = [
            self.membership_form_feedback_text, self.membership_amount_paid_input,
            self.membership_payment_method_input, self.membership_sessions_input,
            self.membership_start_date_text, self.membership_payment_date_text
        ]
        for control in controls_to_update:
            if control.page: control.update()
        self.update()


    def on_delete_selected_member_click_flet(self, e):
        if self.selected_member_id_flet is None:
            self.member_actions_feedback_text.value = "No member selected."
            self.member_actions_feedback_text.color = ft.colors.ORANGE
            if self.member_actions_feedback_text.page: self.member_actions_feedback_text.update()
            return

        member_name = "Selected Member" # Simplified
        dialog = ft.AlertDialog(
            modal=True, title=ft.Text("Confirm Deactivate"),
            content=ft.Text(f"Deactivate member '{member_name}' (ID: {self.selected_member_id_flet})?"),
            actions=[
                ft.TextButton("Yes", on_click=lambda ev: self._perform_deactivate_member_action(True, self.selected_member_id_flet)),
                ft.TextButton("No", on_click=lambda ev: self._perform_deactivate_member_action(False, self.selected_member_id_flet)),
            ], actions_alignment=ft.MainAxisAlignment.END,
        )
        if self.page:
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()

    def _perform_deactivate_member_action(self, confirmed: bool, member_id: int):
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
            self.member_actions_feedback_text.value = "Deactivation cancelled."
            self.member_actions_feedback_text.color = ft.colors.ORANGE
        if self.member_actions_feedback_text.page: self.member_actions_feedback_text.update()

    def populate_plan_dropdowns_flet(self):
        plans = self.controller.get_active_plans()
        options = [ft.dropdown.Option(key=str(p[0]), text=f"{p[1]} ({p[2]} days)") for p in plans]
        current_value = self.membership_plan_dropdown.value
        self.membership_plan_dropdown.options = options
        if options and current_value and any(opt.key == current_value for opt in options):
            self.membership_plan_dropdown.value = current_value
        else: self.membership_plan_dropdown.value = None
        if self.membership_plan_dropdown.page: self.membership_plan_dropdown.update()

    # Removed _get_membership_status_flet as it's not used by this tab directly.
    # Removed placeholder filters apply_member_filters_flet and clear_member_filters_flet
    # build() method is removed. Layout is defined in __init__.
    # did_mount() handles initial data loading.
    # Note: self.update() calls in some handlers might need to be reviewed if is_isolated=True is set.
    # For now, assuming is_isolated=False (default).

    # According to docs, if a custom control calls self.update(), it should be isolated.
    # Many methods here call self.update() or update individual controls.
    # Let's make it isolated.
    def is_isolated(self):
        return True
