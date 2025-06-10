import flet as ft
from ..gui import GuiController # Corrected import
from typing import Optional
import datetime
import calendar

class ReportingTab(ft.Column):  # Changed base class to ft.Column
    def __init__(self, controller: GuiController, file_picker_ref: ft.FilePicker, flet_app_view_ref):
        super().__init__()  # Call super().__init__ for ft.Column
        self.controller = controller
        self.file_picker_ref = file_picker_ref # Shared file picker
        self.flet_app_view_ref = flet_app_view_ref # To interact with FletAppView if needed

        # Internal state for finance report generation using FilePicker
        self._pending_finance_report_year: Optional[int] = None
        self._pending_finance_report_month: Optional[int] = None

        current_year = datetime.datetime.now().year
        month_options = [ft.dropdown.Option(str(i), calendar.month_name[i]) for i in range(1, 13)]

        # --- UI Control Declarations for Renewals Report ---
        self.renewal_report_year_input = ft.TextField(label="Year", value=str(current_year), width=150)
        self.renewal_report_month_dropdown = ft.Dropdown(label="Month", options=month_options, width=200)
        self.generate_renewals_report_button = ft.ElevatedButton(
            text="Generate Renewals Report & Display", on_click=self.on_generate_renewals_report_click
        )
        self.renewals_report_feedback_text = ft.Text("")
        self.pending_renewals_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Member Name")),
                ft.DataColumn(ft.Text("Phone")),
                ft.DataColumn(ft.Text("Membership Type")),
                ft.DataColumn(ft.Text("Plan Name")),
                ft.DataColumn(ft.Text("End Date")),
            ],
            rows=[],
            expand=True, # Make table take available space in its section
        )

        # --- UI Control Declarations for Finance Report ---
        self.finance_report_year_input = ft.TextField(label="Year", value=str(current_year), width=150)
        self.finance_report_month_dropdown = ft.Dropdown(label="Month", options=month_options, width=200)
        self.generate_finance_report_button = ft.ElevatedButton(
            text="Generate & Save Finance Report (.xlsx)", on_click=self.on_generate_finance_report_click
        )
        self.finance_report_feedback_text = ft.Text("")


        # --- Layout Definition (as self.controls for ft.Column) ---
        renewals_section = ft.Column(
            controls=[
                ft.Text("Upcoming Renewals Report", weight=ft.FontWeight.BOLD, size=18),
                ft.Row([self.renewal_report_year_input, self.renewal_report_month_dropdown, self.generate_renewals_report_button], alignment=ft.MainAxisAlignment.START),
                self.renewals_report_feedback_text,
                self.pending_renewals_table,
            ],
            spacing=10,
            # expand=1 # Let sections size based on content initially, or use expand factors
        )

        finance_section = ft.Column(
            controls=[
                ft.Text("Monthly Finance Report", weight=ft.FontWeight.BOLD, size=18),
                ft.Row([self.finance_report_year_input, self.finance_report_month_dropdown, self.generate_finance_report_button], alignment=ft.MainAxisAlignment.START),
                self.finance_report_feedback_text,
            ],
            spacing=10,
            # expand=1
        )

        self.controls = [
            ft.Text("Reporting Dashboard", weight=ft.FontWeight.BOLD, size=24, text_align=ft.TextAlign.CENTER),
            ft.Divider(height=20, color=ft.colors.BLUE_GREY_100),
            renewals_section,
            ft.Divider(height=20, color=ft.colors.BLUE_GREY_100),
            finance_section,
        ]
        # Properties for the main Column (self)
        self.expand = True
        self.scroll = ft.ScrollMode.ADAPTIVE
        self.spacing = 20
        self.padding = 15
        self.alignment = ft.MainAxisAlignment.START # Overall alignment

    def did_mount(self):
        # Load initial renewals report (e.g., for current month/year by default or last settings)
        # For now, let's not auto-load to save an action, user can click generate.
        # self._load_initial_renewals_data()
        if self.page:
            self.page.update()

    # --- Renewals Report Methods ---
    def on_generate_renewals_report_click(self, e):
        year_str = self.renewal_report_year_input.value
        month_str = self.renewal_report_month_dropdown.value

        if not year_str or not month_str:
            self.renewals_report_feedback_text.value = "Please select both year and month for renewals report."
            self.renewals_report_feedback_text.color = ft.colors.RED
            if self.renewals_report_feedback_text.page: self.renewals_report_feedback_text.update()
            return

        try:
            year = int(year_str)
            month = int(month_str)
        except ValueError:
            self.renewals_report_feedback_text.value = "Invalid year or month format."
            self.renewals_report_feedback_text.color = ft.colors.RED
            if self.renewals_report_feedback_text.page: self.renewals_report_feedback_text.update()
            return

        report_data = self.controller.generate_renewals_report_data(year, month)
        self.pending_renewals_table.rows.clear()
        if report_data:
            for row_data in report_data:
                self.pending_renewals_table.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(row_data[0]))), # Member Name
                    ft.DataCell(ft.Text(str(row_data[1]))), # Phone
                    ft.DataCell(ft.Text(str(row_data[2]))), # Membership Type
                    ft.DataCell(ft.Text(str(row_data[3]))), # Plan Name
                    ft.DataCell(ft.Text(str(row_data[4]))), # End Date
                ]))
            self.renewals_report_feedback_text.value = f"Renewals report for {calendar.month_name[month]} {year} generated."
            self.renewals_report_feedback_text.color = ft.colors.GREEN
        else:
            self.renewals_report_feedback_text.value = f"No upcoming renewals found for {calendar.month_name[month]} {year}."
            self.renewals_report_feedback_text.color = ft.colors.ORANGE

        if self.renewals_report_feedback_text.page: self.renewals_report_feedback_text.update()
        if self.pending_renewals_table.page: self.pending_renewals_table.update()
        # self.update()

    # --- Finance Report Methods ---
    def on_generate_finance_report_click(self, e):
        year_str = self.finance_report_year_input.value
        month_str = self.finance_report_month_dropdown.value

        if not year_str or not month_str:
            self.finance_report_feedback_text.value = "Please select both year and month for finance report."
            self.finance_report_feedback_text.color = ft.colors.RED
            if self.finance_report_feedback_text.page: self.finance_report_feedback_text.update()
            return

        try:
            self._pending_finance_report_year = int(year_str)
            self._pending_finance_report_month = int(month_str)
        except ValueError:
            self.finance_report_feedback_text.value = "Invalid year or month format."
            self.finance_report_feedback_text.color = ft.colors.RED
            if self.finance_report_feedback_text.page: self.finance_report_feedback_text.update()
            return

        # Use the shared file_picker_ref to save the file
        # The actual file generation and saving will be handled by FletAppView.on_file_picker_result
        # after the user selects a path.
        if self.file_picker_ref and self.page:
            default_filename = f"finance_report_{self._pending_finance_report_year}_{calendar.month_name[self._pending_finance_report_month]}.xlsx"
            self.file_picker_ref.save_file(
                dialog_title="Save Finance Report",
                file_name=default_filename,
                allowed_extensions=["xlsx"]
            )
            # self.page.add(self.file_picker_ref) # No, file_picker is on overlay
            # self.page.update() # Not needed here, Flet handles picker display
            self.finance_report_feedback_text.value = "Saving file... Please choose a location."
            self.finance_report_feedback_text.color = ft.colors.BLUE
        else:
            self.finance_report_feedback_text.value = "FilePicker not available."
            self.finance_report_feedback_text.color = ft.colors.RED

        if self.finance_report_feedback_text.page: self.finance_report_feedback_text.update()

    # This method will be called by FletAppView after file_picker result
    def process_finance_report_save(self, success: bool, message: str, path: Optional[str]):
        if success:
            self.finance_report_feedback_text.value = f"Finance report saved to {path}. Message: {message}"
            self.finance_report_feedback_text.color = ft.colors.GREEN
        else:
            self.finance_report_feedback_text.value = f"Failed to save finance report. Error: {message}"
            self.finance_report_feedback_text.color = ft.colors.RED

        # Clear pending state
        self._pending_finance_report_year = None
        self._pending_finance_report_month = None

        if self.finance_report_feedback_text.page: self.finance_report_feedback_text.update()
        # self.update()

    def is_isolated(self): # Added as methods call self.update() or update children
        return True
