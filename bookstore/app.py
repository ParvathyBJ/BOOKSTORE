from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import db_mysql
import db_mongo

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

@app.route('/')
def home():
    category_filter = request.args.get('category_id')
    search_query = request.args.get('search')
    
    conn = db_mysql.get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT b.ISBN, b.title, b.price, c.name as category_name, 
        GROUP_CONCAT(a.name SEPARATOR ', ') as author_names
        FROM BOOK b
        LEFT JOIN CATEGORY c ON b.category_id = c.category_id
        LEFT JOIN BOOK_AUTHOR ba ON b.ISBN = ba.ISBN
        LEFT JOIN AUTHOR a ON ba.author_id = a.author_id
        WHERE 1=1
    """
    params = []
    if category_filter:
        query += " AND b.category_id = %s"
        params.append(category_filter)
    if search_query:
        query += " AND b.title LIKE %s"
        params.append(f"%{search_query}%")
        
    query += " GROUP BY b.ISBN"
    
    cursor.execute(query, params)
    books = cursor.fetchall()
    
    cursor.execute("SELECT * FROM CATEGORY")
    categories = cursor.fetchall()
    
    conn.close()
    return render_template('index.html', books=books, categories=categories)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        conn = db_mysql.get_mysql_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO CUSTOMER (name, email) VALUES (%s, %s)", (name, email))
            conn.commit()
            session['customer_id'] = cursor.lastrowid
            session['customer_name'] = name
            flash("Registered successfully!")
            return redirect(url_for('home'))
        except Exception as e:
            conn.rollback()
            flash("Error: Email might already exist.")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        conn = db_mysql.get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM CUSTOMER WHERE email = %s", (email,))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['customer_id'] = user['customer_id']
            session['customer_name'] = user['name']
            flash("Logged in successfully!")
            return redirect(url_for('home'))
        else:
            flash("Email not found. Please register.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('customer_id', None)
    session.pop('customer_name', None)
    flash("Logged out.")
    return redirect(url_for('home'))

@app.route('/book/<isbn>', methods=['GET', 'POST'])
def book_detail(isbn):
    conn = db_mysql.get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.ISBN, b.title, b.price, c.name as category_name
        FROM BOOK b
        LEFT JOIN CATEGORY c ON b.category_id = c.category_id
        WHERE b.ISBN = %s
    """, (isbn,))
    book = cursor.fetchone()
    if not book:
        return "Book not found", 404

    cursor.execute("""
        SELECT a.name FROM AUTHOR a
        JOIN BOOK_AUTHOR ba ON a.author_id = ba.author_id
        WHERE ba.ISBN = %s
    """, (isbn,))
    authors = cursor.fetchall()
    
    conn.close()

    reviews_col = db_mongo.get_mongo_collection()
    
    if request.method == 'POST':
        if 'customer_id' not in session:
            return redirect(url_for('login'))
        rating = int(request.form['rating'])
        review_text = request.form['review_text']
        reviews_col.insert_one({
            "customer_id": session['customer_id'],
            "customer_name": session['customer_name'],
            "ISBN": isbn,
            "book_title": book['title'],
            "rating": rating,
            "review_text": review_text,
            "created_at": datetime.now()
        })
        flash("Review added successfully!")
        return redirect(url_for('book_detail', isbn=isbn))

    reviews = list(reviews_col.find({"ISBN": isbn}).sort("created_at", -1))
    avg_rating = sum([r['rating'] for r in reviews]) / len(reviews) if reviews else 0

    return render_template('book_detail.html', book=book, authors=authors, reviews=reviews, avg_rating=round(avg_rating, 1))

@app.route('/cart', methods=['GET'])
def view_cart():
    if 'customer_id' not in session:
        return redirect(url_for('login'))
        
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    
    if cart:
        conn = db_mysql.get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        format_strings = ','.join(['%s'] * len(cart))
        cursor.execute(f"SELECT ISBN, title, price FROM BOOK WHERE ISBN IN ({format_strings})", tuple(cart.keys()))
        books = cursor.fetchall()
        conn.close()
        
        for b in books:
            qty = cart[b['ISBN']]
            subtotal = float(b['price']) * qty
            total += subtotal
            b['quantity'] = qty
            b['subtotal'] = subtotal
            cart_items.append(b)
            
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/cart/add/<isbn>', methods=['POST'])
def add_to_cart(isbn):
    if 'customer_id' not in session:
        return redirect(url_for('login'))
        
    cart = session.get('cart', {})
    qty = int(request.form.get('quantity', 1))
    cart[isbn] = cart.get(isbn, 0) + qty
    session['cart'] = cart
    flash("Added to cart!")
    return redirect(request.referrer or url_for('home'))

