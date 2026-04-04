# Bookstore Management System

This is a full-stack Flask application integrating both MySQL for relational data and MongoDB for NoSQL review data.

## Requirements
- Python 3.8+
- MySQL Server (running on localhost:3306)
- MongoDB Server (running on localhost:27017)

## Setup Instructions

1. **Install Python Packages**
   ```bash
   pip install -r requirements.txt
   ```

2. **Database Initialization**
   - Ensure MySQL is running on your machine. Default connection uses `root` / `root`. You can edit `db_mysql.py` if your credentials differ.
   - Run the provided `schema.sql` file in your MySQL client to generate the database, tables, and seed data.
     ```bash
     mysql -u root -p < schema.sql
     ```
   - Ensure MongoDB is running on `localhost:27017`. It will automatically create the `bookstore_nosql` database and `reviews` collection upon first insertion.

3. **Start the Application**
   ```bash
   python app.py
   ```

4. **Using the Application**
   - **Frontend:** Go to `http://localhost:5000/`
   - **Admin Panel:** Go to `http://localhost:5000/admin`
   - **Admin Credentials:** `admin` / `admin123`
