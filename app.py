# app.py - Main Flask application for Favourite Books Online Bookstore
# SWE30003 Group 4
# Coding standard: PEP 8 - https://peps.python.org/pep-0008/

import re
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash

from models.database import Database
from models.account import Account, Customer
from models.catalogue import Catalogue, Product
from models.cart import ShoppingCart
from models.order import Order, CheckoutFacade
from models.report import SalesReport

app = Flask(__name__)
app.secret_key = "favouritebooks-secret-2026"


def bootstrap():
    # sets up db tables and seeds data on first run
    db = Database()
    db.initialise_schema()
    db.seed_data()


# decorators to protect routes

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "account_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def customer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "customer":
            flash("This page is for customers only.", "warning")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "account_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Administrator access required.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


# basic input validation helpers

def is_valid_email(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def is_strong_password(pw):
    # must be 8+ chars, have uppercase, number and special char
    if len(pw) < 8:
        return False
    if not re.search(r"[A-Z]", pw):
        return False
    if not re.search(r"\d", pw):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", pw):
        return False
    return True


# public routes

@app.route("/")
def index():
    cat = Catalogue()
    featured = cat.get_all_available()[:6]
    categories = cat.get_all_categories()
    return render_template("index.html", featured=featured, categories=categories)


@app.route("/catalogue")
def catalogue():
    cat = Catalogue()
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    if query:
        books = cat.search(query)
    elif category:
        books = cat.get_by_category(category)
    else:
        books = cat.get_all_available()

    categories = cat.get_all_categories()
    return render_template("catalogue.html", books=books, categories=categories,
                           query=query, selected_category=category)


@app.route("/book/<int:book_id>")
def book_detail(book_id):
    product = Product.get_by_id(book_id)
    if not product or not product.available:
        flash("Book not found.", "danger")
        return redirect(url_for("catalogue"))
    return render_template("book_detail.html", book=product)


# auth routes

@app.route("/register", methods=["GET", "POST"])
def register():
    if "account_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        errors = []
        if not name or len(name) < 2:
            errors.append("Name must be at least 2 characters.")
        if not is_valid_email(email):
            errors.append("Please enter a valid email address.")
        if not is_strong_password(password):
            errors.append("Password must be 8+ characters with at least one uppercase letter, number, and special character.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("register.html", form_data=request.form)

        acc_id = Customer.register(name, email, password, phone, address)
        if acc_id is None:
            flash("An account with this email already exists.", "danger")
            return render_template("register.html", form_data=request.form)

        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form_data={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if "account_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html")

        acc = Account.authenticate(email, password)
        if acc:
            session["account_id"] = acc["id"]
            session["name"] = acc["name"]
            session["role"] = acc["role"]
            flash(f"Welcome back, {acc['name']}!", "success")
            if acc["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# cart routes

@app.route("/cart")
@login_required
@customer_required
def cart():
    c = ShoppingCart.get_for_account(session["account_id"])
    items = c.get_items() if c else []
    total = c.get_total() if c else 0
    return render_template("cart.html", items=items, total=total)


@app.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
@customer_required
def add_to_cart(product_id):
    qty = int(request.form.get("quantity", 1))
    if qty < 1:
        flash("Quantity must be at least 1.", "danger")
        return redirect(request.referrer or url_for("catalogue"))

    c = ShoppingCart.get_for_account(session["account_id"])
    err = c.add_item(product_id, qty)
    if err:
        flash(err, "danger")
    else:
        flash("Book added to your cart.", "success")
    return redirect(request.referrer or url_for("catalogue"))


@app.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required
@customer_required
def update_cart_item(item_id):
    qty = int(request.form.get("quantity", 1))
    c = ShoppingCart.get_for_account(session["account_id"])
    c.update_item_quantity(item_id, qty)
    flash("Cart updated.", "success")
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
@customer_required
def remove_from_cart(item_id):
    c = ShoppingCart.get_for_account(session["account_id"])
    c.remove_item(item_id)
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart"))


# checkout routes

@app.route("/checkout", methods=["GET", "POST"])
@login_required
@customer_required
def checkout():
    c = ShoppingCart.get_for_account(session["account_id"])
    if not c or c.is_empty():
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart"))

    acc = Account.get_by_id(session["account_id"])
    items = c.get_items()
    total = c.get_total()

    if request.method == "POST":
        shipping_address = request.form.get("shipping_address", "").strip()
        card_number = request.form.get("card_number", "").strip().replace(" ", "")
        card_name = request.form.get("card_name", "").strip()
        expiry = request.form.get("expiry", "").strip()
        cvv = request.form.get("cvv", "").strip()

        errors = []
        if len(shipping_address) < 5:
            errors.append("Please enter a valid shipping address.")
        if not re.match(r"^\d{16}$", card_number):
            errors.append("Card number must be 16 digits.")
        if not card_name or len(card_name) < 2:
            errors.append("Please enter the cardholder name.")
        if not re.match(r"^(0[1-9]|1[0-2])\/\d{2}$", expiry):
            errors.append("Expiry must be in MM/YY format.")
        if not re.match(r"^\d{3,4}$", cvv):
            errors.append("CVV must be 3 or 4 digits.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("checkout.html", items=items, total=total, account=acc)

        payment_info = {"card_number": card_number, "card_name": card_name}
        facade = CheckoutFacade(c, session["account_id"])
        success, msg, order_id = facade.checkout(shipping_address, payment_info)

        if success:
            flash(msg, "success")
            return redirect(url_for("order_confirmation", order_id=order_id))
        else:
            flash(msg, "danger")

    return render_template("checkout.html", items=items, total=total, account=acc)


@app.route("/order/confirmation/<int:order_id>")
@login_required
@customer_required
def order_confirmation(order_id):
    order = Order.get_by_id(order_id)
    if not order or order.account_id != session["account_id"]:
        flash("Order not found.", "danger")
        return redirect(url_for("index"))
    items = order.get_items()
    return render_template("order_confirmation.html", order=order, items=items)


@app.route("/orders")
@login_required
@customer_required
def my_orders():
    orders = Order.get_for_account(session["account_id"])
    return render_template("my_orders.html", orders=orders)


@app.route("/order/<int:order_id>")
@login_required
@customer_required
def order_detail(order_id):
    order = Order.get_by_id(order_id)
    if not order or order.account_id != session["account_id"]:
        flash("Order not found.", "danger")
        return redirect(url_for("my_orders"))
    items = order.get_items()
    return render_template("order_detail.html", order=order, items=items)


# admin routes

@app.route("/admin")
@admin_required
def admin_dashboard():
    cat = Catalogue()
    books = cat.get_all_for_admin()
    orders = Order.get_all()
    report = SalesReport()
    summary = report.get_summary("all")
    return render_template("admin/dashboard.html", books=books, orders=orders, summary=summary)


@app.route("/admin/books")
@admin_required
def admin_books():
    cat = Catalogue()
    books = cat.get_all_for_admin()
    return render_template("admin/manage_books.html", books=books)


@app.route("/admin/books/add", methods=["GET", "POST"])
@admin_required
def admin_add_book():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        isbn = request.form.get("isbn", "").strip()
        price = request.form.get("price", "")
        stock = request.form.get("stock", "")
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()

        errors = []
        if not title:
            errors.append("Title is required.")
        if not author:
            errors.append("Author is required.")
        if not re.match(r"^\d{10}(\d{3})?$", isbn.replace("-", "")):
            errors.append("ISBN must be 10 or 13 digits.")
        try:
            price = float(price)
            if price <= 0:
                raise ValueError
        except ValueError:
            errors.append("Price must be a positive number.")
        try:
            stock = int(stock)
            if stock < 0:
                raise ValueError
        except ValueError:
            errors.append("Stock must be a non-negative integer.")
        if not category:
            errors.append("Category is required.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/book_form.html", action="Add", form_data=request.form)

        Product.create(title, author, isbn, price, stock, category, description)
        flash(f"'{title}' added to the catalogue.", "success")
        return redirect(url_for("admin_books"))

    return render_template("admin/book_form.html", action="Add", form_data={})


@app.route("/admin/books/edit/<int:book_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_book(book_id):
    product = Product.get_by_id(book_id)
    if not product:
        flash("Book not found.", "danger")
        return redirect(url_for("admin_books"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        isbn = request.form.get("isbn", "").strip()
        price = request.form.get("price", "")
        stock = request.form.get("stock", "")
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        available = request.form.get("available") == "1"

        errors = []
        if not title:
            errors.append("Title is required.")
        if not author:
            errors.append("Author is required.")
        try:
            price = float(price)
            if price <= 0:
                raise ValueError
        except ValueError:
            errors.append("Price must be a positive number.")
        try:
            stock = int(stock)
            if stock < 0:
                raise ValueError
        except ValueError:
            errors.append("Stock must be a non-negative integer.")
        if not category:
            errors.append("Category is required.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin/book_form.html", action="Edit",
                                   form_data=request.form, book=product)

        Product.update(book_id, title, author, isbn, price, stock, category, description, available)
        flash(f"'{title}' updated.", "success")
        return redirect(url_for("admin_books"))

    return render_template("admin/book_form.html", action="Edit",
                           form_data=product.to_dict(), book=product)


@app.route("/admin/books/delete/<int:book_id>", methods=["POST"])
@admin_required
def admin_delete_book(book_id):
    product = Product.get_by_id(book_id)
    if product:
        Product.delete(book_id)
        flash(f"'{product.title}' removed from catalogue.", "info")
    return redirect(url_for("admin_books"))


@app.route("/admin/orders")
@admin_required
def admin_orders():
    orders = Order.get_all()
    return render_template("admin/orders.html", orders=orders)


@app.route("/admin/reports")
@admin_required
def admin_reports():
    period = request.args.get("period", "all")
    report = SalesReport()
    summary = report.get_summary(period)
    return render_template("admin/reports.html", summary=summary, period=period)


@app.route("/admin/accounts")
@admin_required
def admin_accounts():
    db = Database()
    rows = db.fetchall("SELECT id, name, email, phone, address, role FROM accounts WHERE role = 'customer' ORDER BY name")
    accounts = [dict(r) for r in rows]
    return render_template("admin/accounts.html", accounts=accounts)


@app.route("/admin/accounts/reset/<int:account_id>", methods=["GET", "POST"])
@admin_required
def admin_reset_password(account_id):
    from werkzeug.security import generate_password_hash
    db = Database()
    acc = db.fetchone("SELECT * FROM accounts WHERE id = ? AND role = 'customer'", (account_id,))
    if not acc:
        flash("Account not found.", "danger")
        return redirect(url_for("admin_accounts"))

    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if not is_strong_password(new_password):
            flash("Password must be 8+ characters with at least one uppercase letter, number, and special character.", "danger")
            return render_template("admin/reset_password.html", acc=acc)
        if new_password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("admin/reset_password.html", acc=acc)

        db.execute(
            "UPDATE accounts SET password = ? WHERE id = ?",
            (generate_password_hash(new_password), account_id)
        )
        flash(f"Password for {acc['name']} has been reset.", "success")
        return redirect(url_for("admin_accounts"))

    return render_template("admin/reset_password.html", acc=acc)


if __name__ == "__main__":
    bootstrap()
    app.run(debug=True, port=5000)