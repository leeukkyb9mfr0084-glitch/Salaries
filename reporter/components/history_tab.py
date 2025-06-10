import flet as ft
from ..gui import GuiController # Corrected import
from typing import Optional
from datetime import datetime, date # Corrected from just 'datetime'

class HistoryTab(ft.Column):  # Changed base class to ft.Column
    def __init__(self, controller: GuiController, date_picker_ref: ft.DatePicker, flet_app_view_ref):
        super().__init__()  # Call super().__init__ for ft.Column
        self.controller = controller
        self.date_picker = date_picker_ref # Used for join_date_filter
        self.flet_app_view_ref = flet_app_view_ref # For cross-tab updates

        self.selected_transaction_id: Optional[int] = None

        # --- UI Control Declarations ---
        self.history_actions_feedback_text = ft.Text("")
        self.delete_transaction_button = ft.ElevatedButton(
            text="Delete Selected Transaction",
            on_click=self.on_delete_selected_transaction_click,
            disabled=True # Initially no transaction is selected
        )
        self.history_name_filter_input = ft.TextField(label="Filter by Name", expand=True)
        self.history_phone_filter_input = ft.TextField(label="Filter by Phone", expand=True)

        self.history_join_date_filter_text = ft.Text("No date selected")
        self.history_join_date_filter_input_button = ft.ElevatedButton(
            "Filter by Join Date",
            icon=ft.icons.CALENDAR_MONTH,
            on_click=lambda e: self._pick_join_date_filter(e),
        )
        self._selected_join_date_filter: Optional[date] = None # Internal state for the date picker

        self.apply_history_filters_button = ft.ElevatedButton(text="Apply Filters", on_click=self.apply_history_filters)
        self.clear_history_filters_button = ft.ElevatedButton(text="Clear Filters", on_click=self.clear_history_filters)

        self.full_history_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Trx ID")),
                ft.DataColumn(ft.Text("Member Name")),
                ft.DataColumn(ft.Text("Member Phone")),
                ft.DataColumn(ft.Text("Type")),
                ft.DataColumn(ft.Text("Plan/Details")),
                ft.DataColumn(ft.Text("Paid Date")),
                ft.DataColumn(ft.Text("Start Date")),
                ft.DataColumn(ft.Text("End Date")),
                ft.DataColumn(ft.Text("Amount ($)")),
                ft.DataColumn(ft.Text("Method/Sessions")),
                ft.DataColumn(ft.Text("Status")), # Added Status
            ],
            rows=[],
            on_select_changed=self.on_full_history_select_changed,
            expand=True # Make table take available vertical space
        )

        # --- Layout Definition (as self.controls for ft.Column) ---
        filter_row_1 = ft.Row(
            controls=[self.history_name_filter_input, self.history_phone_filter_input],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        filter_row_2 = ft.Row(
            controls=[
                self.history_join_date_filter_input_button,
                self.history_join_date_filter_text,
                self.apply_history_filters_button,
                self.clear_history_filters_button,
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER, # Align items nicely
            spacing=10
        )

        actions_row = ft.Row(
            controls=[self.delete_transaction_button, self.history_actions_feedback_text],
            alignment=ft.MainAxisAlignment.START
        )

        self.controls = [
            ft.Text("Full Membership History & Transactions", weight=ft.FontWeight.BOLD, size=20),
            filter_row_1,
            filter_row_2,
            ft.Divider(),
            ft.Text("All Transactions:", weight=ft.FontWeight.BOLD),
            self.full_history_table,
            actions_row
        ]
        # Properties for the main Column (self)
        self.expand = True
        self.scroll = ft.ScrollMode.ADAPTIVE # Make column scrollable if content overflows
        self.spacing = 10
        self.padding = 10


    def _pick_join_date_filter(self, e):
        self.date_picker.on_change = self._on_join_date_filter_selected
        self.date_picker.on_dismiss = lambda _: None # Simple dismiss
        if self.page:
            self.date_picker.pick_date()

    def _on_join_date_filter_selected(self, e):
        if self.date_picker.value:
            self._selected_join_date_filter = self.date_picker.value.date()
            self.history_join_date_filter_text.value = self._selected_join_date_filter.strftime("%Y-%m-%d")
        else:
            self._selected_join_date_filter = None
            self.history_join_date_filter_text.value = "No date selected"
        if self.history_join_date_filter_text.page:
            self.history_join_date_filter_text.update()

    def did_mount(self):
        self.refresh_membership_history_display()
        if self.page:
            self.page.update()

    def on_full_history_select_changed(self, e: ft.ControlEvent):
        selected_index_str = e.data
        if selected_index_str: # A row is selected
            try:
                selected_index = int(selected_index_str)
                if 0 <= selected_index < len(self.full_history_table.rows):
                    selected_row = self.full_history_table.rows[selected_index]
                    trx_id_cell = selected_row.cells[0]
                    if isinstance(trx_id_cell.content, ft.Text):
                        self.selected_transaction_id = int(trx_id_cell.content.value)
                        self.delete_transaction_button.disabled = False
                    else: # Should not happen if table is populated correctly
                        self.selected_transaction_id = None
                        self.delete_transaction_button.disabled = True
                else: # Index out of bounds
                    self.selected_transaction_id = None
                    self.delete_transaction_button.disabled = True
            except ValueError: # Invalid index string
                self.selected_transaction_id = None
                self.delete_transaction_button.disabled = True
        else: # No row selected (deselected)
            self.selected_transaction_id = None
            self.delete_transaction_button.disabled = True

        if self.delete_transaction_button.page:
            self.delete_transaction_button.update()
        # self.update() # Consider if needed, on_select_changed might update parent implicitly

    def _get_membership_status(self, end_date_str: Optional[str]) -> str:
        if not end_date_str or end_date_str.lower() == "n/a" or end_date_str.strip() == "":
            return "N/A" # Or perhaps "Ongoing" if it's a PT session count
        try:
            end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            return "Active" if end_date_obj >= date.today() else "Expired"
        except ValueError:
            return "Invalid Date" # Should not happen with DB data

    def refresh_membership_history_display(self, transactions_list: Optional[list] = None):
        if transactions_list is None:
            # Default: get all transactions if no specific list is provided
            transactions_list = self.controller.get_filtered_transaction_history(None, None, None)

        self.full_history_table.rows.clear()
        if transactions_list:
            for trx_data in transactions_list:
                # New column order:
                # 0: t.transaction_id, 1: t.member_id, 2: t.transaction_type, 3: t.plan_id,
                # 4: t.payment_date, 5: t.start_date, 6: t.end_date,
                # 7: t.amount_paid, 8: t.payment_method, 9: t.sessions,
                # 10: m.client_name, 11: m.phone, 12: m.join_date,
                # 13: p.plan_name

                transaction_type = str(trx_data[2]) if trx_data[2] else "N/A"

                plan_details = "N/A"
                if transaction_type == 'Group Class':
                    plan_details = str(trx_data[13]) if trx_data[13] else "N/A" # p.plan_name
                elif transaction_type == 'Personal Training':
                    plan_details = f"{str(trx_data[9])} sessions" if trx_data[9] else "N/A" # t.sessions

                method_sessions = "N/A"
                if transaction_type == 'Group Class':
                    method_sessions = str(trx_data[8]) if trx_data[8] else "N/A" # t.payment_method
                elif transaction_type == 'Personal Training':
                    # For PT, "Method/Sessions" column could show sessions or be N/A if details are in "Plan/Details"
                    method_sessions = f"{str(trx_data[9])} sessions" if trx_data[9] else "N/A" # t.sessions

                status = self._get_membership_status(str(trx_data[6]) if trx_data[6] else None) # t.end_date is at index 6

                row = ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(trx_data[0]))),  # Trx ID (t.transaction_id)
                    ft.DataCell(ft.Text(str(trx_data[10]))), # Member Name (m.client_name)
                    ft.DataCell(ft.Text(str(trx_data[11]))), # Member Phone (m.phone)
                    ft.DataCell(ft.Text(transaction_type)),  # Type (t.transaction_type)
                    ft.DataCell(ft.Text(plan_details)),      # Plan/Details
                    ft.DataCell(ft.Text(str(trx_data[4]))),  # Paid Date (t.payment_date)
                    ft.DataCell(ft.Text(str(trx_data[5]))),  # Start Date (t.start_date)
                    ft.DataCell(ft.Text(str(trx_data[6]))),  # End Date (t.end_date)
                    ft.DataCell(ft.Text(f"{trx_data[7]:.2f}" if isinstance(trx_data[7], (int,float)) else str(trx_data[7]))), # Amount (t.amount_paid)
                    ft.DataCell(ft.Text(method_sessions)),   # Method/Sessions
                    ft.DataCell(ft.Text(status)),            # Membership Status
                ])
                self.full_history_table.rows.append(row)

        self.selected_transaction_id = None # Reset selection
        self.delete_transaction_button.disabled = True
        if self.full_history_table.page: self.full_history_table.update()
        if self.delete_transaction_button.page: self.delete_transaction_button.update()
        # self.update() # Main column update

    def apply_history_filters(self, e):
        name = self.history_name_filter_input.value if self.history_name_filter_input.value else None
        phone = self.history_phone_filter_input.value if self.history_phone_filter_input.value else None
        join_date_str = self._selected_join_date_filter.strftime('%Y-%m-%d') if self._selected_join_date_filter else None

        filtered_transactions = self.controller.get_filtered_transaction_history(name, phone, join_date_str)
        self.refresh_membership_history_display(filtered_transactions)

    def clear_history_filters(self, e):
        self.history_name_filter_input.value = ""
        self.history_phone_filter_input.value = ""
        self._selected_join_date_filter = None
        self.history_join_date_filter_text.value = "No date selected"

        if self.history_name_filter_input.page: self.history_name_filter_input.update()
        if self.history_phone_filter_input.page: self.history_phone_filter_input.update()
        if self.history_join_date_filter_text.page: self.history_join_date_filter_text.update()

        self.refresh_membership_history_display() # Refresh with all transactions

    def on_delete_selected_transaction_click(self, e):
        if self.selected_transaction_id is None:
            self.history_actions_feedback_text.value = "No transaction selected to delete."
            self.history_actions_feedback_text.color = ft.colors.ORANGE
            if self.history_actions_feedback_text.page: self.history_actions_feedback_text.update()
            return

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Delete Transaction"),
            content=ft.Text(f"Are you sure you want to delete transaction ID {self.selected_transaction_id}? This action cannot be undone."),
            actions=[
                ft.TextButton("Yes, Delete", on_click=lambda ev: self._perform_delete_transaction_action(True, self.selected_transaction_id)),
                ft.TextButton("No, Cancel", on_click=lambda ev: self._perform_delete_transaction_action(False, self.selected_transaction_id)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if self.page:
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()

    def _perform_delete_transaction_action(self, confirmed: bool, transaction_id: int):
        if self.page.dialog: # Ensure dialog exists
            self.page.dialog.open = False
            if self.page: self.page.update() # Update page to close dialog

        if confirmed:
            member_id_for_specific_history_refresh = self.controller.get_member_id_for_transaction(transaction_id)
            success, message = self.controller.delete_transaction_action(transaction_id)
            self.history_actions_feedback_text.value = message
            self.history_actions_feedback_text.color = ft.colors.GREEN if success else ft.colors.RED
            if success:
                self.refresh_membership_history_display() # Refresh full history
                # Call FletAppView to refresh member-specific history if it was affected
                if member_id_for_specific_history_refresh is not None and self.flet_app_view_ref:
                    self.flet_app_view_ref.refresh_member_specific_history_after_deletion(member_id_for_specific_history_refresh)
        else:
            self.history_actions_feedback_text.value = "Transaction deletion cancelled."
            self.history_actions_feedback_text.color = ft.colors.ORANGE

        if self.history_actions_feedback_text.page: self.history_actions_feedback_text.update()
        # self.update() # Main column update

    def is_isolated(self): # Added as methods call self.update() or update children
        return True
