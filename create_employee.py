
from db import get_db_connection
from werkzeug.security import generate_password_hash
from getpass import getpass
from datetime import datetime

print("===== Create Employee Account =====")

full_name = input("Enter Employee Name: ").strip()
email = input("Enter Employee Email: ").strip().lower()
password = getpass("Create Employee Password: ")

phone = input("Enter Phone Number (optional): ").strip() or None
department = input("Enter Department: ").strip() or None
designation = input("Enter Designation: ").strip() or None
joining_date = input("Enter Joining Date (YYYY-MM-DD, optional): ").strip() or None

# Validate inputs
if not full_name or not email or not password:
    print("Name, email and password are required.")

elif len(password) < 8:
    print("Password must contain at least 8 characters.")

else:

    # Validate joining date
    if joining_date:
        try:
            datetime.strptime(joining_date, "%Y-%m-%d")
        except ValueError:
            print("Invalid date. Use YYYY-MM-DD format.")
            joining_date = "INVALID"

    if joining_date != "INVALID":

        connection = get_db_connection()

        if connection:
            cursor = connection.cursor()

            try:
                hashed_password = generate_password_hash(password)

                # STEP 1: Insert into users table
                user_query = """
                    INSERT INTO users
                    (full_name, email, password_hash, role, phone)
                    VALUES (%s, %s, %s, %s, %s)
                """

                cursor.execute(
                    user_query,
                    (
                        full_name,
                        email,
                        hashed_password,
                        "employee",
                        phone
                    )
                )

                # Get automatically generated user_id
                user_id = cursor.lastrowid

                # STEP 2: Insert into employees table
                employee_query = """
                    INSERT INTO employees
                    (user_id, department, designation, joining_date)
                    VALUES (%s, %s, %s, %s)
                """

                cursor.execute(
                    employee_query,
                    (
                        user_id,
                        department,
                        designation,
                        joining_date
                    )
                )

                # Save both records together
                connection.commit()

                print("\nEmployee account created successfully!")
                print("User ID:", user_id)
                print("Employee profile created successfully!")

            except Exception as e:
                connection.rollback()
                print("Error creating employee account:", e)

            finally:
                cursor.close()
                connection.close()

        else:
            print("Database connection failed.")
