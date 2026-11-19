
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from db import get_db_connection


app = Flask(__name__)
app.secret_key = "change-this-to-a-long-random-secret-key"


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return render_template("login.html")


# ==========================================
# USER LOGIN
# ==========================================

@app.route("/login", methods=["POST"])
def login():

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "").strip().lower()

    connection = get_db_connection()

    if connection is None:
        flash("Database connection failed.")
        return redirect(url_for("home"))

    cursor = connection.cursor(dictionary=True)

    try:

        query = """
            SELECT user_id, full_name, email, password_hash, role
            FROM users
            WHERE email = %s AND role = %s
        """

        cursor.execute(query, (email, role))
        user = cursor.fetchone()

        if user and check_password_hash(
            user["password_hash"], password
        ):

            session.clear()

            session["user_id"] = user["user_id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"].lower()

            return redirect(url_for("dashboard"))

        flash("Invalid email, password or role.")
        return redirect(url_for("home"))

    except Exception as e:

        print("Login error:", e)
        flash("Something went wrong. Please try again.")
        return redirect(url_for("home"))

    finally:

        cursor.close()
        connection.close()


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("home"))

    role = session.get("role", "").lower()


    # ==========================================
    # MANAGER DASHBOARD
    # ==========================================

    if role == "manager":

        connection = get_db_connection()

        if connection is None:
            flash("Database connection failed.")
            return redirect(url_for("home"))

        cursor = connection.cursor(dictionary=True)

        try:

            # ----------------------------------
            # 1. EMPLOYEE MONITORING
            # ----------------------------------

            employee_query = """
                SELECT
                    e.employee_id,
                    u.full_name,
                    u.email,
                    e.department,
                    e.designation,
                    el.latitude,
                    el.longitude,
                    el.is_sharing,
                    el.recorded_at

                FROM employees e

                JOIN users u
                    ON e.user_id = u.user_id

                LEFT JOIN employee_locations el
                    ON el.location_id = (
                        SELECT el2.location_id
                        FROM employee_locations el2
                        WHERE el2.employee_id = e.employee_id
                        ORDER BY el2.recorded_at DESC,
                                 el2.location_id DESC
                        LIMIT 1
                    )

                ORDER BY u.full_name
            """

            cursor.execute(employee_query)
            employees = cursor.fetchall()


            # ----------------------------------
            # 2. FIELD VISIT HISTORY
            # ----------------------------------

            visit_query = """
                SELECT
                    fv.visit_id,
                    fv.employee_id,
                    u.full_name AS employee_name,
                    fv.client_name,
                    fv.location,
                    fv.visit_date,
                    fv.purpose,
                    fv.status,
                    fv.remarks,
                    fv.latitude,
                    fv.longitude,
                    fv.created_at

                FROM field_visits fv

                JOIN employees e
                    ON fv.employee_id = e.employee_id

                JOIN users u
                    ON e.user_id = u.user_id

                ORDER BY fv.visit_date DESC,
                         fv.visit_id DESC
            """

            cursor.execute(visit_query)
            field_visits = cursor.fetchall()


            # ----------------------------------
            # 3. OVERALL ACTIVITY STATISTICS
            # ----------------------------------

            report_query = """
                SELECT

                    (SELECT COUNT(*)
                     FROM employees)
                     AS total_employees,

                    COUNT(*) AS total_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN status = 'Completed'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS completed_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN status = 'Planned'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS planned_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN status = 'Cancelled'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS cancelled_visits

                FROM field_visits
            """

            cursor.execute(report_query)
            reports = cursor.fetchone()


            # ----------------------------------
            # 4. DAILY VISIT REPORT
            # ----------------------------------

            daily_report_query = """
                SELECT
                    COUNT(*) AS total_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN status = 'Completed'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS completed_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN status = 'Planned'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS planned_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN status = 'Cancelled'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS cancelled_visits

                FROM field_visits

                WHERE visit_date = CURDATE()
            """

            cursor.execute(daily_report_query)
            daily_reports = cursor.fetchone()


            # ----------------------------------
            # 5. MONTHLY VISIT REPORT
            # ----------------------------------

            monthly_report_query = """
                SELECT
                    COUNT(*) AS total_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN status = 'Completed'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS completed_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN status = 'Planned'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS planned_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN status = 'Cancelled'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS cancelled_visits

                FROM field_visits

                WHERE YEAR(visit_date) = YEAR(CURDATE())
                  AND MONTH(visit_date) = MONTH(CURDATE())
            """

            cursor.execute(monthly_report_query)
            monthly_reports = cursor.fetchone()


            # ----------------------------------
            # 6. EMPLOYEE-WISE VISIT SUMMARY
            # ----------------------------------

            employee_report_query = """
                SELECT
                    e.employee_id,
                    u.full_name AS employee_name,

                    COUNT(fv.visit_id) AS total_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN fv.status = 'Completed'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS completed_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN fv.status = 'Planned'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS planned_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN fv.status = 'Cancelled'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS cancelled_visits

                FROM employees e

                JOIN users u
                    ON e.user_id = u.user_id

                LEFT JOIN field_visits fv
                    ON e.employee_id = fv.employee_id

                GROUP BY
                    e.employee_id,
                    u.full_name

                ORDER BY u.full_name
            """

            cursor.execute(employee_report_query)
            employee_reports = cursor.fetchall()


            # ----------------------------------
            # 7. DISPLAY MANAGER DASHBOARD
            # ----------------------------------

            return render_template(
                "manager_dashboard.html",

                name=session["full_name"],

                employees=employees,

                field_visits=field_visits,

                reports=reports,

                daily_reports=daily_reports,

                monthly_reports=monthly_reports,

                employee_reports=employee_reports
            )

        except Exception as e:

            print("Manager dashboard error:", e)

            flash(
                "Unable to load manager dashboard information."
            )

            return redirect(url_for("home"))

        finally:

            cursor.close()
            connection.close()


    # ==========================================
    # ADMIN DASHBOARD
    # ==========================================

    if role == "admin":

        connection = get_db_connection()

        if connection is None:
            flash("Database connection failed.", "error")
            return redirect(url_for("home"))

        cursor = connection.cursor(dictionary=True)

        try:

            cursor.execute("""
                SELECT
                    e.employee_id,
                    u.full_name,
                    u.email,
                    e.department,
                    e.designation

                FROM employees e

                JOIN users u
                    ON e.user_id = u.user_id

                ORDER BY e.employee_id DESC
            """)

            employees = cursor.fetchall()

            total_employees = len(employees)

            return render_template(
                "dashboard.html",
                name=session["full_name"],
                total_employees=total_employees,
                employees=employees
            )

        except Exception as e:

            print("Admin dashboard error:", e)

            flash("Unable to load Admin Dashboard.")

            return redirect(url_for("home"))

        finally:

            cursor.close()
            connection.close()


    # ==========================================
    # EMPLOYEE DASHBOARD
    # ==========================================

    if role == "employee":

        connection = get_db_connection()

        if connection is None:
            flash("Database connection failed.")
            return redirect(url_for("home"))

        cursor = connection.cursor(dictionary=True)

        try:

            # ----------------------------------
            # 1. GET EMPLOYEE DETAILS
            # ----------------------------------

            cursor.execute(
                """
                SELECT
                    employee_id,
                    department,
                    designation

                FROM employees

                WHERE user_id = %s
                """,
                (session["user_id"],)
            )

            employee = cursor.fetchone()

            if not employee:
                flash("Employee profile not found.")
                return redirect(url_for("home"))

            employee_id = employee["employee_id"]


            # ----------------------------------
            # 2. GET EMPLOYEE VISIT STATISTICS
            # ----------------------------------

            stats_query = """
                SELECT
                    COUNT(*) AS total_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN status = 'Completed'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS completed_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN status = 'Planned'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS planned_visits,

                    COALESCE(SUM(
                        CASE
                            WHEN status = 'Cancelled'
                            THEN 1 ELSE 0
                        END
                    ), 0) AS cancelled_visits

                FROM field_visits

                WHERE employee_id = %s
            """

            cursor.execute(
                stats_query,
                (employee_id,)
            )

            stats = cursor.fetchone()


            # ----------------------------------
            # 3. GET EMPLOYEE VISIT HISTORY
            # ----------------------------------

            visit_query = """
                SELECT
                    visit_id,
                    client_name,
                    location,
                    visit_date,
                    purpose,
                    status,
                    remarks,
                    latitude,
                    longitude,
                    created_at

                FROM field_visits

                WHERE employee_id = %s

                ORDER BY visit_date DESC, visit_id DESC
            """

            cursor.execute(
                visit_query,
                (employee_id,)
            )

            my_visits = cursor.fetchall()


            # ----------------------------------
            # 4. DISPLAY EMPLOYEE DASHBOARD
            # ----------------------------------

            return render_template(
                "employee_dashboard.html",
                name=session["full_name"],
                employee=employee,
                stats=stats,
                my_visits=my_visits
            )

        except Exception as e:

            print("Employee dashboard error:", e)

            flash("Unable to load employee dashboard.")

            return redirect(url_for("home"))

        finally:

            cursor.close()
            connection.close()


    # ==========================================
    # INVALID ROLE
    # ==========================================

    session.clear()

    flash("Invalid user role.")

    return redirect(url_for("home"))


