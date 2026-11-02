
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from database import create_database, get_db
import os

app = Flask(__name__)

# APP CONFIGURATION
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "LuxeStay-Development-Secret-Key-Change-Before-Deployment"
)

app.config["SESSION_PERMANENT"] = False

# DATABASE SETUP
create_database()


# ADMIN LOGIN REQUIRED
def login_required(route):
    @wraps(route)
    def wrapper(*args, **kwargs):
        if "admin" not in session:
            flash("Please login to continue.", "error")
            return redirect(url_for("login"))
        return route(*args, **kwargs)
    return wrapper


# CREATE DEFAULT ADMIN
def create_admin():
    conn = get_db()

    admin = conn.execute(
        "SELECT * FROM admins WHERE username = ?",
        ("admin",)
    ).fetchone()

    if not admin:
        password = generate_password_hash("Admin@123")

        conn.execute(
            "INSERT INTO admins (username, password) VALUES (?, ?)",
            ("admin", password)
        )
        conn.commit()

    conn.close()


create_admin()


# HOME - ALWAYS OPEN LOGIN FIRST
@app.route("/")
def home():
    if "admin" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():

    # Already logged-in admin
    if request.method == "GET" and "admin" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()

        admin = conn.execute(
            "SELECT * FROM admins WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if admin and check_password_hash(admin["password"], password):

            session.clear()
            session["admin"] = username

            flash("Welcome to LuxeStay!", "success")

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out successfully.", "success")
    return redirect(url_for("login"))


# DASHBOARD
@app.route("/dashboard")
@login_required
def dashboard():

    conn = get_db()

    rooms = conn.execute(
        "SELECT COUNT(*) FROM rooms"
    ).fetchone()[0]

    customers = conn.execute(
        "SELECT COUNT(*) FROM customers"
    ).fetchone()[0]

    bookings = conn.execute(
        "SELECT COUNT(*) FROM bookings"
    ).fetchone()[0]

    revenue = conn.execute("""
        SELECT COALESCE(SUM(total_amount), 0)
        FROM bookings
        WHERE status IN ('Booked', 'Checked-in', 'Completed')
    """).fetchone()[0]

    recent = conn.execute("""
        SELECT b.id,
               c.name AS customer_name,
               r.room_number,
               b.check_in,
               b.check_out,
               b.status
        FROM bookings b
        JOIN customers c ON b.customer_id = c.id
        JOIN rooms r ON b.room_id = r.id
        ORDER BY b.id DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        rooms=rooms,
        customers=customers,
        bookings=bookings,
        revenue=revenue,
        recent=recent
    )


# ROOM MANAGEMENT
@app.route("/rooms", methods=["GET", "POST"])
@login_required
def rooms():

    conn = get_db()

    if request.method == "POST":

        try:
            conn.execute("""
                INSERT INTO rooms
                (room_number, room_type, price, status, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                request.form["room_number"].strip(),
                request.form["room_type"],
                float(request.form["price"]),
                "Available",
                request.form.get("description", "")
            ))

            conn.commit()
            flash("Room added successfully.", "success")

        except (ValueError, KeyError):
            flash("Please enter valid room details.", "error")

        except Exception:
            flash("Room number may already exist.", "error")

        conn.close()
        return redirect(url_for("rooms"))

    room_list = conn.execute(
        "SELECT * FROM rooms ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template("rooms.html", rooms=room_list)


@app.route("/rooms/delete/<int:id>")
@login_required
def delete_room(id):

    conn = get_db()

    try:
        conn.execute(
            "DELETE FROM rooms WHERE id = ?",
            (id,)
        )

        conn.commit()
        flash("Room deleted successfully.", "success")

    except Exception:
        flash("Room cannot be deleted because it has bookings.", "error")

    conn.close()

    return redirect(url_for("rooms"))


# CUSTOMER MANAGEMENT
@app.route("/customers", methods=["GET", "POST"])
@login_required
def customers():

    conn = get_db()

    if request.method == "POST":

        conn.execute("""
            INSERT INTO customers
            (name, email, phone, address)
            VALUES (?, ?, ?, ?)
        """, (
            request.form["name"].strip(),
            request.form.get("email", ""),
            request.form.get("phone", ""),
            request.form.get("address", "")
        ))

        conn.commit()
        conn.close()

        flash("Customer added successfully.", "success")

        return redirect(url_for("customers"))

    customer_list = conn.execute(
        "SELECT * FROM customers ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "customers.html",
        customers=customer_list
    )


@app.route("/customers/delete/<int:id>")
@login_required
def delete_customer(id):

    conn = get_db()

    try:
        conn.execute(
            "DELETE FROM customers WHERE id = ?",
            (id,)
        )

        conn.commit()
        flash("Customer deleted successfully.", "success")

    except Exception:
        flash("Customer has existing bookings.", "error")

    conn.close()

    return redirect(url_for("customers"))


# BOOKING MANAGEMENT
@app.route("/bookings", methods=["GET", "POST"])
@login_required
def bookings():

    conn = get_db()

    if request.method == "POST":

        try:
            customer_id = int(request.form["customer_id"])
            room_id = int(request.form["room_id"])

            check_in = request.form["check_in"]
            check_out = request.form["check_out"]

            amount = float(request.form["total_amount"])

            start = datetime.strptime(
                check_in, "%Y-%m-%d"
            ).date()

            end = datetime.strptime(
                check_out, "%Y-%m-%d"
            ).date()

            if end <= start or amount < 0:
                raise ValueError()

            customer = conn.execute(
                "SELECT id FROM customers WHERE id = ?",
                (customer_id,)
            ).fetchone()

            room = conn.execute(
                "SELECT * FROM rooms WHERE id = ? AND status = 'Available'",
                (room_id,)
            ).fetchone()

            if not customer:
                flash("Please select a valid customer.", "error")

            elif not room:
                flash("Room is not available.", "error")

            else:

                conflict = conn.execute("""
                    SELECT id FROM bookings
                    WHERE room_id = ?
                    AND status IN ('Booked', 'Checked-in')
                    AND check_in < ?
                    AND check_out > ?
                """, (
                    room_id,
                    check_out,
                    check_in
                )).fetchone()

                if conflict:

                    flash(
                        "Room is already booked for these dates.",
                        "error"
                    )

                else:

                    conn.execute("""
                        INSERT INTO bookings
                        (customer_id, room_id, check_in, check_out, total_amount)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        customer_id,
                        room_id,
                        check_in,
                        check_out,
                        amount
                    ))

                    conn.commit()

                    flash("Booking created successfully.", "success")

        except (ValueError, KeyError):
            flash("Please enter valid booking details.", "error")

        conn.close()

        return redirect(url_for("bookings"))

    customer_list = conn.execute(
        "SELECT * FROM customers ORDER BY name"
    ).fetchall()

    room_list = conn.execute(
        "SELECT * FROM rooms WHERE status = 'Available'"
    ).fetchall()

    booking_list = conn.execute("""
        SELECT b.*,
               c.name AS customer_name,
               r.room_number,
               r.room_type
        FROM bookings b
        JOIN customers c ON b.customer_id = c.id
        JOIN rooms r ON b.room_id = r.id
        ORDER BY b.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "bookings.html",
        customers=customer_list,
        rooms=room_list,
        bookings=booking_list
    )


@app.route("/bookings/status/<int:id>/<status>")
@login_required
def update_booking(id, status):

    allowed = [
        "Booked",
        "Checked-in",
        "Completed",
        "Cancelled"
    ]

    if status not in allowed:
        flash("Invalid booking status.", "error")
        return redirect(url_for("bookings"))

    conn = get_db()

    conn.execute(
        "UPDATE bookings SET status = ? WHERE id = ?",
        (status, id)
    )

    conn.commit()
    conn.close()

    flash("Booking status updated.", "success")

    return redirect(url_for("bookings"))


# RESTAURANT MANAGEMENT
@app.route("/restaurant", methods=["GET", "POST"])
@login_required
def restaurant():

    conn = get_db()

    if request.method == "POST":

        try:
            conn.execute("""
                INSERT INTO food_items
                (name, category, price)
                VALUES (?, ?, ?)
            """, (
                request.form["name"].strip(),
                request.form.get("category", ""),
                float(request.form["price"])
            ))

            conn.commit()

            flash("Food item added successfully.", "success")

        except (ValueError, KeyError):
            flash("Enter valid food details.", "error")

        conn.close()

        return redirect(url_for("restaurant"))

    items = conn.execute(
        "SELECT * FROM food_items ORDER BY id DESC"
    ).fetchall()

    orders = conn.execute("""
        SELECT o.*,
               f.name AS food_name
        FROM food_orders o
        JOIN food_items f ON o.item_id = f.id
        ORDER BY o.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "restaurant.html",
        items=items,
        orders=orders
    )


@app.route("/restaurant/order", methods=["POST"])
@login_required
def add_order():

    conn = get_db()

    try:
        item_id = int(request.form["item_id"])
        quantity = int(request.form["quantity"])

        item = conn.execute("""
            SELECT * FROM food_items
            WHERE id = ? AND available = 'Yes'
        """, (item_id,)).fetchone()

        if not item or quantity < 1:

            flash("Invalid food item or quantity.", "error")

        else:

            total = item["price"] * quantity

            conn.execute("""
                INSERT INTO food_orders
                (customer_name, item_id, quantity, total, order_date)
                VALUES (?, ?, ?, ?, ?)
            """, (
                request.form["customer_name"].strip(),
                item_id,
                quantity,
                total,
                datetime.now().strftime("%Y-%m-%d")
            ))

            conn.commit()

            flash("Food order created successfully.", "success")

    except (ValueError, KeyError):
        flash("Enter valid order details.", "error")

    conn.close()

    return redirect(url_for("restaurant"))


# STAFF MANAGEMENT
@app.route("/staff", methods=["GET", "POST"])
@login_required
def staff():

    conn = get_db()

    if request.method == "POST":

        try:
            conn.execute("""
                INSERT INTO staff
                (name, role, phone, email, salary)
                VALUES (?, ?, ?, ?, ?)
            """, (
                request.form["name"].strip(),
                request.form["role"],
                request.form.get("phone", ""),
                request.form.get("email", ""),
                float(request.form.get("salary") or 0)
            ))

            conn.commit()

            flash("Staff member added successfully.", "success")

        except (ValueError, KeyError):
            flash("Enter valid staff details.", "error")

        conn.close()

        return redirect(url_for("staff"))

    staff_list = conn.execute(
        "SELECT * FROM staff ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "staff.html",
        staff=staff_list
    )


@app.route("/staff/delete/<int:id>")
@login_required
def delete_staff(id):

    conn = get_db()

    conn.execute(
        "DELETE FROM staff WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    flash("Staff member deleted successfully.", "success")

    return redirect(url_for("staff"))


# REPORTS AND FEEDBACK
@app.route("/reports", methods=["GET", "POST"])
@login_required
def reports():

    conn = get_db()

    if request.method == "POST":

        try:
            rating = int(request.form["rating"])

            if rating < 1 or rating > 5:
                raise ValueError()

            conn.execute("""
                INSERT INTO feedback
                (customer_name, rating, message)
                VALUES (?, ?, ?)
            """, (
                request.form["customer_name"].strip(),
                rating,
                request.form.get("message", "")
            ))

            conn.commit()

            flash("Feedback added successfully.", "success")

        except (ValueError, KeyError):
            flash("Enter a rating between 1 and 5.", "error")

        conn.close()

        return redirect(url_for("reports"))

    total_revenue = conn.execute("""
        SELECT COALESCE(SUM(total_amount), 0)
        FROM bookings
        WHERE status IN ('Booked', 'Checked-in', 'Completed')
    """).fetchone()[0]

    feedback_list = conn.execute(
        "SELECT * FROM feedback ORDER BY id DESC"
    ).fetchall()

    total_orders = conn.execute(
        "SELECT COUNT(*) FROM food_orders"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "reports.html",
        revenue=total_revenue,
        feedback=feedback_list,
        total_orders=total_orders
    )


# RUN APPLICATION
if __name__ == "__main__":
    app.run(debug=True)
