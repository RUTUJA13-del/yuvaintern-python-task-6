
from db import get_db_connection
from werkzeug.security import generate_password_hash
from getpass import getpass

print("===== Create Manager Account =====")

full_name = input("Enter Manager Name: ").strip()
email = input("Enter Manager Email: ").strip().lower()
password = getpass("Create Manager Password: ")

if not full_name or not email or not password:
    print("All fields are required.")

elif len(password) < 8:
    print("Password must contain at least 8 characters.")

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
                full_name,
                email,
                hashed_password,
                "manager"
            )

            cursor.execute(query, values)
            connection.commit()

            print("Manager account created successfully!")

        except Exception as e:
            connection.rollback()
            print("Error creating Manager account:", e)

        finally:
            cursor.close()
            connection.close()
