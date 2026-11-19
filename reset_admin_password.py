
from db import get_db_connection
from werkzeug.security import generate_password_hash
from getpass import getpass

print("===== Reset Admin Password =====")

email = input("Enter your Admin email: ").strip().lower()
new_password = getpass("Enter your new password: ")
confirm_password = getpass("Confirm your new password: ")

if not email or not new_password:
    print("All fields are required.")

elif new_password != confirm_password:
    print("Passwords do not match.")

elif len(new_password) < 8:
    print("Password must contain at least 8 characters.")

else:
    connection = get_db_connection()

    if connection:
        cursor = connection.cursor()

        try:
            hashed_password = generate_password_hash(new_password)

            query = """
            UPDATE users
            SET password_hash = %s
            WHERE email = %s AND role = 'admin'
            """

            cursor.execute(query, (hashed_password, email))
            connection.commit()

            if cursor.rowcount == 1:
                print("Admin password reset successfully!")
            else:
                print("Admin account not found. Check your email.")

        except Exception as e:
            connection.rollback()
            print("Error:", e)

        finally:
            cursor.close()
            connection.close()