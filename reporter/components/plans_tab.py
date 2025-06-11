import flet as ft
from ..gui import GuiController # Corrected import
from typing import Optional

class PlansTab(ft.Row):  # Changed base class to ft.Row
    def __init__(self, controller: GuiController, flet_app_view_ref):
        super().__init__()  # Call super().__init__ for ft.Row
        self.controller = controller
        self.flet_app_view_ref = flet_app_view_ref # For cross-tab updates (e.g., refreshing member plan dropdown)

        self.selected_plan_id: Optional[int] = None
        self.current_plan_id_to_update: Optional[int] = None # Used for edit/toggle status context

        # --- UI Control Declarations ---
        self.plan_name_input = ft.TextField(label="Plan Name")
        self.plan_duration_input = ft.TextField(label="Duration (days)", input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]"))
        self.save_plan_button = ft.ElevatedButton(text="Save Plan", on_click=self.on_save_plan_click)
        self.plan_form_feedback_text = ft.Text("")

        self.edit_plan_button = ft.ElevatedButton(text="Edit Selected Plan", on_click=self.on_edit_selected_plan_click, disabled=True)
        self.clear_plan_form_button = ft.ElevatedButton(text="Clear Form / Cancel Edit", on_click=self.on_clear_plan_form_click)

        self.toggle_plan_status_button = ft.ElevatedButton(text="Toggle Status (Activate/Deactivate)", on_click=self.on_toggle_plan_status_click, disabled=True)
        self.delete_plan_button = ft.ElevatedButton(text="Delete Selected Plan", on_click=self.on_delete_selected_plan_click, disabled=True, color=ft.colors.RED_ACCENT)

        self.plans_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Name")),
                ft.DataColumn(ft.Text("Duration (days)")),
                ft.DataColumn(ft.Text("Is Active?")),
            ],
            rows=[],
            on_select_changed=self.on_plan_select_changed,
            expand=True # Make table take available vertical space in its container
        )

        # --- Layout Definition (as self.controls for ft.Row) ---
        form_column = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Manage Plans", weight=ft.FontWeight.BOLD, size=20),
                    self.plan_name_input,
                    self.plan_duration_input,
                    self.save_plan_button,
                    self.plan_form_feedback_text,
                    ft.Divider(),
                    self.clear_plan_form_button,
                ],
                spacing=10,
                width=350, # Fixed width for the form column
                alignment=ft.MainAxisAlignment.START,
            ),
            padding=10,
            bgcolor=ft.colors.BLUE_GREY_200, # Matches MembershipTab form color
            expand=1 # Takes 1 part of the row space
        )

        table_column = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("All Plans", weight=ft.FontWeight.BOLD, size=20),
                    self.plans_table,
                    ft.Row( # Action buttons for selected plan
                        controls=[
                            self.edit_plan_button,
                            self.toggle_plan_status_button,
                            self.delete_plan_button,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND, # Spread them out
                        spacing=10
                    )
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.START,
                expand=True # Ensure this column expands
            ),
            padding=10,
            bgcolor=ft.colors.BLUE_GREY_300, # Matches MembershipTab table area color
            expand=2 # Takes 2 parts of the row space
        )

        self.controls = [form_column, table_column]
        # Properties for the main Row (self)
        self.expand = True
        self.vertical_alignment = ft.CrossAxisAlignment.START

    def did_mount(self):
        self.display_all_plans()
        if self.page:
            self.page.update()

    def on_plan_select_changed(self, e: ft.ControlEvent):
        selected_index_str = e.data
        if selected_index_str:
            try:
                selected_index = int(selected_index_str)
                if 0 <= selected_index < len(self.plans_table.rows):
                    selected_row = self.plans_table.rows[selected_index]
                    plan_id_cell = selected_row.cells[0]
                    if isinstance(plan_id_cell.content, ft.Text):
                        self.selected_plan_id = int(plan_id_cell.content.value)
                        self.edit_plan_button.disabled = False
                        self.toggle_plan_status_button.disabled = False
                        self.delete_plan_button.disabled = False
                    else: # Should not happen
                        self._reset_selection_state()
                else: self._reset_selection_state()
            except ValueError: self._reset_selection_state()
        else: self._reset_selection_state()

        controls_to_update = [self.edit_plan_button, self.toggle_plan_status_button, self.delete_plan_button]
        for control in controls_to_update:
            if control.page: control.update()
        # self.update() # Main row update

    def _reset_selection_state(self):
        self.selected_plan_id = None
        self.edit_plan_button.disabled = True
        self.toggle_plan_status_button.disabled = True
        self.delete_plan_button.disabled = True
        # current_plan_id_to_update is reset by clear_plan_form

    def display_all_plans(self, plans_list: Optional[list] = None):
        if plans_list is None:
            plans_list = self.controller.get_all_plans_with_inactive() # Fetches all, active and inactive

        self.plans_table.rows.clear()
        if plans_list:
            for plan_data in plans_list: # id, name, duration, is_active
                self.plans_table.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(plan_data[0]))),
                    ft.DataCell(ft.Text(str(plan_data[1]))),
                    ft.DataCell(ft.Text(str(plan_data[2]))),
                    ft.DataCell(ft.Text("Yes" if plan_data[3] else "No")),
                ]))

        self._reset_selection_state() # Also reset buttons when table refreshes
        if self.plans_table.page: self.plans_table.update()
        # self.update()

    def on_save_plan_click(self, e):
        name = self.plan_name_input.value
        duration_str = self.plan_duration_input.value

        if not name.strip():
            self.plan_form_feedback_text.value = "Plan Name cannot be empty."
            self.plan_form_feedback_text.color = ft.Colors.RED # Assuming ft.Colors
            if self.plan_form_feedback_text.page: self.plan_form_feedback_text.update()
            return

        try:
            duration_days = int(duration_str)
            if duration_days <= 0:
                raise ValueError("Duration must be positive.")
        except ValueError:
            self.plan_form_feedback_text.value = "Duration must be a positive number of days."
            self.plan_form_feedback_text.color = ft.Colors.RED # Assuming ft.Colors
            if self.plan_form_feedback_text.page: self.plan_form_feedback_text.update()
            return

        # If validation passes, proceed to call controller
        success, message = self.controller.save_plan_action(
            name, duration_str, self.current_plan_id_to_update # Pass duration_str as controller expects it
        )

        self.plan_form_feedback_text.value = message
        if success:
            self.plan_form_feedback_text.color = ft.Colors.GREEN # Assuming ft.Colors
            self.display_all_plans()
            self.on_clear_plan_form_click(None) # Clear form and reset edit state
            if self.flet_app_view_ref: # Refresh dropdowns in other tabs
                 self.flet_app_view_ref.refresh_membership_plan_dropdowns()
        else:
            self.plan_form_feedback_text.color = ft.Colors.RED # Assuming ft.Colors

        if self.plan_form_feedback_text.page: self.plan_form_feedback_text.update()
        # self.update()

    def on_edit_selected_plan_click(self, e):
        if self.selected_plan_id is None:
            self.plan_form_feedback_text.value = "No plan selected to edit."
            self.plan_form_feedback_text.color = ft.colors.ORANGE
            if self.plan_form_feedback_text.page: self.plan_form_feedback_text.update()
            return

        plan_details = self.controller.get_plan_details(self.selected_plan_id)
        if plan_details: # id, name, duration, is_active
            self.plan_name_input.value = plan_details[1]
            self.plan_duration_input.value = str(plan_details[2])
            self.current_plan_id_to_update = plan_details[0] # Set context for save
            self.save_plan_button.text = "Update Plan"
            self.plan_form_feedback_text.value = f"Editing Plan ID: {plan_details[0]}"
            self.plan_form_feedback_text.color = ft.Colors.BLUE # Assuming ft.Colors
        else:
            self.plan_form_feedback_text.value = "Failed to load plan details for editing."
            self.plan_form_feedback_text.color = ft.Colors.RED # Assuming ft.Colors

        controls_to_update = [self.plan_name_input, self.plan_duration_input, self.save_plan_button, self.plan_form_feedback_text]
        for control in controls_to_update:
            if control.page: control.update()
        # self.update()

    def on_clear_plan_form_click(self, e):
        self.plan_name_input.value = ""
        self.plan_duration_input.value = ""
        self.current_plan_id_to_update = None
        self.save_plan_button.text = "Save Plan"
        self.plan_form_feedback_text.value = ""
        # self.selected_plan_id = None # Don't clear this, user might want to perform other actions
        # self._reset_selection_state() # This would also deselect from table and disable buttons

        controls_to_update = [self.plan_name_input, self.plan_duration_input, self.save_plan_button, self.plan_form_feedback_text]
        for control in controls_to_update:
            if control.page: control.update()
        # self.update()

    def on_toggle_plan_status_click(self, e):
        if self.selected_plan_id is None:
            # This should not happen if button is enabled correctly
            self.plan_form_feedback_text.value = "Error: No plan selected for status toggle."
            self.plan_form_feedback_text.color = ft.Colors.RED # Assuming ft.Colors
            if self.plan_form_feedback_text.page: self.plan_form_feedback_text.update()
            return

        success, message = self.controller.toggle_plan_status_action(self.selected_plan_id)
        # Use plan_form_feedback_text for messages from toggle/delete actions too for simplicity
        self.plan_form_feedback_text.value = message
        self.plan_form_feedback_text.color = ft.Colors.GREEN if success else ft.Colors.RED # Assuming ft.Colors
        if success:
            self.display_all_plans()
            if self.flet_app_view_ref: # Refresh dropdowns in other tabs
                 self.flet_app_view_ref.refresh_membership_plan_dropdowns()

        if self.plan_form_feedback_text.page: self.plan_form_feedback_text.update()
        # self.update()

    def on_delete_selected_plan_click(self, e):
        if self.selected_plan_id is None:
            self.plan_form_feedback_text.value = "No plan selected to delete."
            self.plan_form_feedback_text.color = ft.Colors.ORANGE # Assuming ft.Colors
            if self.plan_form_feedback_text.page: self.plan_form_feedback_text.update()
            return

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Delete Plan"),
            content=ft.Text(f"Are you sure you want to delete plan ID {self.selected_plan_id}? This may affect existing memberships."),
            actions=[
                ft.TextButton("Yes, Delete", on_click=lambda ev: self._perform_delete_plan_action(True, self.selected_plan_id)),
                ft.TextButton("No, Cancel", on_click=lambda ev: self._perform_delete_plan_action(False, self.selected_plan_id)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if self.page:
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()

    def _perform_delete_plan_action(self, confirmed: bool, plan_id: int):
        if self.page.dialog:
            self.page.dialog.open = False
            if self.page: self.page.update()

        if confirmed:
            success, message = self.controller.delete_plan_action(plan_id)
            self.plan_form_feedback_text.value = message
            self.plan_form_feedback_text.color = ft.Colors.GREEN if success else ft.Colors.RED # Assuming ft.Colors
            if success:
                self.display_all_plans()
                self.on_clear_plan_form_click(None) # Clear form if deleted plan was being edited
                if self.flet_app_view_ref: # Refresh dropdowns
                     self.flet_app_view_ref.refresh_membership_plan_dropdowns()
        else:
            self.plan_form_feedback_text.value = "Plan deletion cancelled."
            self.plan_form_feedback_text.color = ft.Colors.ORANGE # Assuming ft.Colors

        if self.plan_form_feedback_text.page: self.plan_form_feedback_text.update()
        # self.update()

    def is_isolated(self): # Added as methods call self.update() or update children
        return True
