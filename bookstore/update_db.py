import db_mysql

def migrate():
    conn = db_mysql.get_mysql_connection()
    cursor = conn.cursor()
    
    try:
        print("Adding stock column to BOOK table...")
        cursor.execute("ALTER TABLE BOOK ADD COLUMN stock INT NOT NULL DEFAULT 10")
        print("Success.")
    except Exception as e:
        print("Skipped or error adding stock column:", e)
        
    try:
        print("Creating trigger update_stock_after_order...")
        cursor.execute("DROP TRIGGER IF EXISTS update_stock_after_order")
        cursor.execute("""
            CREATE TRIGGER update_stock_after_order
            AFTER INSERT ON ORDERITEM
            FOR EACH ROW
            BEGIN
                UPDATE BOOK SET stock = stock - NEW.quantity WHERE ISBN = NEW.ISBN;
            END
        """)
        print("Success.")
    except Exception as e:
        print("Error creating trigger:", e)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
