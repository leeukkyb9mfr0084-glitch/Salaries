import sys
import os

# Adjust PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from reporter import database_manager
except ModuleNotFoundError:
    print("CRITICAL ERROR: Could not import 'reporter.database_manager'.")
    print("Ensure that the script is run from the project root where 'reporter' is a subdirectory.")
    sys.exit(1)

def main():
    target_member_id = 7
    target_member_name = "Test User Script" # From previous scripts, associated with ID 7
    target_member_phone = "0000000000"

    # Details of the Group Class transaction expected to exist (from add_group_class_transaction.py)
    # Plan ID 12 ("Test Auto Plan", 30 days), Start: 2025-06-09, End: 2025-07-09, Amount: 50
    expected_gc_plan_name = "Test Auto Plan"
    expected_gc_end_date = "2025-07-09"
    expected_gc_amount = 50.0

    # Details of the PT transaction expected to exist (from add_pt_transaction.py)
    # Start: 2025-06-09, Amount: 200
    expected_pt_amount = 200.0

    # --- Verify Data Integrity (Implicitly by checking activities) ---
    print(f"--- Verifying Expected Transactions for Member ID {target_member_id} ---")
    activities = database_manager.get_all_activity_for_member(target_member_id)
    gc_transaction_present = False
    pt_transaction_present = False

    if not activities:
        print(f"CRITICAL: No activities found for member {target_member_id}. Cannot proceed with test.")
        return

    for activity in activities:
        # (transaction_type, name_or_description, payment_date, start_date, end_date, amount_paid, payment_method_or_sessions, transaction_id)
        if (activity[0] == 'Group Class' and
            activity[1] == expected_gc_plan_name and
            activity[3] == '2025-06-09' and # start_date
            activity[4] == expected_gc_end_date and # end_date
            activity[5] == expected_gc_amount):
            gc_transaction_present = True
            print(f"Found expected Group Class transaction: {activity}")

        if (activity[0] == 'Personal Training' and
            activity[3] == '2025-06-09' and # start_date
            activity[5] == expected_pt_amount):
            pt_transaction_present = True
            print(f"Found expected Personal Training transaction: {activity}")

    if not (gc_transaction_present and pt_transaction_present):
        print("CRITICAL: Not all expected transactions for member 7 are present. Renewal/Finance tests might be invalid.")
        print(f"  Group Class present: {gc_transaction_present}, Personal Training present: {pt_transaction_present}")
        # Decide if to proceed or not; for now, proceed but with this warning.
        # return

    print(f"\n--- 1. Fetching Pending Renewals for July 2025 ---")
    # Target date for renewals: any date in July 2025, e.g., 2025-07-01
    renewals_target_date = "2025-07-01"
    pending_renewals = database_manager.get_pending_renewals(renewals_target_date)

    found_expected_renewal = False
    if pending_renewals:
        print(f"Found {len(pending_renewals)} pending renewal(s) for month of {renewals_target_date}:")
        for renewal in pending_renewals:
            # (client_name, phone, plan_name, end_date)
            print(f"  - Name: {renewal[0]}, Phone: {renewal[1]}, Plan: {renewal[2]}, End Date: {renewal[3]}")
            if (renewal[0] == target_member_name and
                renewal[1] == target_member_phone and
                renewal[2] == expected_gc_plan_name and
                renewal[3] == expected_gc_end_date):
                found_expected_renewal = True

        if found_expected_renewal:
            print(f"Success: Expected renewal for '{target_member_name}' (Plan: '{expected_gc_plan_name}', End: {expected_gc_end_date}) found.")
        else:
            print(f"Error: Expected renewal for '{target_member_name}' not found in July 2025 renewals list.")
    else:
        print(f"No pending renewals found for July 2025. Expected at least one for '{target_member_name}'.")

    print(f"\n--- 2. Fetching Finance Report for June 2025 ---")
    report_year = 2025
    report_month = 6
    total_revenue_june = database_manager.get_finance_report(report_year, report_month)

    expected_revenue_june = expected_gc_amount + expected_pt_amount # 50 + 200 = 250

    if total_revenue_june is not None:
        print(f"Total revenue for {report_year}-{report_month:02d}: {total_revenue_june}")
        if total_revenue_june == expected_revenue_june:
            print(f"Success: Finance report for June {report_year} matches expected total of {expected_revenue_june}.")
        else:
            # As per analysis, no other June 2025 payments are expected from migration.
            # If there were, this check would need to be total_revenue_june >= expected_revenue_june
            print(f"Error: Finance report for June {report_year} is {total_revenue_june}, but expected {expected_revenue_june}.")
            print("This implies other transactions with payment_date in June 2025 exist, or an issue with the test data/logic.")
    else:
        print(f"Error: Could not retrieve finance report for June {report_year}.")

if __name__ == '__main__':
    if os.getenv('PYTHONPATH') is None or not os.getcwd() in os.getenv('PYTHONPATH').split(os.pathsep):
         os.environ['PYTHONPATH'] = os.getcwd() + (os.pathsep + os.getenv('PYTHONPATH') if os.getenv('PYTHONPATH') else '')
    main()
