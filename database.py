
import sqlite3
import os
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "hotel.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_database():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            room_type TEXT NOT NULL,
            price REAL NOT NULL,
            status TEXT DEFAULT 'Available',
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'Booked',
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(room_id) REFERENCES rooms(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL,
            available TEXT DEFAULT 'Yes'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total REAL NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY(item_id) REFERENCES food_items(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            salary REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # SAMPLE ROOMS
    if cursor.execute("SELECT COUNT(*) FROM rooms").fetchone()[0] == 0:
        rooms = [
            ("101", "Standard", 1500, "Available", "Comfortable standard room"),
            ("102", "Standard", 1500, "Available", "Modern standard room"),
            ("201", "Deluxe", 2500, "Available", "Luxury deluxe room"),
            ("202", "Deluxe", 2500, "Available", "Deluxe room with city view"),
            ("301", "Suite", 4500, "Available", "Premium luxury suite"),
            ("302", "Suite", 4500, "Available", "Spacious premium suite"),
            ("401", "Family", 3500, "Available", "Family accommodation"),
            ("402", "Family", 3500, "Available", "Family room with extra space")
        ]

        cursor.executemany("""
            INSERT INTO rooms
            (room_number, room_type, price, status, description)
            VALUES (?, ?, ?, ?, ?)
        """, rooms)

    # SAMPLE CUSTOMERS
    if cursor.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
        customers = [
            ("Arun Kumar", "arun@gmail.com", "9876543210", "Chennai"),
            ("Priya Sharma", "priya@gmail.com", "9876543211", "Coimbatore"),
            ("Rahul Kumar", "rahul@gmail.com", "9876543212", "Bangalore"),
            ("Divya Raj", "divya@gmail.com", "9876543213", "Trichy"),
            ("Karthik S", "karthik@gmail.com", "9876543214", "Madurai")
        ]

        cursor.executemany("""
            INSERT INTO customers (name, email, phone, address)
            VALUES (?, ?, ?, ?)
        """, customers)

    # SAMPLE BOOKINGS
    if cursor.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 0:
        customers = cursor.execute(
            "SELECT id FROM customers ORDER BY id LIMIT 5"
        ).fetchall()

        rooms = cursor.execute(
            "SELECT id, price FROM rooms ORDER BY id LIMIT 5"
        ).fetchall()

        today = date.today()

        for i, (customer, room) in enumerate(zip(customers, rooms)):
            check_in = today - timedelta(days=i + 1)
            check_out = check_in + timedelta(days=2)

            cursor.execute("""
                INSERT INTO bookings
                (customer_id, room_id, check_in, check_out, total_amount, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                customer["id"],
                room["id"],
                check_in.isoformat(),
                check_out.isoformat(),
                room["price"] * 2,
                "Booked"
            ))

    # SAMPLE FOOD ITEMS
    if cursor.execute("SELECT COUNT(*) FROM food_items").fetchone()[0] == 0:
        food_items = [
            ("Chicken Biryani", "Main Course", 250, "Yes"),
            ("Veg Fried Rice", "Main Course", 180, "Yes"),
            ("Paneer Butter Masala", "Main Course", 220, "Yes"),
            ("Fresh Juice", "Beverages", 100, "Yes"),
            ("Chocolate Cake", "Dessert", 150, "Yes")
        ]

        cursor.executemany("""
            INSERT INTO food_items (name, category, price, available)
            VALUES (?, ?, ?, ?)
        """, food_items)

    # SAMPLE FOOD ORDERS
    if cursor.execute("SELECT COUNT(*) FROM food_orders").fetchone()[0] == 0:
        items = cursor.execute(
            "SELECT id, price FROM food_items ORDER BY id LIMIT 3"
        ).fetchall()

        for i, item in enumerate(items):
            cursor.execute("""
                INSERT INTO food_orders
                (customer_name, item_id, quantity, total, order_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ["Arun Kumar", "Priya Sharma", "Rahul Kumar"][i],
                item["id"],
                2,
                item["price"] * 2,
                date.today().isoformat(),
                "Completed"
            ))

    # SAMPLE STAFF
    if cursor.execute("SELECT COUNT(*) FROM staff").fetchone()[0] == 0:
        staff = [
            ("Ramesh", "Manager", "9876500001", "ramesh@luxestay.com", 30000),
            ("Suresh", "Receptionist", "9876500002", "suresh@luxestay.com", 18000),
            ("Meena", "Housekeeping", "9876500003", "meena@luxestay.com", 15000),
            ("Kumar", "Chef", "9876500004", "kumar@luxestay.com", 22000),
            ("Anitha", "Accountant", "9876500005", "anitha@luxestay.com", 25000)
        ]

        cursor.executemany("""
            INSERT INTO staff (name, role, phone, email, salary)
            VALUES (?, ?, ?, ?, ?)
        """, staff)

    # SAMPLE FEEDBACK
    if cursor.execute("SELECT COUNT(*) FROM feedback").fetchone()[0] == 0:
        feedback = [
            ("Arun Kumar", 5, "Excellent hotel and friendly staff."),
            ("Priya Sharma", 4, "Clean rooms and good service."),
            ("Rahul Kumar", 5, "Wonderful experience.")
        ]

        cursor.executemany("""
            INSERT INTO feedback (customer_name, rating, message)
            VALUES (?, ?, ?)
        """, feedback)

    conn.commit()
    conn.close()
