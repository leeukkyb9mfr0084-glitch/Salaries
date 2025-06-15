import os
from flask import Flask, request, jsonify
from .database_manager import DatabaseManager
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_NAME = "kranos_gym.db"
DB_PATH = os.path.join("db", DB_NAME)

app = Flask(__name__)

try:
    db_manager = DatabaseManager(db_path=DB_PATH)
except Exception as e:
    print(f"CRITICAL: Failed to initialize DatabaseManager: {e}")
    db_manager = None


@app.teardown_appcontext
def shutdown_session(exception=None):
    pass


@app.route("/api/reports/renewal", methods=["GET"])
def get_renewal_report():
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    try:
        days_ahead_str = request.args.get("days_ahead", default="30")
        if not days_ahead_str.isdigit():
            return jsonify({"error": "Invalid 'days_ahead' parameter."}), 400
        days_ahead = int(days_ahead_str)
        if days_ahead < 0:
            return jsonify({"error": "'days_ahead' must be non-negative."}), 400
    except ValueError:
        return jsonify({"error": "Invalid 'days_ahead' parameter."}), 400
    try:
        report_df = db_manager.generate_renewal_report(days_ahead)
        if report_df is None:
            return jsonify({"error": "Failed to generate renewal report."}), 500
        return jsonify(report_df.to_dict(orient="records"))
    except Exception as e:
        app.logger.error(f"Error generating renewal report: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/reports/monthly", methods=["GET"])
def get_monthly_report_api():
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    try:
        month_str = request.args.get("month")
        year_str = request.args.get("year")
        if not month_str or not year_str:
            return jsonify({"error": "Missing 'month' or 'year'."}), 400
        if not month_str.isdigit() or not year_str.isdigit():
            return jsonify({"error": "'month'/'year' must be integers."}), 400
        month, year = int(month_str), int(year_str)
        if not (1 <= month <= 12):
            return jsonify({"error": "Invalid 'month'."}), 400
    except ValueError:
        return jsonify({"error": "Invalid 'month' or 'year'."}), 400
    try:
        report_data = db_manager.get_monthly_financial_report(month, year)
        if report_data is None:
            return jsonify({"error": "Failed to generate monthly report."}), 500
        return jsonify(report_data)
    except Exception as e:
        app.logger.error(f"Error in monthly report for {month}-{year}: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/transactions", methods=["POST"])
def create_transaction_api():
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided."}), 400

    member_id = data.get("member_id")
    plan_id = data.get("plan_id")
    transaction_date_str = data.get("payment_date")  # From Streamlit form
    amount_paid_str = data.get("amount_paid")
    payment_method = data.get("payment_method")
    transaction_type = data.get("transaction_type")
    notes = data.get("notes", "")

    required_fields = {
        "member_id": member_id,
        "payment_date": transaction_date_str,
        "amount_paid": amount_paid_str,
        "payment_method": payment_method,
        "transaction_type": transaction_type,
    }
    for field, value in required_fields.items():
        if value is None:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    if transaction_type in ["New Subscription", "Renewal"] and not plan_id:
        return (
            jsonify(
                {
                    "error": f"plan_id is required for transaction type '{transaction_type}'."
                }
            ),
            400,
        )

    try:
        amount_paid = float(amount_paid_str)
        if amount_paid < 0:
            return jsonify({"error": "amount_paid must be non-negative."}), 400
    except ValueError:
        return jsonify({"error": "Invalid amount_paid format."}), 400

    try:
        transaction_id = db_manager.add_membership_transaction(
            member_id=member_id,
            plan_id=plan_id,
            transaction_date_str=transaction_date_str,
            amount_paid=amount_paid,
            payment_method=payment_method,
            notes=notes,
            transaction_type=transaction_type,
        )
        if transaction_id:
            return (
                jsonify(
                    {
                        "message": "Transaction recorded",
                        "transaction_id": transaction_id,
                    }
                ),
                201,
            )
        else:  # Should ideally be caught by specific exceptions from db_manager
            return (
                jsonify(
                    {
                        "error": "Failed to record transaction (unknown DB manager error)."
                    }
                ),
                500,
            )
    except ValueError as ve:
        app.logger.warning(f"Validation error creating transaction: {ve}")
        return jsonify({"error": str(ve)}), 400
    except ConnectionError as ce:
        app.logger.error(f"DB connection error: {ce}")
        return jsonify({"error": "Database service unavailable"}), 503
    except Exception as e:
        app.logger.error(f"Unexpected error in create_transaction_api: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/plans", methods=["POST"])
