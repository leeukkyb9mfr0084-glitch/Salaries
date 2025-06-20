import logging
import sqlite3
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .models import (  # Assuming Member dataclass exists
    GroupClassMembership,
    GroupClassMembershipView,
    GroupPlan,
    GroupPlanView,
    Member,
    MemberView,
    PTMembership,
    PTMembershipView,
)

# Basic logging configuration (can be overridden by application's config)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# This constant can remain as per original file analysis
DB_FILE = "reporter/data/kranos_data.db"


class DatabaseManager:
    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
        self.conn.row_factory = sqlite3.Row

    def add_member(self, member: Member) -> Optional[Member]:
        """Adds a new member to the database.
        Sets join_date to current date and is_active to True by default if not provided.
        Raises ValueError if phone number already exists.
        Returns the member object with id, or None if an error occurs.
        """
        cursor = self.conn.cursor()
        try:
            # Check for phone uniqueness
            cursor.execute("SELECT id FROM members WHERE phone = ?", (member.phone,))
            if cursor.fetchone():
                logging.warning(
                    f"Attempt to add member with existing phone number: {member.phone}"
                )
                raise ValueError(f"Phone number {member.phone} already exists.")

            join_date_to_use = (
                member.join_date if member.join_date else date.today().isoformat()
            )
            # Ensure is_active is 1 or 0 for SQLite
            is_active_int = 1 if member.is_active else 0

            cursor.execute(
                "INSERT INTO members (name, phone, email, join_date, is_active) VALUES (?, ?, ?, ?, ?)",
                (
                    member.name,
                    member.phone,
                    member.email,
                    join_date_to_use,
                    is_active_int,
                ),
            )
            self.conn.commit()
            member.id = cursor.lastrowid
            logging.info(f"Member '{member.name}' added with ID {member.id}.")
            return member
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(
                f"Database error in add_member for '{member.name}': {e}", exc_info=True
            )
            return None
        except ValueError:  # Re-raise ValueError for phone uniqueness
            raise

    def update_member(self, member: Member) -> bool:
        """Updates an existing member's details.
        If phone is provided, checks for uniqueness unless it's the member's current phone.
        Returns True if update was successful, False otherwise.
        """
        cursor = self.conn.cursor()
        fields_to_update = []
        params = []

        # We need to fetch the original member data to compare phone numbers
        cursor.execute("SELECT phone FROM members WHERE id = ?", (member.id,))
        current_member_data = cursor.fetchone()

        if not current_member_data:
            logging.warning(f"Member with ID {member.id} not found for update.")
            return False
        current_phone = current_member_data["phone"]

        if member.name is not None:
            fields_to_update.append("name = ?")
            params.append(member.name)
        if member.email is not None:
            fields_to_update.append("email = ?")
            params.append(member.email)
        if member.is_active is not None:
            fields_to_update.append("is_active = ?")
            params.append(1 if member.is_active else 0)

        try:
            if member.phone is not None and member.phone != current_phone:
                # If phone is different, check for uniqueness among other members
                cursor.execute(
                    "SELECT id FROM members WHERE phone = ? AND id != ?",
                    (member.phone, member.id),
                )
                if cursor.fetchone():
                    logging.warning(
                        f"Attempt to update member {member.id} with existing phone number: {member.phone}"
                    )
                    raise ValueError(
                        f"Phone number {member.phone} already exists for another member."
                    )
                fields_to_update.append("phone = ?")
                params.append(member.phone)
            elif (
                member.phone is not None
            ):  # phone is same as current, still add to update if it was provided
                fields_to_update.append("phone = ?")
                params.append(member.phone)

            if not fields_to_update:
                logging.info(f"No fields provided to update for member ID {member.id}.")
                return True

            sql_update = (
                f"UPDATE members SET {', '.join(fields_to_update)} WHERE id = ?"
            )
            params.append(member.id)

            cursor.execute(sql_update, tuple(params))
            self.conn.commit()

            if cursor.rowcount == 0:
                # This means either member not found or data was the same.
                # We've already checked if member exists.
                logging.info(
                    f"Member ID {member.id} data was the same, no update performed."
                )
                return True  # Data was the same

            logging.info(f"Member ID {member.id} updated successfully.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(
                f"Database error in update_member for ID {member.id}: {e}",
                exc_info=True,
            )
            return False
        except ValueError:  # Re-raise ValueError for phone uniqueness
            raise

    def get_all_members(self) -> List[Member]:
        """Retrieves all members from the database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, name, phone, email, join_date, is_active FROM members ORDER BY name ASC"
            )
            rows = cursor.fetchall()
            return [Member(**row) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"Database error in get_all_members: {e}", exc_info=True)
            return []

    def delete_member(self, member_id: int) -> bool:
        """Deletes a member from the database by their ID.
        Returns True if deletion was successful, False otherwise.
        """
        cursor = self.conn.cursor()
        try:
            # Future consideration: Check for related records (e.g., active memberships)
            # and decide on deletion policy (cascade, prevent, set null).
            # For now, direct delete.
            cursor.execute("DELETE FROM members WHERE id = ?", (member_id,))
            self.conn.commit()
            if cursor.rowcount == 0:
                logging.warning(f"No member found with ID {member_id} to delete.")
                return False
            logging.info(f"Member ID {member_id} deleted successfully.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(
                f"Database error in delete_member for ID {member_id}: {e}",
                exc_info=True,
            )
            return False

    def add_group_plan(self, group_plan: GroupPlan) -> Optional[GroupPlan]:
        """Adds a new group_plan to the database.
        Generates display_name from name and duration_days if not provided.
        Sets is_active to True by default.
        Raises ValueError if display_name already exists.
        Returns the group_plan object with id, or None if an error occurs.
        """
        cursor = self.conn.cursor()
        display_name = (
            group_plan.display_name
            if group_plan.display_name
            else f"{group_plan.name} - {group_plan.duration_days} days"
        )
        is_active_int = 1 if group_plan.is_active else 0

        try:
            # Check for display_name uniqueness
            cursor.execute(
                "SELECT id FROM group_plans WHERE display_name = ?", (display_name,)
            )
            if cursor.fetchone():
                logging.warning(
                    f"Attempt to add group_plan with existing display_name: {display_name}"
                )
                raise ValueError(f"Display name '{display_name}' already exists.")

            cursor.execute(
                "INSERT INTO group_plans (name, duration_days, default_amount, display_name, is_active) VALUES (?, ?, ?, ?, ?)",
                (
                    group_plan.name,
                    group_plan.duration_days,
                    group_plan.default_amount,
                    display_name,
                    is_active_int,
                ),
            )
            self.conn.commit()
            group_plan.id = cursor.lastrowid
            group_plan.display_name = (
                display_name  # Ensure display_name is set on the object
            )
            logging.info(
                f"Group Plan '{group_plan.name}' added with ID {group_plan.id}, display_name '{display_name}'."
            )
            return group_plan
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(
                f"Database error in add_group_plan for '{group_plan.name}': {e}",
                exc_info=True,
            )
            return None
        except ValueError:  # Re-raise ValueError for display_name uniqueness
            raise

    def update_group_plan(self, group_plan: GroupPlan) -> bool:
        """Updates an existing group_plan's details.
        If name or duration_days are changed, display_name is regenerated and its uniqueness checked.
        Returns True if update was successful, False otherwise.
        """
        cursor = self.conn.cursor()
        fields_to_update = []
        params_for_update = []

        # Fetch current group_plan details first to determine if display_name needs update and for current values
        try:
            cursor.execute(
                "SELECT name, duration_days, display_name FROM group_plans WHERE id = ?",
                (group_plan.id,),
            )
            current_plan_row = cursor.fetchone()
            if not current_plan_row:
                logging.warning(
                    f"Group Plan with ID {group_plan.id} not found for update."
                )
                return False
            current_name, current_duration_days, current_display_name = (
                current_plan_row["name"],
                current_plan_row["duration_days"],
                current_plan_row["display_name"],
            )

            new_name = group_plan.name if group_plan.name is not None else current_name
            new_duration_days = (
                group_plan.duration_days
                if group_plan.duration_days is not None
                else current_duration_days
            )
            new_display_name = group_plan.display_name

            display_name_changed = False
            if group_plan.name is not None and group_plan.name != current_name:
                fields_to_update.append("name = ?")
                params_for_update.append(group_plan.name)
                display_name_changed = True
            elif (
                group_plan.name is not None
            ):  # Name is same as current, still add to update if it was provided
                fields_to_update.append("name = ?")
                params_for_update.append(group_plan.name)

            if (
                group_plan.duration_days is not None
                and group_plan.duration_days != current_duration_days
            ):
                fields_to_update.append("duration_days = ?")
                params_for_update.append(group_plan.duration_days)
                display_name_changed = True
            elif (
                group_plan.duration_days is not None
            ):  # Duration is same as current, still add to update if it was provided
                fields_to_update.append("duration_days = ?")
                params_for_update.append(group_plan.duration_days)

            if display_name_changed:
                # Regenerate display_name if name or duration_days changed
                new_display_name = f"{new_name} - {new_duration_days} days"
                if new_display_name != current_display_name:
                    # Check for uniqueness only if the new display_name is actually different
                    cursor.execute(
                        "SELECT id FROM group_plans WHERE display_name = ? AND id != ?",
                        (new_display_name, group_plan.id),
                    )
                    if cursor.fetchone():
                        logging.warning(
                            f"Attempt to update group_plan {group_plan.id} with existing display_name: {new_display_name}"
                        )
                        raise ValueError(
                            f"Display name '{new_display_name}' already exists for another group_plan."
                        )
                fields_to_update.append("display_name = ?")
                params_for_update.append(new_display_name)
                group_plan.display_name = (
                    new_display_name  # Update the object's display_name
                )
            elif (
                group_plan.display_name is not None
                and group_plan.display_name != current_display_name
            ):
                # This case handles if only display_name is provided and different
                cursor.execute(
                    "SELECT id FROM group_plans WHERE display_name = ? AND id != ?",
                    (group_plan.display_name, group_plan.id),
                )
                if cursor.fetchone():
                    logging.warning(
                        f"Attempt to update group_plan {group_plan.id} with existing display_name: {group_plan.display_name}"
                    )
                    raise ValueError(
                        f"Display name '{group_plan.display_name}' already exists for another group_plan."
                    )
                fields_to_update.append("display_name = ?")
                params_for_update.append(group_plan.display_name)

            if group_plan.default_amount is not None:
                fields_to_update.append("default_amount = ?")
                params_for_update.append(group_plan.default_amount)

            if group_plan.is_active is not None:
                fields_to_update.append("is_active = ?")
                params_for_update.append(1 if group_plan.is_active else 0)

            if not fields_to_update:
                logging.info(
                    f"No fields provided to update for group_plan ID {group_plan.id}."
                )
                return True

            sql_update_stmt = (
                f"UPDATE group_plans SET {', '.join(fields_to_update)} WHERE id = ?"
            )
            params_for_update.append(group_plan.id)

            cursor.execute(sql_update_stmt, tuple(params_for_update))
            self.conn.commit()

            if cursor.rowcount == 0:
                logging.info(
                    f"Group Plan ID {group_plan.id} data was the same, no update performed."
                )
                return True

            logging.info(
                f"Group Plan ID {group_plan.id} updated successfully. New display_name: '{group_plan.display_name}'."
            )
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(
                f"Database error in update_group_plan for ID {group_plan.id}: {e}",
                exc_info=True,
            )
            return False
        except ValueError:  # Re-raise ValueError for display_name uniqueness
            raise

    def get_all_group_plans(self) -> List[GroupPlan]:
        """Retrieves all group_plans from the database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, name, duration_days, default_amount, display_name, is_active FROM group_plans ORDER BY name ASC"
            )
            rows = cursor.fetchall()
            return [GroupPlan(**row) for row in rows]
        except sqlite3.Error as e:
            logging.error(f"Database error in get_all_group_plans: {e}", exc_info=True)
            return []

    def delete_group_plan(self, plan_id: int) -> bool:
        """Deletes a group_plan from the database by its ID.
        Returns True if deletion was successful, False otherwise.
        """
        cursor = self.conn.cursor()
        try:
            # Future consideration: Check for related memberships.
            # For now, direct delete.
            cursor.execute("DELETE FROM group_plans WHERE id = ?", (plan_id,))
            self.conn.commit()
            if cursor.rowcount == 0:
                logging.warning(f"No group_plan found with ID {plan_id} to delete.")
                return False
            logging.info(f"Group Plan ID {plan_id} deleted successfully.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(
                f"Database error in delete_group_plan for ID {plan_id}: {e}",
                exc_info=True,
            )
            return False

    def get_group_plan_by_display_name(self, display_name: str) -> Optional[GroupPlan]:
        """Retrieves a specific group_plan by its display_name."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT id, name, duration_days, default_amount, display_name, is_active FROM group_plans WHERE display_name = ?",
                (display_name,),
            )
            plan_row = cursor.fetchone()
            if plan_row:
                return GroupPlan(**plan_row)
            return None
        except sqlite3.Error as e:
            logging.error(
                f"Database error in get_group_plan_by_display_name for '{display_name}': {e}",
                exc_info=True,
            )
            return None

    def get_group_plan_by_id(self, plan_id: int) -> Optional[GroupPlan]:
        """Retrieves details for a specific group_plan by its ID."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT id, name, duration_days, default_amount, display_name, is_active FROM group_plans WHERE id = ?",
                (plan_id,),
            )
            plan_row = cursor.fetchone()
            if plan_row:
                return GroupPlan(**plan_row)
            return None
        except sqlite3.Error as e:
            logging.error(
                f"Database error in get_group_plan_by_id for plan_id {plan_id}: {e}",
                exc_info=True,
            )
            return None

    def find_or_create_group_plan(self, name: str, duration_days: int, price: float) -> Optional[int]:
        """
        Finds a group plan by name, duration, and price. If not found, creates a new one.
        Returns the plan ID.
        """
        cursor = self.conn.cursor()
        try:
            # Attempt to find an existing plan with the same name, duration, and price.
            # Note: display_name is usually name + duration, but price is also a key factor here.
            # The group_plans table has `default_amount` for price.
            cursor.execute(
                "SELECT id FROM group_plans WHERE name = ? AND duration_days = ? AND default_amount = ?",
                (name, duration_days, price),
            )
            row = cursor.fetchone()
            if row:
                logging.info(f"Found existing group plan ID {row['id']} for {name}, {duration_days} days, price {price}.")
                return row["id"]
            else:
                # Plan not found, create a new one
                logging.info(f"No existing plan found for {name}, {duration_days} days, price {price}. Creating new one.")
                # Create a GroupPlan object to pass to add_group_plan
                # is_active defaults to True, display_name will be auto-generated by add_group_plan
                new_plan = GroupPlan(
                    id=None, # Will be set by add_group_plan
                    name=name,
                    duration_days=duration_days,
                    default_amount=price,
                    is_active=True # New plans from migration are active
                )
                added_plan_obj = self.add_group_plan(new_plan)
                if added_plan_obj and added_plan_obj.id is not None:
                    logging.info(f"Created new group plan ID {added_plan_obj.id}.")
                    return added_plan_obj.id
                else:
                    logging.error(f"Failed to create new group plan for {name}, {duration_days} days, price {price}.")
                    return None
        except sqlite3.Error as e:
            logging.error(f"Database error in find_or_create_group_plan for '{name}': {e}", exc_info=True)
            return None
        except ValueError as ve: # Catch ValueError from add_group_plan (e.g. duplicate display_name if logic changes)
            logging.error(f"ValueError in find_or_create_group_plan for '{name}': {ve}", exc_info=True)
            return None


    def add_group_class_membership(
        self, membership: GroupClassMembership
    ) -> Optional[GroupClassMembership]:
        """Creates a new group_class_membership record.
        Sets purchase_date to current timestamp if not provided.
        Raises ValueError if start_date or end_date is invalid.
        Returns the membership object with id, or None if an error occurs.
        """
        cursor = self.conn.cursor()
        try:  # Main try block for all operations
            # Date validation
            try:
                datetime.strptime(membership.start_date, "%Y-%m-%d")
                datetime.strptime(membership.end_date, "%Y-%m-%d")
            except ValueError as ve:  # Handles date validation error specifically
                logging.error(f"Invalid date format: {ve}")
                # Re-raise as a new ValueError with a more specific message to the caller
                raise ValueError(
                    f"Invalid date format for start_date or end_date. Expected YYYY-MM-DD."
                )

            purchase_date_to_use = (
                membership.purchase_date
                if membership.purchase_date
                else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            is_active_int = 1 if membership.is_active else 0

            # Note: payment_method and notes are part of the dataclass but not the DB table.
            # They will not be inserted. Logging them if present.

            sql_insert = """
            INSERT INTO group_class_memberships (
                member_id, plan_id, start_date, end_date, amount_paid,
                purchase_date, membership_type, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(
                sql_insert,
                (
                    membership.member_id,
                    membership.plan_id,
                    membership.start_date,
                    membership.end_date,
                    membership.amount_paid,
                    purchase_date_to_use,
                    membership.membership_type,
                    is_active_int,
                ),
            )
            self.conn.commit()
            membership.id = cursor.lastrowid
            membership.purchase_date = (
                purchase_date_to_use  # Ensure purchase_date is set on the object
            )

            log_message = (
                f"Group Class Membership record created for member ID {membership.member_id}, "
                f"plan ID {membership.plan_id} with membership ID {membership.id}."
            )
            if membership.payment_method:
                log_message += (
                    f" Payment Method (not stored): {membership.payment_method}."
                )
            if membership.notes:
                log_message += f" Notes (not stored): {membership.notes}."
            logging.info(log_message)

            return membership

        except sqlite3.IntegrityError as ie:  # Aligned with the main try
            self.conn.rollback()
            logging.error(
                f"DB integrity error creating group_class_membership for member {membership.member_id}, plan {membership.plan_id}: {ie}",
                exc_info=True,
            )
            raise  # Re-raise the IntegrityError to signal failure to caller
        except sqlite3.Error as e:  # Aligned with the main try
            self.conn.rollback()
            logging.error(
                f"DB error (type: {type(e)}) creating group_class_membership for member {membership.member_id}, plan {membership.plan_id}: {e}",
                exc_info=True,
            )
            return None  # Or raise an AppAPI specific exception
        except (
            ValueError
        ) as ve:  # Catches the re-raised ValueError from date validation or any other new ValueError
            # No rollback needed here if it's from date validation as it happens before DB ops.
            # Logging is already done for date validation error.
            raise  # Re-raise to the caller

    def get_all_group_class_memberships(
        self,
        # name_filter: Optional[str] = None, # Filtering by name requires a JOIN with members table
        status_filter: Optional[str] = None,  # 'Active', 'Inactive', or None
    ) -> List[GroupClassMembership]:
        try:
            cursor = self.conn.cursor()
            # Removed JOINs with members and group_plans, and related fields (member_name, plan_name)
            # If these are needed, consider creating a specific View model or adding optional fields to GroupClassMembership
            sql_select = """
            SELECT
                gcm.id,
                gcm.member_id,
                gcm.plan_id,
                gcm.start_date,
                gcm.end_date,
                gcm.is_active,
                gcm.amount_paid,
                gcm.purchase_date,
                gcm.membership_type
            FROM group_class_memberships gcm
            """
            conditions = []
            params = []

            # if name_filter: # Requires JOIN with members
            #     conditions.append("m.name LIKE ?") # This would need 'm' alias from JOIN
            #     params.append(f"%{name_filter}%")
            if status_filter:
                is_active_val = 1 if status_filter.lower() == "active" else 0
                conditions.append("gcm.is_active = ?")
                params.append(is_active_val)

            if conditions:
                sql_select += " WHERE " + " AND ".join(conditions)

            # sql_select += " ORDER BY gcm.start_date DESC, m.name ASC" # Ordering by m.name requires JOIN
            sql_select += " ORDER BY gcm.start_date DESC"

            cursor.execute(sql_select, params)
            rows = cursor.fetchall()
            # Assuming GroupClassMembership dataclass matches these fields
            return [GroupClassMembership(**row) for row in rows]
        except sqlite3.Error as e:
            logging.error(
                f"Database error while fetching group_class_memberships: {e}",
                exc_info=True,
            )
            return []

    def get_group_class_memberships_by_member_id(
        self, member_id: int
    ) -> List[GroupClassMembership]:
        """Retrieves all group class memberships for a specific member."""
        try:
            cursor = self.conn.cursor()
            # Removed JOINs and member_name, plan_name for consistency with GroupClassMembership dataclass
            sql_select = """
            SELECT
                gcm.id,
                gcm.member_id,
                gcm.plan_id,
                gcm.start_date,
                gcm.end_date,
                gcm.purchase_date,
                gcm.membership_type,
                gcm.is_active,
                gcm.amount_paid
            FROM group_class_memberships gcm
            WHERE gcm.member_id = ?
            ORDER BY gcm.start_date DESC;
            """
            cursor.execute(sql_select, (member_id,))
            rows = cursor.fetchall()
            return [GroupClassMembership(**row) for row in rows]
        except sqlite3.Error as e:
            logging.error(
                f"Database error in get_group_class_memberships_by_member_id for member_id {member_id}: {e}",
                exc_info=True,
            )
            return []

    def update_group_class_membership(self, membership: GroupClassMembership) -> bool:
        cursor = self.conn.cursor()
        try:  # Main try block
            # Date validation
            try:
                datetime.strptime(membership.start_date, "%Y-%m-%d")
                datetime.strptime(membership.end_date, "%Y-%m-%d")
            except ValueError as ve:  # Specific to date validation
                logging.error(
                    f"Invalid date format for membership ID {membership.id}: {ve}"
                )
                raise ValueError(
                    f"Invalid date format for start_date or end_date. Expected YYYY-MM-DD."
                )

            # purchase_date and membership_type are part of the dataclass but might not always be intended for update here.
            # Current DB schema for group_class_memberships includes:
            # member_id, plan_id, start_date, end_date, amount_paid, purchase_date, membership_type, is_active
            # We will update all fields from the membership object except id.
            # is_active is also updated.
            sql_update = """
            UPDATE group_class_memberships
            SET
                member_id = ?,
                plan_id = ?,
                start_date = ?,
                end_date = ?,
                amount_paid = ?,
                purchase_date = ?,
                membership_type = ?,
                is_active = ?
            WHERE id = ?
            """
            is_active_int = 1 if membership.is_active else 0
            cursor.execute(
                sql_update,
                (
                    membership.member_id,
                    membership.plan_id,
                    membership.start_date,
                    membership.end_date,
                    membership.amount_paid,
                    membership.purchase_date,  # Assuming purchase_date can be updated
                    membership.membership_type,  # Assuming membership_type can be updated
                    is_active_int,
                    membership.id,
                ),
            )
            self.conn.commit()

            if cursor.rowcount == 0:
                logging.warning(
                    f"No group_class_membership record found with id {membership.id} to update, or data was the same."
                )
                # Check if the record actually exists to differentiate
                cursor.execute(
                    "SELECT id FROM group_class_memberships WHERE id = ?",
                    (membership.id,),
                )
                if not cursor.fetchone():
                    return False  # Record not found
                return True  # Data was the same

            logging.info(
                f"Group Class Membership record {membership.id} updated successfully."
            )
            return True

        except sqlite3.Error as e:  # For DB errors
            self.conn.rollback()
            logging.error(
                f"Database error while updating group_class_membership {membership.id}: {e}",
                exc_info=True,
            )
            return False
        except (
            ValueError
        ) as ve:  # For date validation errors (re-raised) or other ValueErrors
            # If this ValueError is from our date validation, logging is already done.
            # If other ValueErrors could occur after DB ops, consider rollback.
            # For now, assume ValueErrors are pre-commit.
            if "Invalid date format" not in str(ve):
                logging.error(
                    f"Value error during update for membership ID {membership.id}: {ve}",
                    exc_info=True,
                )
            # If rollback is desired for all ValueErrors: self.conn.rollback()
            raise  # Re-raise to signal invalid input or issue to caller

    def delete_group_class_membership(self, membership_id: int) -> bool:
        try:
            cursor = self.conn.cursor()
            sql_delete = "DELETE FROM group_class_memberships WHERE id = ?"
            cursor.execute(sql_delete, (membership_id,))
            self.conn.commit()

            if cursor.rowcount == 0:
                logging.warning(
                    f"No group_class_membership record found with id {membership_id} to delete."
                )
                return False  # No record found

            logging.info(
                f"Group Class Membership record {membership_id} deleted successfully."
            )
            return True

        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(
                f"Database error while deleting group_class_membership {membership_id}: {e}",
                exc_info=True,
            )
            return False

    # Personal Training (PT) Membership CRUD operations
    def add_pt_membership(self, pt_membership: PTMembership) -> Optional[PTMembership]:
        """Adds a new PT membership record.
        Sessions_remaining is set to sessions_total if not explicitly set otherwise (though typically they'd be same on creation).
        Returns the pt_membership object with id, or None if an error occurs.
        """
        cursor = self.conn.cursor()
        try:
            # Ensure sessions_remaining is set, defaulting to sessions_total if it's None or not set.
            # The dataclass definition makes sessions_remaining non-optional, so it should always be present.
            # If it could be optional on the input object, we might do:
            # sessions_remaining_to_insert = pt_membership.sessions_remaining if pt_membership.sessions_remaining is not None else pt_membership.sessions_total
            sessions_remaining_to_insert = pt_membership.sessions_remaining

            sql_insert = """
            INSERT INTO pt_memberships (member_id, purchase_date, amount_paid, sessions_total, sessions_remaining)
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(
                sql_insert,
                (
                    pt_membership.member_id,
                    pt_membership.purchase_date,
                    pt_membership.amount_paid,
                    pt_membership.sessions_total,
                    sessions_remaining_to_insert,
                ),
            )
            self.conn.commit()
            pt_membership.id = cursor.lastrowid
            logging.info(
                f"PT Membership record created for member ID {pt_membership.member_id} with ID {pt_membership.id}."
            )
            return pt_membership
        except sqlite3.IntegrityError as ie:
            self.conn.rollback()
            logging.error(
                f"DB integrity error creating PT membership for member {pt_membership.member_id}: {ie}",
                exc_info=True,
            )
            raise  # Re-raise the IntegrityError
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(
                f"DB error creating PT membership for member {pt_membership.member_id}: {e}",
                exc_info=True,
            )
            return None

    def get_all_pt_memberships(self) -> List[PTMembership]:
        """Retrieves all PT memberships from the database."""
        try:
            cursor = self.conn.cursor()
            # Removed JOIN with members and member_name field.
            # Renamed pt.id to id to match PTMembership dataclass.
            sql_select = """
            SELECT
                pt.id,
                pt.member_id,
                pt.purchase_date,
                pt.sessions_total,
                pt.sessions_remaining,
                pt.amount_paid
            FROM pt_memberships pt
            ORDER BY pt.purchase_date DESC, pt.id DESC
            """
            cursor.execute(sql_select)
            rows = cursor.fetchall()
            # Map rows to PTMembership objects
            return [PTMembership(**row) for row in rows]
        except sqlite3.Error as e:
            logging.error(
                f"Database error in get_all_pt_memberships: {e}", exc_info=True
            )
            return []

    def delete_pt_membership(self, membership_id: int) -> bool:
        """Deletes a PT membership by its ID.
        Returns True if deletion was successful, False otherwise.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("DELETE FROM pt_memberships WHERE id = ?", (membership_id,))
            self.conn.commit()
            if cursor.rowcount == 0:
                logging.warning(
                    f"No PT membership found with ID {membership_id} to delete."
                )
                return False
            logging.info(f"PT Membership ID {membership_id} deleted successfully.")
            return True
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(
                f"Database error deleting PT membership ID {membership_id}: {e}",
                exc_info=True,
            )
            return False

    def update_pt_membership(self, pt_membership: PTMembership) -> bool:
        """Updates an existing PT membership's details.
        All fields from the pt_membership object are used in the update.
        Returns True if update was successful, False otherwise.
        """
        cursor = self.conn.cursor()

        try:  # Main try block for all operations
            # Check if the PT membership exists
            cursor.execute(
                "SELECT id FROM pt_memberships WHERE id = ?", (pt_membership.id,)
            )
            if not cursor.fetchone():
                logging.warning(
                    f"PT Membership with ID {pt_membership.id} not found for update."
                )
                return False  # Return False if not found, before other ops

            # Date validation for purchase_date
            try:
                datetime.strptime(pt_membership.purchase_date, "%Y-%m-%d")
            except ValueError:  # Handles date validation error specifically
                logging.error(
                    f"Invalid purchase_date format: {pt_membership.purchase_date}. Expected YYYY-MM-DD."
                )
                raise ValueError(
                    f"Invalid purchase_date format: {pt_membership.purchase_date}. Expected YYYY-MM-DD."
                )

            if pt_membership.amount_paid < 0:
                logging.error(
                    f"Invalid amount_paid: {pt_membership.amount_paid}. Cannot be negative."
                )
                raise ValueError(
                    f"Invalid amount_paid: {pt_membership.amount_paid}. Cannot be negative."
                )

            if pt_membership.sessions_total < 0:
                logging.error(
                    f"Invalid sessions_total: {pt_membership.sessions_total}. Cannot be negative."
                )
                raise ValueError(
                    f"Invalid sessions_total: {pt_membership.sessions_total}. Cannot be negative."
                )

            if pt_membership.sessions_remaining < 0:
                logging.error(
                    f"Invalid sessions_remaining: {pt_membership.sessions_remaining}. Cannot be negative."
                )
                raise ValueError(
                    f"Invalid sessions_remaining: {pt_membership.sessions_remaining}. Cannot be negative."
                )

            sql_update_stmt = """
            UPDATE pt_memberships
            SET purchase_date = ?, amount_paid = ?, sessions_total = ?, sessions_remaining = ?
            WHERE id = ?
            """
            params = (
                pt_membership.purchase_date,
                pt_membership.amount_paid,
                pt_membership.sessions_total,
                pt_membership.sessions_remaining,
                pt_membership.id,
            )

            cursor.execute(sql_update_stmt, params)
            self.conn.commit()

            if cursor.rowcount == 0:
                logging.info(
                    f"PT Membership ID {pt_membership.id} data was the same, no update performed."
                )
            else:
                logging.info(
                    f"PT Membership ID {pt_membership.id} updated successfully."
                )
            return True

        except sqlite3.Error as e:  # For DB errors
            self.conn.rollback()
            logging.error(
                f"Database error in update_pt_membership for ID {pt_membership.id}: {e}",
                exc_info=True,
            )
            return False
        except (
            ValueError
        ) as ve:  # For validation errors (re-raised from date or new ones)
            # Logging already done for specific validation error.
            # No rollback needed if error is before DB ops that change data.
            # If ValueErrors could occur after commit, a rollback might be needed,
            # but current ValueErrors are pre-DB-commit.
            return (
                False  # Or re-raise ve if API contract prefers exceptions for bad input
            )

    def generate_financial_report_data(
        self, start_date: str, end_date: str
    ) -> List[Dict]:
        """
        Fetches raw transaction data from both group_class_memberships and pt_memberships
        within the given date range.
        Returns a list of dictionaries, where each dictionary represents a raw transaction.
        """
        transactions = []
        cursor = self.conn.cursor()

        try:
            # Query for group class memberships
            sql_group_details = """
            SELECT
                gcm.purchase_date,
                gcm.amount_paid,
                'group' as type,
                m.name as member_name,
                gp.name as plan_name,
                gcm.member_id,
                gcm.plan_id
            FROM group_class_memberships gcm
            JOIN members m ON gcm.member_id = m.id
            JOIN group_plans gp ON gcm.plan_id = gp.id
            WHERE date(gcm.purchase_date) BETWEEN date(?) AND date(?)
            """
            cursor.execute(sql_group_details, (start_date, end_date))
            column_names_group = [description[0] for description in cursor.description]
            for row in cursor.fetchall():
                transactions.append(dict(zip(column_names_group, row)))

            # Query for PT memberships
            sql_pt_details = """
            SELECT
                ptm.purchase_date,
                ptm.amount_paid,
                'pt' as type,
                m.name as member_name,
                ptm.sessions_total,
                ptm.member_id
            FROM pt_memberships ptm
            JOIN members m ON ptm.member_id = m.id
            WHERE date(ptm.purchase_date) BETWEEN date(?) AND date(?)
            """
            cursor.execute(sql_pt_details, (start_date, end_date))
            column_names_pt = [description[0] for description in cursor.description]
            for row in cursor.fetchall():
                transactions.append(dict(zip(column_names_pt, row)))

            # Sort all transactions by purchase_date
            transactions.sort(key=lambda x: x["purchase_date"])

            return transactions

        except sqlite3.Error as e:
            logging.error(
                f"Database error while generating financial report data for {start_date} to {end_date}: {e}",
                exc_info=True,
            )
            return []
        except Exception as ex:
            logging.error(
                f"Unexpected error while generating financial report data: {ex}",
                exc_info=True,
            )
            return []

    def generate_renewal_report_data(
        self, start_date_str: str, end_date_str: str
    ) -> list:
        try:
            cursor = self.conn.cursor()
            # Removed internal date calculations

            # Query for renewal data
            # Joins with members and group_plans to get names.
            # Filters for group_class_memberships ending in the next 30 days.
            # The check for gcm.is_active = 1 is replaced by date comparison.
            # PT memberships are not included here as they are session-based.
            sql_select_renewals = """
            SELECT
                m.name AS member_name,
                m.phone AS member_phone,
                gp.name AS plan_name,
                gcm.start_date,
                gcm.end_date,
                gcm.amount_paid,
                gcm.membership_type
            FROM group_class_memberships gcm
            JOIN members m ON gcm.member_id = m.id
            JOIN group_plans gp ON gcm.plan_id = gp.id
            WHERE gcm.is_active = 1 -- Ensure the membership itself is marked active
            AND date('now') BETWEEN gcm.start_date AND gcm.end_date -- Check for current active status by date range
            AND gcm.end_date BETWEEN ? AND ? -- Check for renewal period
            ORDER BY gcm.end_date ASC, m.name ASC;
            """
            # Parameters for the query: start_date_str and end_date_str
            cursor.execute(sql_select_renewals, (start_date_str, end_date_str))

            # Fetch as a list of dictionaries or tuples.
            column_names = [description[0] for description in cursor.description]
            renewal_list = [dict(zip(column_names, row)) for row in cursor.fetchall()]

            return renewal_list

        except sqlite3.Error as e:
            logging.error(
                f"Database error while generating renewal report data: {e}",
                exc_info=True,
            )
            return []
        except Exception as ex:
            logging.error(
                f"Unexpected error while generating renewal report data: {ex}",
                exc_info=True,
            )
            return []
