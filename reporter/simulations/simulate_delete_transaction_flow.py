import os
import sys
from datetime import datetime, timedelta
import time

# --- Setup Project Path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from reporter.gui import GuiController
from reporter import database_manager
from reporter.database import create_database, seed_initial_plans

# --- Simulation Database Setup ---
SIMULATION_DB_DIR = os.path.join(project_root, "reporter", "simulations", "sim_data")
# Using a specific DB file for this simulation
SIMULATION_DB_FILE = os.path.join(
    SIMULATION_DB_DIR, "simulation_kranos_data_del_trans.db"
)

# original_db_file is captured in __main__ block

# Define SIM_DB_DIR and SIM_DB_FILE at global scope
SIM_DB_DIR = os.path.join(project_root, "reporter", "simulations", "sim_data")
SIM_DB_FILE = os.path.join(SIM_DB_DIR, "simulation_kranos_data_del_trans.db")


def main_simulation_logic(controller: GuiController):  # Renamed and controller passed
    print("\n--- Starting Simulation: Delete Transaction Flow ---")

    # 1. Add a test member
    member_name = f"TxDeleteUser_{int(time.time())%1000}"
    member_phone = f"TDEL{int(time.time())%100000}"
    print(f"\nStep 1: Adding test member: Name='{member_name}', Phone='{member_phone}'")
    add_success, _ = controller.db_manager.add_member_to_db(member_name, member_phone)
    if not add_success:  # Check the success flag from the tuple
        print(f"FAILURE: Could not add member '{member_name}'.")
        # cleanup_simulation_environment() # Cleanup is in __main__
        return

    member_db_info = controller.db_manager.get_all_members(phone_filter=member_phone)
    if not member_db_info:
        print(f"FAILURE: Member '{member_name}' not found after adding.")
        # cleanup_simulation_environment() # Cleanup is in __main__
        return
    member_id = member_db_info[0][0]
    print(f"Member added successfully. ID: {member_id}")

    # 2. Add two transactions for the member
    print(f"\nStep 2: Adding two transactions for member ID {member_id}")
    plans = controller.db_manager.get_all_plans()
    if len(plans) < 1:  # Need at least one plan
        print("FAILURE: Not enough plans found. Seeding might have failed.")
        # cleanup_simulation_environment() # Cleanup is in __main__
        return
    plan_id1 = plans[0][0]

    tx1_details = {
        "transaction_type": "Group Class",
        "member_id": member_id,
        "plan_id": plan_id1,
        "payment_date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
        "start_date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
        "amount_paid": 60.00,
        "payment_method": "SimCash1",
    }
    tx2_details = {
        "transaction_type": "Personal Training",
        "member_id": member_id,
        "start_date": datetime.now().strftime("%Y-%m-%d"),
        "sessions": 5,
        "amount_paid": 200.00,
        "payment_date": datetime.now().strftime(
            "%Y-%m-%d"
        ),  # PT needs payment_date too
        "payment_method": "SimCardPT",  # PT can have payment_method
    }

    tx1_success, _ = controller.db_manager.add_transaction(**tx1_details)
    if not tx1_success:
        print(f"FAILURE: Could not add transaction 1 for member ID {member_id}.")
        # cleanup_simulation_environment() # Cleanup is in __main__
        return
    print("Transaction 1 added.")

    tx2_success, _ = controller.db_manager.add_transaction(**tx2_details)
    if not tx2_success:
        print(f"FAILURE: Could not add transaction 2 for member ID {member_id}.")
        # cleanup_simulation_environment() # Cleanup is in __main__
        return
    print("Transaction 2 added.")

    # Get IDs of the transactions
    activity = controller.db_manager.get_all_activity_for_member(member_id)
    if len(activity) != 2:
        print(
            f"FAILURE: Expected 2 transactions for member {member_id}, found {len(activity)}."
        )
        # cleanup_simulation_environment() # Cleanup is in __main__
        return

    # Assuming order by start_date DESC from get_all_activity_for_member
    # tx2 (PT, today) should be first, tx1 (GC, 10 days ago) second.
    transaction_id_to_delete = None
    other_transaction_id = None

    for trans in activity:
        # identify by amount or type, assuming amount is unique enough for this sim
        if trans[5] == 60.00:  # Amount for tx1
            transaction_id_to_delete = trans[7]  # activity_id
        elif trans[5] == 200.00:  # Amount for tx2
            other_transaction_id = trans[7]

    if not transaction_id_to_delete or not other_transaction_id:
        print(
            f"FAILURE: Could not reliably identify transaction IDs from activity list: {activity}"
        )
        # cleanup_simulation_environment() # Cleanup is in __main__
        return

    print(
        f"Transaction to delete ID: {transaction_id_to_delete} (Amount: {tx1_details['amount_paid']})"
    )
    print(
        f"Other transaction ID: {other_transaction_id} (Amount: {tx2_details['amount_paid']})"
    )

    # 3. Call controller.delete_transaction_action
    print(
        f"\nStep 3: Calling controller.delete_transaction_action for transaction ID {transaction_id_to_delete}"
    )
    # Based on test_gui_flows.py, controller.delete_transaction_action does NOT use askyesno.
    delete_success, delete_message = controller.delete_transaction_action(
        transaction_id_to_delete
    )
    print(f"Controller action message: '{delete_message}' (Success: {delete_success})")

    if not delete_success:
        print(
            f"WARNING: controller.delete_transaction_action reported failure for transaction ID {transaction_id_to_delete}."
        )
        # Continue to verification to see state

    # 4. Verify the specific transaction is deleted
    print("\nStep 4: Verifying transaction deletion...")
    activity_after_delete = controller.db_manager.get_all_activity_for_member(member_id)

    deleted_found = False
    other_tx_found = False
    if activity_after_delete:
        for trans in activity_after_delete:
            if trans[7] == transaction_id_to_delete:
                deleted_found = True
            if trans[7] == other_transaction_id:
                other_tx_found = True

    if not deleted_found:
        print(f"SUCCESS: Transaction ID {transaction_id_to_delete} correctly deleted.")
    else:
        print(
            f"FAILURE: Transaction ID {transaction_id_to_delete} still found after deletion attempt."
        )

    # 5. Verify the other transaction for the member still exists
    print("\nStep 5: Verifying other transaction still exists...")
    if other_tx_found:
        print(
            f"SUCCESS: Other transaction (ID: {other_transaction_id}) still exists for member {member_id}."
        )
        if (
            len(activity_after_delete) == 1
            and activity_after_delete[0][7] == other_transaction_id
        ):
            print("Correct number of transactions (1) remaining.")
        else:
            print(
                f"WARNING: Expected 1 transaction remaining, found {len(activity_after_delete)}."
            )
    else:
        print(
            f"FAILURE: Other transaction (ID: {other_transaction_id}) was also deleted or not found."
        )

    # 6. Verify the member still exists
    print("\nStep 6: Verifying member still exists...")
    member_after_delete = controller.db_manager.get_all_members(
        phone_filter=member_phone
    )
    if member_after_delete and member_after_delete[0][0] == member_id:
        print(f"SUCCESS: Member '{member_name}' (ID: {member_id}) still exists.")
    else:
        print(
            f"FAILURE: Member '{member_name}' (ID: {member_id}) was deleted or not found."
        )

    print("\n--- Simulation: Delete Transaction Flow Complete ---")
    # Cleanup is handled in the __main__ block's finally clause


