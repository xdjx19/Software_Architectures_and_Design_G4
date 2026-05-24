"""
Product and Catalogue models for Favourite Books Online Bookstore.
Implements Observer-like refresh between Catalogue and Product data.

Coding standard: PEP 8 (https://peps.python.org/pep-0008/)
"""

from models.database import Database


class Product:
    """
    Represents a single book available in Favourite Books' catalogue.
    Stores all book-related data and manages availability status.
    """

    def __init__(self, product_id, title, author, isbn, price, stock,
                 category, description, available):
        self._id = product_id
        self._title = title
        self._author = author
        self._isbn = isbn
        self._price = price
        self._stock = stock
        self._category = category
        self._description = description
        self._available = bool(available)

    @property
    def id(self):
        return self._id

    @property
    def title(self):
        return self._title

    @property
    def author(self):
        return self._author

    @property
    def isbn(self):
        return self._isbn

    @property
    def price(self):
        return self._price

    @property
    def stock(self):
        return self._stock

    @property
    def category(self):
        return self._category

    @property
    def description(self):
        return self._description

    @property
    def available(self):
        return self._available

    def to_dict(self):
        """Returns a dictionary representation of the product."""
        return {
            "id": self._id,
            "title": self._title,
            "author": self._author,
            "isbn": self._isbn,
            "price": self._price,
            "stock": self._stock,
            "category": self._category,
            "description": self._description,
            "available": self._available
        }

    @staticmethod
    def get_by_id(product_id):
        """Fetches a single Product by its ID."""
        db = Database()
        row = db.fetchone("SELECT * FROM products WHERE id = ?", (product_id,))
        if row:
            return Product(row["id"], row["title"], row["author"], row["isbn"],
                           row["price"], row["stock"], row["category"],
                           row["description"], row["available"])
        return None

    @staticmethod
    def create(title, author, isbn, price, stock, category, description):
        """Inserts a new product into the database. Returns the new product ID."""
        db = Database()
        cursor = db.execute(
            """INSERT INTO products (title, author, isbn, price, stock, category, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, author, isbn, float(price), int(stock), category, description)
        )
        return cursor.lastrowid

    @staticmethod
    def update(product_id, title, author, isbn, price, stock, category, description, available):
        """Updates an existing product record."""
        db = Database()
        db.execute(
            """UPDATE products SET title=?, author=?, isbn=?, price=?, stock=?,
               category=?, description=?, available=? WHERE id=?""",
            (title, author, isbn, float(price), int(stock),
             category, description, int(available), product_id)
        )

    @staticmethod
    def delete(product_id):
        """Deletes a product from the database."""
        db = Database()
        db.execute("DELETE FROM products WHERE id = ?", (product_id,))

    @staticmethod
    def reduce_stock(product_id, quantity):
        """Reduces stock for a product after a successful order."""
        db = Database()
        db.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?",
            (quantity, product_id)
        )


class Catalogue:
    """
    Manages the display and retrieval of books in Favourite Books' online catalogue.
    Responsible for querying, filtering, and categorising products.
    """

    def __init__(self):
        self._db = Database()

    def get_all_available(self):
        """Returns all available products as Product instances."""
        rows = self._db.fetchall(
            "SELECT * FROM products WHERE available = 1 ORDER BY title"
        )
        return [Product(r["id"], r["title"], r["author"], r["isbn"],
                        r["price"], r["stock"], r["category"],
                        r["description"], r["available"]) for r in rows]

    def search(self, query):
        """
        Searches for products by title, author, or category.
        Returns matching available Product instances.
        """
        like = f"%{query}%"
        rows = self._db.fetchall(
            """SELECT * FROM products
               WHERE available = 1
               AND (title LIKE ? OR author LIKE ? OR category LIKE ?)
               ORDER BY title""",
            (like, like, like)
        )
        return [Product(r["id"], r["title"], r["author"], r["isbn"],
                        r["price"], r["stock"], r["category"],
                        r["description"], r["available"]) for r in rows]

    def get_by_category(self, category):
        """Returns all available products in a given category."""
        rows = self._db.fetchall(
            "SELECT * FROM products WHERE available = 1 AND category = ? ORDER BY title",
            (category,)
        )
        return [Product(r["id"], r["title"], r["author"], r["isbn"],
                        r["price"], r["stock"], r["category"],
                        r["description"], r["available"]) for r in rows]

    def get_all_categories(self):
        """Returns a sorted list of distinct product categories."""
        rows = self._db.fetchall(
            "SELECT DISTINCT category FROM products WHERE available = 1 ORDER BY category"
        )
        return [row["category"] for row in rows]

    def get_all_for_admin(self):
        """Returns all products (including unavailable) for admin management."""
        rows = self._db.fetchall("SELECT * FROM products ORDER BY title")
        return [Product(r["id"], r["title"], r["author"], r["isbn"],
                        r["price"], r["stock"], r["category"],
                        r["description"], r["available"]) for r in rows]