@app.route('/cart/remove/<isbn>', methods=['POST'])
def remove_from_cart(isbn):
    if 'customer_id' not in session:
        return redirect(url_for('login'))
        
    cart = session.get('cart', {})
    if isbn in cart:
        del cart[isbn]
        session['cart'] = cart
        flash("Item removed from cart.")
    return redirect(url_for('view_cart'))

@app.route('/cart/update/<isbn>', methods=['POST'])
def update_cart(isbn):
    if 'customer_id' not in session:
        return redirect(url_for('login'))
        
    cart = session.get('cart', {})
    if isbn in cart:
        try:
            qty = int(request.form.get('quantity', 1))
            if qty > 0:
                cart[isbn] = qty
                session['cart'] = cart
                flash("Cart updated.")
            else:
                del cart[isbn]
                session['cart'] = cart
                flash("Item removed from cart.")
        except ValueError:
            pass
    return redirect(url_for('view_cart'))

@app.route('/order', methods=['GET', 'POST'])
def order():
    if 'customer_id' not in session:
        return redirect(url_for('login'))
        
    cart = session.get('cart', {})
    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for('view_cart'))
        
    conn = db_mysql.get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    
    format_strings = ','.join(['%s'] * len(cart))
    cursor.execute(f"SELECT ISBN, title, price FROM BOOK WHERE ISBN IN ({format_strings})", tuple(cart.keys()))
    books = cursor.fetchall()
    
    total_amount = sum(float(b['price']) * cart[b['ISBN']] for b in books)
    
    if request.method == 'POST':
        address = request.form['address']
        payment_method = 'Cash on Delivery'
        
        try:
            cursor.execute("INSERT INTO ORDER_ (order_date, customer_id) VALUES (CURDATE(), %s)", (session['customer_id'],))
            order_id = cursor.lastrowid
            
            for b in books:
                cursor.execute("INSERT INTO ORDERITEM (order_id, ISBN, quantity, price) VALUES (%s, %s, %s, %s)",
                               (order_id, b['ISBN'], cart[b['ISBN']], float(b['price'])))
                               
            cursor.execute("INSERT INTO PAYMENT (amount, payment_method, order_id) VALUES (%s, %s, %s)",
                           (total_amount, payment_method, order_id))
                           
            cursor.execute("INSERT INTO SHIPPINGADDRESS (address, order_id) VALUES (%s, %s)",
                           (address, order_id))
                           
            conn.commit()
            session.pop('cart', None)
            flash(f"Order ORD-{order_id:05d} placed successfully using Cash on Delivery!")
            return redirect(url_for('my_orders'))
        except Exception as e:
            conn.rollback()
            flash("Error placing order.")
            print(e)
        finally:
            conn.close()
            
    conn.close()
    return render_template('order.html', books=books, cart=cart, total_amount=total_amount)