if __name__ == "__main__":
    original_db_manager_db_file = database_manager.DB_FILE  # Store original
    db_connection = None  # Initialize db_connection

    try:
        print(f"--- Main: Setting up simulation DB: {SIM_DB_FILE} ---")
        os.makedirs(SIMULATION_DB_DIR, exist_ok=True)
        if os.path.exists(SIM_DB_FILE):
            os.remove(SIM_DB_FILE)
            print(f"Deleted existing simulation DB: {SIM_DB_FILE}")

        database_manager.DB_FILE = SIM_DB_FILE  # Monkeypatch

        create_database(db_name=SIM_DB_FILE)

        import sqlite3  # Ensure sqlite3 is imported

        seed_conn = None
        try:
            seed_conn = sqlite3.connect(SIM_DB_FILE)  # Connection for seeding
            seed_initial_plans(seed_conn)
            seed_conn.commit()
            print(f"Recreated and seeded simulation DB: {SIM_DB_FILE}")
        except Exception as e_seed:
            print(
                f"Error seeding simulation DB {SIM_DB_FILE}: {e_seed}", file=sys.stderr
            )
            raise
        finally:
            if seed_conn:
                seed_conn.close()

        # Create the main DB connection for the controller
        db_connection = sqlite3.connect(SIM_DB_FILE, check_same_thread=False)
        controller = GuiController(db_connection)  # Pass connection to controller

        main_simulation_logic(controller)  # Pass controller

    except Exception as e_outer:
        print(f"--- SIMULATION SCRIPT ERROR: {e_outer} ---", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        if db_connection:  # Close the main connection
            db_connection.close()
            print(f"Closed main DB connection to {SIM_DB_FILE}")
        database_manager.DB_FILE = (
            original_db_manager_db_file  # Restore global if it was used
        )
        print(
            f"--- Main: Restored database_manager.DB_FILE to: {original_db_manager_db_file} ---"
        )
