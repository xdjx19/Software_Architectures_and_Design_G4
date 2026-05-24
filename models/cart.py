"""
ShoppingCart and CartItem models for Favourite Books Online Bookstore.

Coding standard: PEP 8 (https://peps.python.org/pep-0008/)
"""

from models.database import Database
from models.catalogue import Product


class CartItem:
    """
    Represents a single item in a customer's shopping cart.
    Knows the associated product, its price, and the selected quantity.
    """

    def __init__(self, item_id, cart_id, product, quantity):
        self._id = item_id
        self._cart_id = cart_id
        self._product = product
        self._quantity = quantity

    @property
    def id(self):
        return self._id

    @property
    def product(self):
        return self._product

    @property
    def quantity(self):
        return self._quantity

    @property
    def subtotal(self):
        """Returns the total price for this cart item (unit price × quantity)."""
        return round(self._product.price * self._quantity, 2)

    def to_dict(self):
        return {
            "id": self._id,
            "product": self._product.to_dict(),
            "quantity": self._quantity,
            "subtotal": self.subtotal
        }


class ShoppingCart:
    """
    Represents a single customer's shopping cart.
    Manages adding, removing, and updating cart items,
    and is responsible for generating an Order on checkout.
    """

    def __init__(self, cart_id, account_id):
        self._id = cart_id
        self._account_id = account_id
        self._db = Database()

    @property
    def id(self):
        return self._id

    @staticmethod
    def get_for_account(account_id):
        """Fetches the ShoppingCart instance belonging to a given account."""
        db = Database()
        row = db.fetchone("SELECT * FROM carts WHERE account_id = ?", (account_id,))
        if row:
            return ShoppingCart(row["id"], account_id)
        return None

    def get_items(self):
        """Returns all CartItem objects currently in this cart."""
        rows = self._db.fetchall(
            """SELECT ci.id, ci.cart_id, ci.product_id, ci.quantity
               FROM cart_items ci
               WHERE ci.cart_id = ?""",
            (self._id,)
        )
        items = []
        for row in rows:
            product = Product.get_by_id(row["product_id"])
            if product:
                items.append(CartItem(row["id"], row["cart_id"], product, row["quantity"]))
        return items

    def add_item(self, product_id, quantity=1):
        """
        Adds a product to the cart. If the product is already in the cart,
        increments the quantity instead. Returns an error string on failure.
        """
        product = Product.get_by_id(product_id)
        if not product or not product.available:
            return "Product is not available."
        if product.stock < quantity:
            return "Insufficient stock."

        existing = self._db.fetchone(
            "SELECT id, quantity FROM cart_items WHERE cart_id = ? AND product_id = ?",
            (self._id, product_id)
        )
        if existing:
            new_qty = existing["quantity"] + quantity
            if product.stock < new_qty:
                return "Insufficient stock for requested quantity."
            self._db.execute(
                "UPDATE cart_items SET quantity = ? WHERE id = ?",
                (new_qty, existing["id"])
            )
        else:
            self._db.execute(
                "INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (?, ?, ?)",
                (self._id, product_id, quantity)
            )
        return None

    def update_item_quantity(self, cart_item_id, quantity):
        """Updates the quantity of a specific cart item. Removes it if quantity is 0."""
        if quantity <= 0:
            self.remove_item(cart_item_id)
            return
        self._db.execute(
            "UPDATE cart_items SET quantity = ? WHERE id = ? AND cart_id = ?",
            (quantity, cart_item_id, self._id)
        )

    def remove_item(self, cart_item_id):
        """Removes a single item from the cart."""
        self._db.execute(
            "DELETE FROM cart_items WHERE id = ? AND cart_id = ?",
            (cart_item_id, self._id)
        )

    def clear(self):
        """Removes all items from the cart."""
        self._db.execute("DELETE FROM cart_items WHERE cart_id = ?", (self._id,))

    def get_total(self):
        """Calculates and returns the total price of all items in the cart."""
        items = self.get_items()
        return round(sum(item.subtotal for item in items), 2)

    def is_empty(self):
        """Returns True if the cart contains no items."""
        row = self._db.fetchone(
            "SELECT COUNT(*) as cnt FROM cart_items WHERE cart_id = ?", (self._id,)
        )
        return row["cnt"] == 0