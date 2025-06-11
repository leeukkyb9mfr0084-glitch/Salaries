import flet as ft
from ..gui import GuiController # Corrected import
from typing import Optional
import datetime
import calendar

class SettingsTab(ft.Column):  # Changed base class to ft.Column
    def __init__(self, controller: GuiController):
        super().__init__()  # Call super().__init__ for ft.Column
        self.controller = controller

        # --- UI Control Initializations ---
        self.book_status_display_label = ft.Text("")

        current_year_str = str(datetime.datetime.now().year)
        current_month_str = str(datetime.datetime.now().month)

        self.book_closing_year_input = ft.TextField(label="Year", value=current_year_str, width=150)
        self.book_closing_month_dropdown = ft.Dropdown(
            label="Month",
            options=[ft.dropdown.Option(str(i), calendar.month_name[i]) for i in range(1, 13)],
            value=current_month_str,
            width=200
        )
        self.check_book_status_button = ft.ElevatedButton(
            text="Check Book Status",
            on_click=self._handle_check_book_status_click
        )
        self.close_books_button = ft.ElevatedButton(
            text="Close Books for Period",
            on_click=self._handle_close_books_action_click
        )
        self.open_books_button = ft.ElevatedButton(
            text="Re-open Books for Period",
            on_click=self._handle_open_books_action_click
        )

        # --- Layout Definition (as self.controls for ft.Column) ---
        # Properties from the old build() method's root Column are applied to self
        self.controls = [
            ft.Text("Book Management", weight=ft.FontWeight.BOLD, size=20),
            ft.Row(
                controls=[
                    self.book_closing_year_input,
                    self.book_closing_month_dropdown,
                ],
                alignment=ft.MainAxisAlignment.START
            ),
            ft.Row(controls=[
                self.check_book_status_button,
                self.close_books_button,
                self.open_books_button,
            ], alignment=ft.MainAxisAlignment.START),
            self.book_status_display_label,
            ft.Divider(),
            ft.Container(content=ft.Text("Other Settings Placeholder"), padding=10, alignment=ft.alignment.center)
        ]
        self.spacing = 15
        self.expand = True
        # self.alignment = ft.MainAxisAlignment.START # Default for Column, if needed
        # self.horizontal_alignment = ft.CrossAxisAlignment.CENTER # If needed for items

    def did_mount(self):
        self._handle_check_book_status_click(None)
        if self.page: # Ensure page is available
            self.page.update()

    def _handle_check_book_status_click(self, e):
        if not self.book_closing_year_input.value or not self.book_closing_month_dropdown.value:
            self.book_status_display_label.value = "Error: Year and Month must be selected."
            self.book_status_display_label.color = ft.Colors.RED
            if self.page: self.book_status_display_label.update()
            return
        try:
            year_int = int(self.book_closing_year_input.value)
            month_int = int(self.book_closing_month_dropdown.value)
        except ValueError:
            self.book_status_display_label.value = "Error: Invalid year or month format."
            self.book_status_display_label.color = ft.Colors.RED
            if self.page: self.book_status_display_label.update()
            return

        status_message = self.controller.get_book_status_action(year_int, month_int)
        self.book_status_display_label.value = status_message

        if "OPEN" in status_message.upper():
            self.book_status_display_label.color = ft.Colors.GREEN
        elif "CLOSED" in status_message.upper():
            self.book_status_display_label.color = ft.Colors.ORANGE
        else:
            self.book_status_display_label.color = ft.Colors.BLUE
        if self.page: self.book_status_display_label.update()

    def _handle_close_books_action_click(self, e):
        if not self.book_closing_year_input.value or not self.book_closing_month_dropdown.value:
            self.book_status_display_label.value = "Error: Year and Month must be selected for closing."
            # ... (rest of the error handling as before)
            self.book_status_display_label.color = ft.Colors.RED
            if self.page: self.book_status_display_label.update()
            return
        try:
            year_int = int(self.book_closing_year_input.value)
            month_int = int(self.book_closing_month_dropdown.value)
            month_name = calendar.month_name[month_int]
            month_key = f"{year_int:04d}-{month_int:02d}"
        except (ValueError, IndexError): # Combined exception handling
            self.book_status_display_label.value = "Error: Invalid year or month."
            self.book_status_display_label.color = ft.Colors.RED
            if self.page: self.book_status_display_label.update()
            return

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Close Books"),
            content=ft.Text(f"Are you sure you want to close the books for {month_name} {year_int} ({month_key})? This will prevent further financial entries for this period."),
            actions=[
                ft.TextButton("Yes, Close Books", on_click=lambda ev: self._perform_close_books_action(True, year_int, month_int)),
                ft.TextButton("No, Cancel", on_click=lambda ev: self._perform_close_books_action(False, year_int, month_int)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if self.page: # Ensure page context
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()

    def _perform_close_books_action(self, confirmed: bool, year_int: int, month_int: int):
        if self.page.dialog:
            self.page.dialog.open = False
            # No need to self.page.update() here, dialog closing does it.

        if confirmed:
            success, message = self.controller.close_books_action(year_int, month_int)
            self.book_status_display_label.value = message
            self.book_status_display_label.color = ft.Colors.GREEN if success else ft.Colors.RED
            if success:
                self._handle_check_book_status_click(None) # Refresh status
        else:
            self.book_status_display_label.value = "Book closing cancelled by user."
            self.book_status_display_label.color = ft.Colors.ORANGE

        if self.page:
            self.book_status_display_label.update()
            # self.page.update() # Only update label, not whole page unless necessary

    def _handle_open_books_action_click(self, e):
        if not self.book_closing_year_input.value or not self.book_closing_month_dropdown.value:
            self.book_status_display_label.value = "Error: Year and Month must be selected for re-opening."
            # ... (rest of the error handling as before)
            self.book_status_display_label.color = ft.Colors.RED
            if self.page: self.book_status_display_label.update()
            return
        try:
            year_int = int(self.book_closing_year_input.value)
            month_int = int(self.book_closing_month_dropdown.value)
            month_name = calendar.month_name[month_int]
            month_key = f"{year_int:04d}-{month_int:02d}"
        except (ValueError, IndexError):
            self.book_status_display_label.value = "Error: Invalid year or month."
            self.book_status_display_label.color = ft.Colors.RED
            if self.page: self.book_status_display_label.update()
            return

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Re-open Books"),
            content=ft.Text(f"Are you sure you want to re-open the books for {month_name} {year_int} ({month_key})? This will allow modifications to financial entries for this period."),
            actions=[
                ft.TextButton("Yes, Re-open Books", on_click=lambda ev: self._perform_open_books_action(True, year_int, month_int)),
                ft.TextButton("No, Cancel", on_click=lambda ev: self._perform_open_books_action(False, year_int, month_int)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if self.page:
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()

    def _perform_open_books_action(self, confirmed: bool, year_int: int, month_int: int):
        if self.page.dialog:
            self.page.dialog.open = False

        if confirmed:
            success, message = self.controller.open_books_action(year_int, month_int)
            self.book_status_display_label.value = message
            self.book_status_display_label.color = ft.Colors.GREEN if success else ft.Colors.RED
            if success:
                self._handle_check_book_status_click(None) # Refresh status
        else:
            self.book_status_display_label.value = "Book re-opening cancelled by user."
            self.book_status_display_label.color = ft.Colors.ORANGE

        if self.page:
            self.book_status_display_label.update()
            # self.page.update()

    def is_isolated(self): # Added as methods update child controls and page dialogs
        return True