# ==========================================
# UPDATE FIELD VISIT STATUS
# ==========================================

@app.route(
    "/update_visit_status/<int:visit_id>",
    methods=["POST"]
)
def update_visit_status(visit_id):

    if "user_id" not in session:
        return redirect(url_for("home"))

    if session.get("role", "").lower() != "manager":
        flash("You are not authorized to update visit status.")
        return redirect(url_for("home"))

    new_status = request.form.get(
        "status", ""
    ).strip()

    allowed_statuses = [
        "Planned",
        "Completed",
        "Cancelled"
    ]

    if new_status not in allowed_statuses:
        flash("Invalid visit status.")
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    if connection is None:
        flash("Database connection failed.")
        return redirect(url_for("dashboard"))

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT visit_id
            FROM field_visits
            WHERE visit_id = %s
            """,
            (visit_id,)
        )

        visit = cursor.fetchone()

        if visit is None:
            flash("Field visit record not found.")
            return redirect(url_for("dashboard"))

        cursor.execute(
            """
            UPDATE field_visits
            SET status = %s
            WHERE visit_id = %s
            """,
            (new_status, visit_id)
        )

        connection.commit()

        flash("Visit status updated successfully!")

    except Exception as e:

        connection.rollback()

        print("Visit status update error:", e)

        flash("Unable to update visit status.")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("dashboard"))


# ==========================================
# EMPLOYEE FIELD VISIT SUBMISSION
# ==========================================

@app.route("/add_visit", methods=["POST"])
def add_visit():

    if "user_id" not in session:
        return redirect(url_for("home"))

    if session.get("role", "").lower() != "employee":
        flash("Only employees can submit field visits.")
        return redirect(url_for("dashboard"))

    client_name = request.form.get(
        "client_name", ""
    ).strip()

    location = request.form.get(
        "visit_location", ""
    ).strip()

    visit_date = request.form.get(
        "visit_date", ""
    ).strip()

    purpose = request.form.get(
        "purpose", ""
    ).strip()

    remarks = request.form.get(
        "remarks", ""
    ).strip()

    latitude = request.form.get(
        "latitude", ""
    ).strip() or None

    longitude = request.form.get(
        "longitude", ""
    ).strip() or None

    if not client_name or not visit_date:
        flash("Client name and visit date are required.")
        return redirect(url_for("dashboard"))

    try:

        datetime.strptime(visit_date, "%Y-%m-%d")

    except ValueError:

        flash("Please enter a valid visit date.")
        return redirect(url_for("dashboard"))

    connection = get_db_connection()

    if connection is None:
        flash("Database connection failed.")
        return redirect(url_for("dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT employee_id
            FROM employees
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        employee = cursor.fetchone()

        if not employee:
            flash("Employee profile not found.")
            return redirect(url_for("dashboard"))

        employee_id = employee["employee_id"]

        query = """
            INSERT INTO field_visits
            (
                employee_id,
                client_name,
                location,
                visit_date,
                purpose,
                remarks,
                latitude,
                longitude
            )

            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            employee_id,
            client_name,
            location or None,
            visit_date,
            purpose or None,
            remarks or None,
            latitude,
            longitude
        )

        cursor.execute(query, values)

        connection.commit()

        flash("Field visit submitted successfully!")

    except Exception as e:

        connection.rollback()

        print("Field visit error:", e)

        flash(
            "Unable to submit field visit. Please try again."
        )

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("dashboard"))


