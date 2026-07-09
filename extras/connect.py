import mysql.connector

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Ikjot123@",      # replace if your root password is different
        database="ETL_Project"
    )

    if conn.is_connected():
        print("Connected successfully!")
        print("Database:", conn.database)

except mysql.connector.Error as err:
    print("Error:", err)

finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()
        print("Connection closed.")