def add_plan_api():
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided."}), 400
    name = data.get("name")
    price_str = data.get("price")
    duration_str = data.get("duration")
    plan_type = data.get("type")
    is_active = data.get("is_active", True)
    if is_active is None:
        is_active = True
    if not all([name, price_str is not None, duration_str, plan_type]):
        return (
            jsonify({"error": "Missing fields: name, price, duration, type required."}),
            400,
        )
    try:
        price = int(price_str)
        if price < 0:
            return jsonify({"error": "Price must be non-negative."}), 400
        if not isinstance(duration_str, str) or not duration_str.strip():
            return jsonify({"error": "Duration must be non-empty string."}), 400
    except ValueError:
        return jsonify({"error": "Price must be integer."}), 400
    allowed_plan_types = [
        "GC",
        "PT",
        "Group Class",
        "Personal Training",
        "Open Mat",
        "Other",
    ]
    if plan_type not in allowed_plan_types:
        return jsonify({"error": f"Invalid type: {plan_type}."}), 400
    try:
        plan_id = db_manager.add_plan(
            name, price, duration_str, plan_type, is_active=is_active
        )
        if plan_id:
            return jsonify({"message": "Plan added", "plan_id": plan_id}), 201
        else:
            return (
                jsonify({"error": "Failed to add plan (duplicate name or DB issue)."}),
                500,
            )
    except Exception as e:
        app.logger.error(f"Error in add_plan_api: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/plans/<int:plan_id>", methods=["PUT"])
def update_plan_api(plan_id):
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided."}), 400
    name = data.get("name")
    price_str = data.get("price")
    duration_str = data.get("duration")
    plan_type = data.get("type")
    if not all([name, price_str is not None, duration_str, plan_type]):
        return (
            jsonify({"error": "Missing fields: name, price, duration, type required."}),
            400,
        )
    try:
        price = int(price_str)
        if price < 0:
            return jsonify({"error": "Price must be non-negative."}), 400
        if not isinstance(duration_str, str) or not duration_str.strip():
            return jsonify({"error": "Duration must be non-empty string."}), 400
    except ValueError:
        return jsonify({"error": "Price must be integer."}), 400
    allowed_plan_types = [
        "GC",
        "PT",
        "Group Class",
        "Personal Training",
        "Open Mat",
        "Other",
    ]
    if plan_type not in allowed_plan_types:
        return jsonify({"error": f"Invalid type: {plan_type}."}), 400
    try:
        updated_count = db_manager.update_plan(
            plan_id, name, price, duration_str, plan_type
        )
        if updated_count:
            return jsonify({"message": f"Plan ID {plan_id} updated."}), 200
        elif updated_count == 0:
            return jsonify({"error": f"Plan ID {plan_id} not found or no change."}), 404
        else:
            return (
                jsonify(
                    {"error": "Failed to update plan (duplicate name or DB issue)."}
                ),
                500,
            )
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        app.logger.error(f"Error updating plan {plan_id}: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/plans/<int:plan_id>", methods=["DELETE"])
def delete_plan_api(plan_id):
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    try:
        deleted_count = db_manager.delete_plan(plan_id)
        if deleted_count:
            return jsonify({"message": f"Plan ID {plan_id} deleted."}), 200
        elif deleted_count == 0:
            return jsonify({"error": f"Plan ID {plan_id} not found."}), 404
        else:
            return jsonify({"error": "Failed to delete plan (DB error)."}), 500
    except Exception as e:
        app.logger.error(f"Error deleting plan {plan_id}: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/plans/<int:plan_id>/status", methods=["PUT"])
def set_plan_active_status_api(plan_id):
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    data = request.get_json()
    if (
        data is None
        or "is_active" not in data
        or not isinstance(data["is_active"], bool)
    ):
        return jsonify({"error": "Invalid input: 'is_active' (boolean) required."}), 400
    is_active = data["is_active"]
    try:
        updated_count = db_manager.set_plan_active_status(plan_id, is_active)
        if updated_count:
            return (
                jsonify({"message": f"Plan ID {plan_id} status set to {is_active}"}),
                200,
            )
        elif updated_count == 0:
            return jsonify({"error": f"Plan ID {plan_id} not found."}), 404
        else:
            return jsonify({"error": "Failed to update plan status (DB error)."}), 500
    except Exception as e:
        app.logger.error(f"Error setting plan status {plan_id}: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/plans/all", methods=["GET"])
def get_all_plans_api():
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    try:
        plans_df = db_manager.get_all_plans_details()
        if plans_df is None:
            return jsonify({"error": "Failed to retrieve plans."}), 500
        return jsonify(plans_df.to_dict(orient="records"))
    except Exception as e:
        app.logger.error(f"Error in get_all_plans_api: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/members", methods=["POST"])