# ==========================================
# SAVE EMPLOYEE GPS LOCATION
# ==========================================

@app.route("/api/location", methods=["POST"])
def save_location():

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Please log in."
        }), 401

    if session.get("role", "").lower() != "employee":
        return jsonify({
            "success": False,
            "message": "Employee access only."
        }), 403

    data = request.get_json(silent=True) or {}

    try:

        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))

        if not (-90 <= latitude <= 90):
            raise ValueError("Invalid latitude")

        if not (-180 <= longitude <= 180):
            raise ValueError("Invalid longitude")

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message": "Invalid GPS coordinates."
        }), 400

    connection = get_db_connection()

    if connection is None:
        return jsonify({
            "success": False,
            "message": "Database connection failed."
        }), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT employee_id
            FROM employees
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        employee = cursor.fetchone()

        if not employee:
            return jsonify({
                "success": False,
                "message": "Employee profile not found."
            }), 404

        query = """
            INSERT INTO employee_locations
            (employee_id, latitude, longitude, is_sharing)
            VALUES (%s, %s, %s, 1)
        """

        cursor.execute(
            query,
            (
                employee["employee_id"],
                latitude,
                longitude
            )
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Location saved successfully."
        })

    except Exception as e:

        connection.rollback()

        print("Location save error:", e)

        return jsonify({
            "success": False,
            "message": "Unable to save location."
        }), 500

    finally:

        cursor.close()
        connection.close()


