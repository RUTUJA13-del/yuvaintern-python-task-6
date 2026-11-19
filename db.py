
import mysql.connector
from mysql.connector import Error

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="admin21",
            database="employee_tracker",
            port=3306
        )

        if connection.is_connected():
            print("MySQL Database Connected Successfully!")
            return connection

    except Error as e:
        print("Error connecting to MySQL:", e)

    return None


if __name__ == "__main__":
    connection = get_db_connection()

    if connection:
        connection.close()
        print("Database connection closed.")