def create_member_api():
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided."}), 400
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    join_date_str = data.get("join_date")
    notes = data.get("notes", "")
    if not name or not phone:
        return jsonify({"error": "Name and phone are required."}), 400
    try:
        member_id = db_manager.add_member(name, email, phone, join_date_str, notes)
        if member_id:
            return jsonify({"message": "Member added", "member_id": member_id}), 201
        else:
            return jsonify({"error": "Failed to add member (DB manager error)."}), 500
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        app.logger.error(f"Error in create_member_api: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/member/<int:member_id_path>", methods=["PUT"])
def update_member_api(member_id_path: int):
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided."}), 400
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    join_date_str = data.get("join_date")
    notes = data.get("notes")
    is_active = data.get("is_active")
    if not name or not phone:
        return jsonify({"error": "Name and phone are required."}), 400
    if is_active is None or not isinstance(is_active, bool):
        return jsonify({"error": "'is_active' (boolean) required."}), 400
    notes_to_pass = notes if notes is not None else ""
    try:
        updated_count = db_manager.update_member(
            member_id_path, name, email, phone, join_date_str, notes_to_pass, is_active
        )
        if updated_count:
            return jsonify({"message": f"Member ID {member_id_path} updated."}), 200
        elif updated_count == 0:
            return (
                jsonify(
                    {"error": f"Member ID {member_id_path} not found or no change."}
                ),
                404,
            )
        else:
            return (
                jsonify({"error": "Failed to update member (DB manager error)."}),
                500,
            )
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        app.logger.error(f"Error updating member {member_id_path}: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/member/<int:member_id_path>/active_status", methods=["PUT"])
def set_member_active_status_api(member_id_path: int):
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    data = request.get_json()
    if (
        data is None
        or "is_active" not in data
        or not isinstance(data["is_active"], bool)
    ):
        return jsonify({"error": "Invalid input: 'is_active' (boolean) required."}), 400
    is_active = data["is_active"]
    try:
        updated_count = db_manager.set_member_active_status(member_id_path, is_active)
        if updated_count:
            return (
                jsonify(
                    {"message": f"Member ID {member_id_path} status set to {is_active}"}
                ),
                200,
            )
        elif updated_count == 0:
            return jsonify({"error": f"Member ID {member_id_path} not found."}), 404
        else:
            return jsonify({"error": "Failed to update member status (DB error)."}), 500
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        app.logger.error(f"Error setting member status {member_id_path}: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/members/filtered/", methods=["GET"])
def get_filtered_members_api():
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    search_term = request.args.get("search_term", None)
    plan_type = request.args.get("plan_type", None)
    status = request.args.get("status", None)
    try:
        members_df = db_manager.get_filtered_members(
            search_term=search_term, plan_type=plan_type, status=status
        )
        if members_df is None:
            return jsonify({"error": "Failed to retrieve members."}), 500
        return jsonify(members_df.to_dict(orient="records"))
    except Exception as e:
        app.logger.error(f"Error in get_filtered_members_api: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/member/<int:member_id>", methods=["GET"])
def get_member_details_api(member_id):
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    try:
        member_details = db_manager.get_member_details(member_id)
        if member_details is not None:
            # Ensure date is in ISO format (already handled by Series if from TEXT)
            return jsonify(member_details.to_dict())
        else:
            return jsonify({"error": f"Member ID {member_id} not found"}), 404
    except Exception as e:
        app.logger.error(f"Error in get_member_details_api for ID {member_id}: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/plans/list", methods=["GET"])
def get_plans_list_api():
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    try:
        plans_list = db_manager.get_all_plans_for_selection()
        return jsonify([{"id": pid, "name": pname} for pid, pname in plans_list])
    except Exception as e:
        app.logger.error(f"Error in get_plans_list_api: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/member/<int:member_id>/transactions", methods=["GET"])
def get_member_transactions_api(member_id):
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    try:
        transactions_df = db_manager.get_member_transaction_history(member_id)
        if transactions_df is None:
            return jsonify({"error": "Failed to retrieve transactions."}), 500
        return jsonify(transactions_df.to_dict(orient="records"))
    except Exception as e:
        app.logger.error(f"Error for member {member_id} transactions: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/transactions/filtered", methods=["GET"])
def get_filtered_transactions_api():
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    try:
        params = {
            "start_date": request.args.get("start_date"),
            "end_date": request.args.get("end_date"),
            "member_name_search": request.args.get("member_name_search"),
            "transaction_type": request.args.get("transaction_type"),
        }
        # Filter out None values to pass only provided filters
        active_params = {k: v for k, v in params.items() if v is not None}
        transactions_df = db_manager.get_filtered_transactions(**active_params)
        if transactions_df is None:
            return jsonify({"error": "Failed to retrieve transactions."}), 500
        return jsonify(transactions_df.to_dict(orient="records"))
    except Exception as e:
        app.logger.error(f"Error in get_filtered_transactions_api: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/books/close", methods=["POST"])
def close_books_api():
    if not db_manager:
        return jsonify({"error": "Database service not available"}), 503
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided."}), 400
    month_str = data.get("month")
    year_str = data.get("year")
    if not month_str or not year_str:
        return jsonify({"error": "Month and year required."}), 400
    try:
        month = int(month_str)
        year = int(year_str)
        if not (1 <= month <= 12 and 2000 < year < 2100):
            return jsonify({"error": "Invalid month or year."}), 400
    except ValueError:
        return jsonify({"error": "Month/year must be integers."}), 400
    try:
        success = db_manager.perform_book_closing(month, year)
        if success:
            return jsonify({"message": f"Books closed for {month:02d}-{year}."}), 200
        else:
            return (
                jsonify(
                    {
                        "error": f"Failed to close books for {month:02d}-{year} (see logs)."
                    }
                ),
                500,
            )
    except Exception as e:
        app.logger.error(f"Error closing books for {month:02d}-{year}: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


if __name__ == "__main__":
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    if not db_manager:
        print("Cannot start Flask app: DatabaseManager failed to initialize.")
    else:
        app.run(debug=True, port=5000)
