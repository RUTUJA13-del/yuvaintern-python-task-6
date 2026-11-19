
from db import get_db_connection
from werkzeug.security import generate_password_hash
from getpass import getpass

print("===== Create Admin Account =====")

full_name = input("Enter Admin Name: ")
email = input("Enter Admin Email: ")
password = getpass("Create Admin Password: ")

if not full_name.strip() or not email.strip() or not password:
    print("All fields are required.")
else:
    connection = get_db_connection()

    if connection:
        cursor = connection.cursor()

        try:
            hashed_password = generate_password_hash(password)

            query = """
            INSERT INTO users
            (full_name, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            """

            values = (
                full_name.strip(),
                email.strip().lower(),
                hashed_password,
                "admin"
            )

            cursor.execute(query, values)
            connection.commit()

            print("Admin account created successfully!")

        except Exception as e:
            connection.rollback()
            print("Error:", e)

        finally:
            cursor.close()
            connection.close()
