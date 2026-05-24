"""
app.py — Main entry point for Favourite Books Online Bookstore.
Implements MVC routing using Flask, with session-based authentication.

Coding standard: PEP 8 (https://peps.python.org/pep-0008/)
Reference: https://peps.python.org/pep-0008/
"""

import re
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, jsonify)

from models.database import Database
from models.account import Account, Customer
from models.catalogue import Catalogue, Product
from models.cart import ShoppingCart
from models.order import Order, CheckoutFacade
from models.report import SalesReport

app = Flask(__name__)
app.secret_key = "favouritebooks-secret-2026"

# ─── Bootstrap ──────────────────────────────────────────────────────────────

def bootstrap():
    """
    Bootstraps the application on startup:
    1. Creates a singleton Database instance
    2. Initialises the schema
    3. Seeds sample data if the database is empty
    """
    db = Database()
    db.initialise_schema()
    db.seed_data()

# ─── Auth Decorators ─────────────────────────────────────────────────────────

def login_required(f):
    """Redirects unauthenticated users to the login page."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "account_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def customer_required(f):
    """Restricts route to customer accounts only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "customer":
            flash("This page is for customers only.", "warning")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Restricts route to administrator accounts only."""
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

# ─── Validation Helpers ──────────────────────────────────────────────────────

def is_valid_email(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

def is_strong_password(password):
    """Validates: 8+ chars, 1 uppercase, 1 number, 1 special character."""
    return (len(password) >= 8 and
            re.search(r"[A-Z]", password) and
            re.search(r"\d", password) and
            re.search(r"[!@#$%^&*(),.?\":{}|<>]", password))

# ─── Public Routes ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    catalogue = Catalogue()
    featured = catalogue.get_all_available()[:6]
    categories = catalogue.get_all_categories()
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


# ─── Authentication Routes ───────────────────────────────────────────────────

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
            for error in errors:
                flash(error, "danger")
            return render_template("register.html",
                                   form_data=request.form)

        account_id = Customer.register(name, email, password, phone, address)
        if account_id is None:
            flash("An account with this email already exists.", "danger")
            return render_template("register.html", form_data=request.form)

        flash("Account created successfully! Please log in.", "success")
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

        account = Account.authenticate(email, password)
        if account:
            session["account_id"] = account["id"]
            session["name"] = account["name"]
            session["role"] = account["role"]
            flash(f"Welcome back, {account['name']}!", "success")
            if account["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

# ─── Cart Routes ─────────────────────────────────────────────────────────────

@app.route("/cart")
@login_required
@customer_required
def cart():
    cart = ShoppingCart.get_for_account(session["account_id"])
    items = cart.get_items() if cart else []
    total = cart.get_total() if cart else 0
    return render_template("cart.html", items=items, total=total)


@app.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
@customer_required
def add_to_cart(product_id):
    quantity = int(request.form.get("quantity", 1))
    if quantity < 1:
        flash("Quantity must be at least 1.", "danger")
        return redirect(request.referrer or url_for("catalogue"))

    cart = ShoppingCart.get_for_account(session["account_id"])
    error = cart.add_item(product_id, quantity)
    if error:
        flash(error, "danger")
    else:
        flash("Book added to your cart.", "success")
    return redirect(request.referrer or url_for("catalogue"))


@app.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required
@customer_required
def update_cart_item(item_id):
    quantity = int(request.form.get("quantity", 1))
    cart = ShoppingCart.get_for_account(session["account_id"])
    cart.update_item_quantity(item_id, quantity)
    flash("Cart updated.", "success")
    return redirect(url_for("cart"))


@app.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
@customer_required
def remove_from_cart(item_id):
    cart = ShoppingCart.get_for_account(session["account_id"])
    cart.remove_item(item_id)
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart"))

# ─── Checkout Routes ──────────────────────────────────────────────────────────

@app.route("/checkout", methods=["GET", "POST"])
@login_required
@customer_required
def checkout():
    cart = ShoppingCart.get_for_account(session["account_id"])
    if not cart or cart.is_empty():
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart"))

    account = Account.get_by_id(session["account_id"])
    items = cart.get_items()
    total = cart.get_total()

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
            for error in errors:
                flash(error, "danger")
            return render_template("checkout.html", items=items, total=total, account=account)

        payment_method = {"card_number": card_number, "card_name": card_name}
        facade = CheckoutFacade(cart, session["account_id"])
        success, message, order_id = facade.checkout(shipping_address, payment_method)

        if success:
            flash(message, "success")
            return redirect(url_for("order_confirmation", order_id=order_id))
        else:
            flash(message, "danger")

    return render_template("checkout.html", items=items, total=total, account=account)


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

# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin_dashboard():
    catalogue = Catalogue()
    books = catalogue.get_all_for_admin()
    orders = Order.get_all()
    report = SalesReport()
    summary = report.get_summary("all")
    return render_template("admin/dashboard.html", books=books,
                           orders=orders, summary=summary)


@app.route("/admin/books")
@admin_required
def admin_books():
    catalogue = Catalogue()
    books = catalogue.get_all_for_admin()
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
            for error in errors:
                flash(error, "danger")
            return render_template("admin/book_form.html", action="Add", form_data=request.form)

        Product.create(title, author, isbn, price, stock, category, description)
        flash(f"'{title}' has been added to the catalogue.", "success")
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
            for error in errors:
                flash(error, "danger")
            return render_template("admin/book_form.html", action="Edit",
                                   form_data=request.form, book=product)

        Product.update(book_id, title, author, isbn, price, stock,
                       category, description, available)
        flash(f"'{title}' has been updated.", "success")
        return redirect(url_for("admin_books"))

    return render_template("admin/book_form.html", action="Edit",
                           form_data=product.to_dict(), book=product)


@app.route("/admin/books/delete/<int:book_id>", methods=["POST"])
@admin_required
def admin_delete_book(book_id):
    product = Product.get_by_id(book_id)
    if product:
        Product.delete(book_id)
        flash(f"'{product.title}' has been removed from the catalogue.", "info")
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


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    bootstrap()
    app.run(debug=True, port=5000)