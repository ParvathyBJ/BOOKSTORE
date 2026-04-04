CREATE DATABASE IF NOT EXISTS bookstore_db;
USE bookstore_db;

CREATE TABLE CATEGORY (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE AUTHOR (
    author_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE BOOK (
    ISBN VARCHAR(20) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    category_id INT,
    FOREIGN KEY (category_id) REFERENCES CATEGORY(category_id) ON DELETE SET NULL
);

CREATE TABLE BOOK_AUTHOR (
    ISBN VARCHAR(20),
    author_id INT,
    PRIMARY KEY(ISBN, author_id),
    FOREIGN KEY (ISBN) REFERENCES BOOK(ISBN) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES AUTHOR(author_id) ON DELETE CASCADE
);

CREATE TABLE CUSTOMER (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE ORDER_ (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    order_date DATE NOT NULL,
    customer_id INT,
    FOREIGN KEY (customer_id) REFERENCES CUSTOMER(customer_id) ON DELETE CASCADE
);

CREATE TABLE ORDERITEM (
    order_id INT,
    ISBN VARCHAR(20),
    quantity INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    PRIMARY KEY(order_id, ISBN),
    FOREIGN KEY (order_id) REFERENCES ORDER_(order_id) ON DELETE CASCADE,
    FOREIGN KEY (ISBN) REFERENCES BOOK(ISBN) ON DELETE CASCADE
);

CREATE TABLE PAYMENT (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    order_id INT,
    FOREIGN KEY (order_id) REFERENCES ORDER_(order_id) ON DELETE CASCADE
);

CREATE TABLE SHIPPINGADDRESS (
    address_id INT PRIMARY KEY AUTO_INCREMENT,
    address TEXT NOT NULL,
    order_id INT,
    FOREIGN KEY (order_id) REFERENCES ORDER_(order_id) ON DELETE CASCADE
);

-- Insert sample data
INSERT INTO CATEGORY (name) VALUES ('Fiction'), ('Science Fiction'), ('Programming');
INSERT INTO AUTHOR (name) VALUES ('J.K. Rowling'), ('Isaac Asimov'), ('Guido van Rossum'), ('Robert C. Martin');

INSERT INTO BOOK (ISBN, title, price, category_id) VALUES 
('978-0439708180', 'Harry Potter', 549.00, 1),
('978-0553293357', 'Foundation', 640.00, 2),
('978-0131103627', 'Clean Code', 1299.00, 3),
('978-1593279288', 'Python Crash Course', 899.00, 3),
('978-0135957059', 'The Pragmatic Programmer', 1200.00, 3);

INSERT INTO BOOK_AUTHOR (ISBN, author_id) VALUES
('978-0439708180', 1),
('978-0553293357', 2),
('978-0131103627', 4),
('978-1593279288', 3),
('978-0135957059', 4);

INSERT INTO CUSTOMER (name, email) VALUES
('Alice Smith', 'alice@example.com'),
('Bob Jones', 'bob@example.com'),
('Charlie Brown', 'charlie@example.com');

-- Orders for Alice and Bob
INSERT INTO ORDER_ (order_date, customer_id) VALUES ('2023-10-01', 1), ('2023-10-05', 2);

-- Order Items
INSERT INTO ORDERITEM (order_id, ISBN, quantity, price) VALUES
(1, '978-0131103627', 1, 1299.00),
(2, '978-0553293357', 2, 1280.00);

-- Payment
INSERT INTO PAYMENT (amount, payment_method, order_id) VALUES
(1299.00, 'Cash on Delivery', 1),
(1280.00, 'Cash on Delivery', 2);

-- Shipping Address
INSERT INTO SHIPPINGADDRESS (address, order_id) VALUES
('Flat 42, Bangalore, India', 1),
('Building 301, Mumbai, India', 2);
