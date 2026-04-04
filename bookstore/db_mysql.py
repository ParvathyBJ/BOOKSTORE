import mysql.connector

def get_mysql_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Parvathy",
        database="bookstore_db"
    )