@app.route('/my-orders')
def my_orders():
    if 'customer_id' not in session:
        return redirect(url_for('login'))
        
    conn = db_mysql.get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT o.order_id, o.order_date, p.payment_method, p.amount, s.address
        FROM ORDER_ o
        LEFT JOIN PAYMENT p ON o.order_id = p.order_id
        LEFT JOIN SHIPPINGADDRESS s ON o.order_id = s.order_id
        WHERE o.customer_id = %s
        ORDER BY o.order_id DESC
    """, (session['customer_id'],))
    orders = cursor.fetchall()
    
    for o in orders:
        cursor.execute("""
            SELECT i.quantity, i.price, b.title
            FROM ORDERITEM i
            JOIN BOOK b ON i.ISBN = b.ISBN
            WHERE i.order_id = %s
        """, (o['order_id'],))
        o['items'] = cursor.fetchall()
        
    conn.close()
    return render_template('my_orders.html', orders=orders)

# ADMIN ROUTES
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Invalid admin credentials")
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    conn = db_mysql.get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM BOOK")
    total_books = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM CUSTOMER")
    total_customers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM ORDER_")
    total_orders = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(amount) FROM PAYMENT")
    res = cursor.fetchone()
    total_revenue = res[0] if res and res[0] else 0
    conn.close()
    
    return render_template('admin/dashboard.html', 
                           books=total_books, customers=total_customers, 
                           orders=total_orders, revenue=total_revenue)

@app.route('/admin/books', methods=['GET', 'POST'])
def admin_books():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    conn = db_mysql.get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        action = request.form['action']
        if action == 'add':
            isbn = request.form['isbn']
            title = request.form['title']
            price = request.form['price']
            category_id = request.form['category_id']
            author_ids = request.form.getlist('author_ids')
            
            try:
                cursor.execute("INSERT INTO BOOK (ISBN, title, price, category_id) VALUES (%s, %s, %s, %s)",
                               (isbn, title, price, category_id))
                for aid in author_ids:
                    cursor.execute("INSERT INTO BOOK_AUTHOR (ISBN, author_id) VALUES (%s, %s)", (isbn, aid))
                conn.commit()
                flash("Book added.")
            except Exception as e:
                conn.rollback()
                flash("Error adding book: " + str(e))
        elif action == 'delete':
            isbn = request.form['isbn']
            try:
                cursor.execute("DELETE FROM BOOK WHERE ISBN = %s", (isbn,))
                conn.commit()
                flash("Book deleted.")
            except Exception as e:
                conn.rollback()
                flash("Error deleting book: " + str(e))
    
    cursor.execute("""
        SELECT b.ISBN, b.title, b.price, c.name as category_name
        FROM BOOK b LEFT JOIN CATEGORY c ON b.category_id = c.category_id
    """)
    books = cursor.fetchall()
    cursor.execute("SELECT * FROM CATEGORY")
    categories = cursor.fetchall()
    cursor.execute("SELECT * FROM AUTHOR")
    authors = cursor.fetchall()
    
    conn.close()
    return render_template('admin/books.html', books=books, categories=categories, authors=authors)

@app.route('/admin/books/edit/<isbn>', methods=['GET', 'POST'])
def admin_books_edit(isbn):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    conn = db_mysql.get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        title = request.form['title']
        price = request.form['price']
        category_id = request.form['category_id']
        author_ids = request.form.getlist('author_ids')
        
        try:
            cursor.execute("UPDATE BOOK SET title = %s, price = %s, category_id = %s WHERE ISBN = %s",
                           (title, price, category_id, isbn))
            cursor.execute("DELETE FROM BOOK_AUTHOR WHERE ISBN = %s", (isbn,))
            for aid in author_ids:
                cursor.execute("INSERT INTO BOOK_AUTHOR (ISBN, author_id) VALUES (%s, %s)", (isbn, aid))
            conn.commit()
            flash("Book updated successfully.")
            return redirect(url_for('admin_books'))
        except Exception as e:
            conn.rollback()
            flash("Error updating book: " + str(e))
            
    cursor.execute("SELECT * FROM BOOK WHERE ISBN = %s", (isbn,))
    book = cursor.fetchone()
    
    if not book:
        conn.close()
        flash("Book not found")
        return redirect(url_for('admin_books'))
    
    cursor.execute("SELECT author_id FROM BOOK_AUTHOR WHERE ISBN = %s", (isbn,))
    book_authors = [row['author_id'] for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM CATEGORY")
    categories = cursor.fetchall()
    
    cursor.execute("SELECT * FROM AUTHOR")
    authors = cursor.fetchall()
    
    conn.close()
    return render_template('admin/book_edit.html', book=book, book_authors=book_authors, categories=categories, authors=authors)

@app.route('/admin/categories', methods=['GET', 'POST'])
def admin_categories():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    conn = db_mysql.get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        if action == 'add':
            name = request.form['name']
            try:
                cursor.execute("INSERT INTO CATEGORY (name) VALUES (%s)", (name,))
                conn.commit()
                flash("Category added.")
            except Exception as e:
                conn.rollback()
                flash("Error: " + str(e))
        elif action == 'delete':
            category_id = request.form['category_id']
            try:
                cursor.execute("DELETE FROM CATEGORY WHERE category_id = %s", (category_id,))
                conn.commit()
                flash("Category deleted.")
            except Exception as e:
                conn.rollback()
                flash("Error: " + str(e))
    cursor.execute("SELECT * FROM CATEGORY")
    cats = cursor.fetchall()
    conn.close()
    return render_template('admin/categories.html', categories=cats)

@app.route('/admin/authors', methods=['GET', 'POST'])
def admin_authors():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    conn = db_mysql.get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        if action == 'add':
            name = request.form['name']
            try:
                cursor.execute("INSERT INTO AUTHOR (name) VALUES (%s)", (name,))
                conn.commit()
                flash("Author added.")
            except Exception as e:
                conn.rollback()
                flash("Error: " + str(e))
        elif action == 'delete':
            author_id = request.form['author_id']
            try:
                cursor.execute("DELETE FROM AUTHOR WHERE author_id = %s", (author_id,))
                conn.commit()
                flash("Author deleted.")
            except Exception as e:
                conn.rollback()
                flash("Error: " + str(e))
    cursor.execute("SELECT * FROM AUTHOR")
    auths = cursor.fetchall()
    conn.close()
    return render_template('admin/authors.html', authors=auths)

@app.route('/admin/orders')
def admin_orders():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    conn = db_mysql.get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.order_id, o.order_date, c.name as customer_name, p.amount, p.payment_method, s.address
        FROM ORDER_ o
        LEFT JOIN CUSTOMER c ON o.customer_id = c.customer_id
        LEFT JOIN PAYMENT p ON o.order_id = p.order_id
        LEFT JOIN SHIPPINGADDRESS s ON o.order_id = s.order_id
        ORDER BY o.order_id DESC
    """)
    orders = cursor.fetchall()
    conn.close()
    return render_template('admin/orders.html', orders=orders)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
