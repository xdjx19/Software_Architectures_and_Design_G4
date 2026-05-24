"""
Order, Payment, and Receipt models for Favourite Books Online Bookstore.
Implements the Facade pattern via CheckoutFacade to simplify the checkout workflow.

Coding standard: PEP 8 (https://peps.python.org/pep-0008/)
"""

from models.database import Database
from models.catalogue import Product


class Order:
    """
    Represents a customer's placed order.
    Stores order items, pricing, status, and shipping address.
    """

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
        """Returns a list of order item dicts including product details."""
        db = Database()
        rows = db.fetchall(
            """SELECT oi.quantity, oi.unit_price,
                      p.title, p.author, p.isbn
               FROM order_items oi
               JOIN products p ON p.id = oi.product_id
               WHERE oi.order_id = ?""",
            (self._id,)
        )
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(order_id):
        """Fetches an Order instance by its ID."""
        db = Database()
        row = db.fetchone("SELECT * FROM orders WHERE id = ?", (order_id,))
        if row:
            return Order(row["id"], row["account_id"], row["total_price"],
                         row["status"], row["created_at"], row["shipping_address"])
        return None

    @staticmethod
    def get_for_account(account_id):
        """Returns all orders placed by a given customer account, most recent first."""
        db = Database()
        rows = db.fetchall(
            "SELECT * FROM orders WHERE account_id = ? ORDER BY created_at DESC",
            (account_id,)
        )
        return [Order(r["id"], r["account_id"], r["total_price"],
                      r["status"], r["created_at"], r["shipping_address"]) for r in rows]

    @staticmethod
    def get_all():
        """Returns all orders for admin review, most recent first."""
        db = Database()
        rows = db.fetchall(
            """SELECT o.*, a.name as customer_name, a.email as customer_email
               FROM orders o
               JOIN accounts a ON a.id = o.account_id
               ORDER BY o.created_at DESC"""
        )
        return [dict(r) for r in rows]


class Payment:
    """
    Represents the payment step for a customer order.
    Delegates actual processing to a simulated third-party payment method.
    """

    def __init__(self, order_id, amount, payment_method):
        self._order_id = order_id
        self._amount = amount
        self._payment_method = payment_method
        self._status = "pending"

    @property
    def status(self):
        return self._status

    def process(self):
        """
        Simulates payment processing via a third-party provider.
        In production, this would call an external payment gateway API (e.g. PayPal, Stripe).
        Returns True on success, False on failure.
        """
        # Simulate payment success for all non-declined test cards
        if self._payment_method.get("card_number", "").endswith("0000"):
            self._status = "declined"
            return False

        self._status = "approved"
        db = Database()
        db.execute(
            "UPDATE orders SET status = 'paid' WHERE id = ?",
            (self._order_id,)
        )
        return True


class Receipt:
    """
    Represents a receipt generated after a successful payment.
    Stores paid order information and can be sent to the customer.
    """

    def __init__(self, order):
        self._order = order

    def generate(self):
        """Returns a dict summary of the receipt for display to the customer."""
        return {
            "order_id": self._order.id,
            "items": self._order.get_items(),
            "total_price": self._order.total_price,
            "shipping_address": self._order.shipping_address,
            "status": self._order.status,
            "created_at": self._order.created_at
        }


class CheckoutFacade:
    """
    Facade class that simplifies the checkout workflow for the customer.
    Internally coordinates ShoppingCart, Order, Payment, and Receipt without
    exposing the complexity to the caller.
    """

    def __init__(self, cart, account_id):
        self._cart = cart
        self._account_id = account_id
        self._db = Database()

    def checkout(self, shipping_address, payment_method):
        """
        Executes the full checkout process:
        1. Validates the cart is not empty
        2. Creates an Order from cart contents
        3. Processes Payment
        4. Generates a Receipt
        5. Clears the cart on success

        Returns a tuple of (success: bool, message: str, order_id: int or None).
        """
        if self._cart.is_empty():
            return False, "Your cart is empty. Add books before checking out.", None

        if not shipping_address or len(shipping_address.strip()) < 5:
            return False, "Please enter a valid shipping address.", None

        items = self._cart.get_items()
        total = self._cart.get_total()

        # Create the order record
        cursor = self._db.execute(
            "INSERT INTO orders (account_id, total_price, status, shipping_address) VALUES (?, ?, ?, ?)",
            (self._account_id, total, "pending", shipping_address.strip())
        )
        order_id = cursor.lastrowid

        # Save each order item and reduce product stock
        for item in items:
            self._db.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                (order_id, item.product.id, item.quantity, item.product.price)
            )
            Product.reduce_stock(item.product.id, item.quantity)

        # Process payment
        payment = Payment(order_id, total, payment_method)
        success = payment.process()

        if not success:
            # Roll back order status on payment failure
            self._db.execute("UPDATE orders SET status = 'payment_failed' WHERE id = ?", (order_id,))
            return False, "Payment was declined. Please check your card details and try again.", None

        # Generate receipt and clear cart
        order = Order.get_by_id(order_id)
        receipt = Receipt(order)
        self._cart.clear()

        return True, "Order placed successfully!", order_id