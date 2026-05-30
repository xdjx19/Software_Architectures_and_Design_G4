# order.py - Order, Payment, Receipt and CheckoutFacade
# CheckoutFacade ties together the whole checkout process in one place
# Coding standard: PEP 8 - https://peps.python.org/pep-0008/

from models.database import Database
from models.catalogue import Product


class Order:

    def __init__(self, order_id, account_id, total_price, status, created_at, shipping_address):
        self._id = order_id
        self._account_id = account_id
        self._total_price = total_price
        self._status = status
        self._created_at = created_at
        self._shipping_address = shipping_address

    @property
    def id(self):
        return self._id

    @property
    def account_id(self):
        return self._account_id

    @property
    def total_price(self):
        return self._total_price

    @property
    def status(self):
        return self._status

    @property
    def created_at(self):
        return self._created_at

    @property
    def shipping_address(self):
        return self._shipping_address

    def get_items(self):
        db = Database()
        rows = db.fetchall(
            """SELECT oi.quantity, oi.unit_price, p.title, p.author, p.isbn
               FROM order_items oi
               JOIN products p ON p.id = oi.product_id
               WHERE oi.order_id = ?""",
            (self._id,)
        )
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(order_id):
        db = Database()
        row = db.fetchone("SELECT * FROM orders WHERE id = ?", (order_id,))
        if row:
            return Order(row["id"], row["account_id"], row["total_price"],
                         row["status"], row["created_at"], row["shipping_address"])
        return None

    @staticmethod
    def get_for_account(account_id):
        db = Database()
        rows = db.fetchall(
            "SELECT * FROM orders WHERE account_id = ? ORDER BY created_at DESC",
            (account_id,)
        )
        return [Order(r["id"], r["account_id"], r["total_price"],
                      r["status"], r["created_at"], r["shipping_address"]) for r in rows]

    @staticmethod
    def get_all():
        db = Database()
        rows = db.fetchall(
            """SELECT o.*, a.name as customer_name, a.email as customer_email
               FROM orders o
               JOIN accounts a ON a.id = o.account_id
               ORDER BY o.created_at DESC"""
        )
        return [dict(r) for r in rows]


class Payment:
    # simulates payment processing - in production this would call PayPal or Stripe

    def __init__(self, order_id, amount, payment_method):
        self._order_id = order_id
        self._amount = amount
        self._payment_method = payment_method
        self._status = "pending"

    @property
    def status(self):
        return self._status

    def process(self):
        # cards ending in 0000 simulate a declined payment for testing
        if self._payment_method.get("card_number", "").endswith("0000"):
            self._status = "declined"
            return False

        self._status = "approved"
        db = Database()
        db.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (self._order_id,))
        return True


class Receipt:

    def __init__(self, order):
        self._order = order

    def generate(self):
        return {
            "order_id": self._order.id,
            "items": self._order.get_items(),
            "total_price": self._order.total_price,
            "shipping_address": self._order.shipping_address,
            "status": self._order.status,
            "created_at": self._order.created_at
        }


class CheckoutFacade:
    # facade that handles the full checkout flow so the route stays clean

    def __init__(self, cart, account_id):
        self._cart = cart
        self._account_id = account_id
        self._db = Database()

    def checkout(self, shipping_address, payment_method):
        if self._cart.is_empty():
            return False, "Your cart is empty. Add books before checking out.", None

        if not shipping_address or len(shipping_address.strip()) < 5:
            return False, "Please enter a valid shipping address.", None

        items = self._cart.get_items()
        total = self._cart.get_total()

        # create the order
        cursor = self._db.execute(
            "INSERT INTO orders (account_id, total_price, status, shipping_address) VALUES (?, ?, ?, ?)",
            (self._account_id, total, "pending", shipping_address.strip())
        )
        order_id = cursor.lastrowid

        # save order items and reduce stock
        for item in items:
            self._db.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                (order_id, item.product.id, item.quantity, item.product.price)
            )
            Product.reduce_stock(item.product.id, item.quantity)

        # try payment
        payment = Payment(order_id, total, payment_method)
        success = payment.process()

        if not success:
            self._db.execute("UPDATE orders SET status = 'payment_failed' WHERE id = ?", (order_id,))
            return False, "Payment was declined. Please check your card details and try again.", None

        order = Order.get_by_id(order_id)
        Receipt(order).generate()
        self._cart.clear()

        return True, "Order placed successfully!", order_id