# ==========================================
# STOP EMPLOYEE LOCATION SHARING
# ==========================================

@app.route("/api/location/stop", methods=["POST"])
def stop_location_sharing():

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Please log in."
        }), 401

    if session.get("role", "").lower() != "employee":
        return jsonify({
            "success": False,
            "message": "Employee access only."
        }), 403

    connection = get_db_connection()

    if connection is None:
        return jsonify({
            "success": False,
            "message": "Database connection failed."
        }), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT employee_id
            FROM employees
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        employee = cursor.fetchone()

        if not employee:
            return jsonify({
                "success": False,
                "message": "Employee profile not found."
            }), 404

        cursor.execute(
            """
            UPDATE employee_locations
            SET is_sharing = 0
            WHERE employee_id = %s
              AND is_sharing = 1
            """,
            (employee["employee_id"],)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Location sharing stopped."
        })

    except Exception as e:

        connection.rollback()

        print("Stop location error:", e)

        return jsonify({
            "success": False,
            "message": "Unable to stop location sharing."
        }), 500

    finally:

        cursor.close()
        connection.close()


# ==========================================
# ADMIN: ADD EMPLOYEE
# ==========================================

@app.route("/admin/add_employee", methods=["POST"])
def admin_add_employee():

    if (
        "user_id" not in session
        or session.get("role", "").lower() != "admin"
    ):
        flash("Unauthorized access.", "error")
        return redirect(url_for("home"))

    full_name = request.form.get(
        "full_name", ""
    ).strip()

    email = request.form.get(
        "email", ""
    ).strip().lower()

    password = request.form.get(
        "password", ""
    )

    phone = request.form.get(
        "phone", ""
    ).strip() or None

    department = request.form.get(
        "department", ""
    ).strip() or None

    designation = request.form.get(
        "designation", ""
    ).strip() or None

    joining_date = request.form.get(
        "joining_date", ""
    ).strip() or None

    if not full_name or not email or not password:
        flash(
            "Name, email and password are required.",
            "error"
        )
        return redirect(url_for("dashboard"))

    if len(password) < 8:
        flash(
            "Password must contain at least 8 characters.",
            "error"
        )
        return redirect(url_for("dashboard"))

    if joining_date:

        try:

            datetime.strptime(
                joining_date, "%Y-%m-%d"
            )

        except ValueError:

            flash("Invalid joining date.", "error")
            return redirect(url_for("dashboard"))

    connection = get_db_connection()

    if connection is None:
        flash("Database connection failed.", "error")
        return redirect(url_for("dashboard"))

    cursor = connection.cursor()

    try:

        hashed_password = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users
            (full_name, email, password_hash, role, phone)

            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                full_name,
                email,
                hashed_password,
                "employee",
                phone
            )
        )

        user_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO employees
            (user_id, department, designation, joining_date)

            VALUES (%s, %s, %s, %s)
            """,
            (
                user_id,
                department,
                designation,
                joining_date
            )
        )

        connection.commit()

        flash(
            "Employee account created successfully!",
            "success"
        )

    except Exception as e:

        connection.rollback()

        print("Employee creation error:", e)

        flash(
            "Unable to create employee. Check whether the email already exists.",
            "error"
        )

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("dashboard"))


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    flash("You have logged out successfully.")

    return redirect(url_for("home"))


# ==========================================
# RUN FLASK APPLICATION
# ==========================================

if __name__ == "__main__":

    app.run(debug=True)
