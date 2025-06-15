from typing import Any, Dict, List, Optional

from reporter.database_manager import DatabaseManager


class AppAPI:
    """
    API layer for the Kranos MMA Reporter application.
    Acts as a bridge between the UI and Business Logic layers.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initializes the AppAPI with a DatabaseManager instance.

        Args:
            db_manager: An instance of the DatabaseManager.
        """
        self.db_manager: DatabaseManager = db_manager

    def create_membership_record(self, data: Dict[str, Any]) -> Optional[int]:
        """
        Creates a new membership record.

        Args:
            data: A dictionary containing the membership record data.

        Returns:
            The ID of the newly created record, or None if creation failed.
        """
        return self.db_manager.create_membership_record(data)

    def get_all_memberships_for_view(self) -> List[Dict[str, Any]]:
        """
        Retrieves all membership records for display.

        Returns:
            A list of dictionaries, each representing a membership record.
            Returns an empty list if no records are found or an error occurs.
        """
        records = self.db_manager.get_all_memberships_for_view()
        return records if records is not None else []

    def update_membership_record(self, record_id: int, data: Dict[str, Any]) -> bool:
        """
        Updates an existing membership record.

        Args:
            record_id: The ID of the record to update.
            data: A dictionary containing the updated data.

        Returns:
            True on success, False otherwise.
        """
        return self.db_manager.update_membership_record(record_id, data)

    def delete_membership_record(self, record_id: int) -> bool:
        """
        Deletes a membership record.

        Args:
            record_id: The ID of the record to delete.

        Returns:
            True if the deletion was successful, False otherwise.
        """
        return self.db_manager.delete_membership_record(record_id)

    def generate_financial_report_data(self) -> List[Dict[str, Any]]:
        """
        Generates data for the financial report.

        Returns:
            A list of dictionaries representing financial data. Returns an
            empty list if no data is available or an error occurs.
        """
        data = self.db_manager.generate_financial_report_data()
        return data if data is not None else []

    def generate_renewal_report_data(self) -> List[Dict[str, Any]]:
        """
        Generates data for the renewal report.

        Returns:
            A list of dictionaries representing renewal data. Returns an empty
            list if no data is available or an error occurs.
        """
        data = self.db_manager.generate_renewal_report_data()
        return data if data is not None else []

    def get_active_members(self) -> List[Dict[str, Any]]:
        """
        Retrieves all active members.

        Returns:
            A list of dictionaries, each representing an active member.
            Returns an empty list if no active members are found or an error
            occurs.
        """
        members = self.db_manager.get_active_members()
        return members if members is not None else []

    def get_active_plans(self) -> List[Dict[str, Any]]:
        """
        Retrieves all active membership plans.

        Returns:
            A list of dictionaries, each representing an active plan.
            Returns an empty list if no active plans are found or an error
            occurs.
        """
        plans = self.db_manager.get_active_plans()
        return plans if plans is not None else []
