"""
Database module for Favourite Books Online Bookstore.
Implements the Singleton pattern to ensure a single shared database connection.

Coding standard: PEP 8 (https://peps.python.org/pep-0008/)
"""

import sqlite3
import os


class Database:
    """
    Singleton database class responsible for managing all SQLite operations.
    Ensures only one database connection exists throughout the application lifecycle.
    """

    _instance = None
    _db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "favouritebooks.db")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connection = None
        return cls._instance

    def get_connection(self):
        """Returns the active SQLite connection, creating one if necessary."""
        if self._connection is None:
            self._connection = sqlite3.connect(self._db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    def execute(self, query, params=()):
        """Executes a write query (INSERT, UPDATE, DELETE) and commits."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor

    def fetchone(self, query, params=()):
        """Executes a SELECT query and returns a single row."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query, params=()):
        """Executes a SELECT query and returns all matching rows."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def initialise_schema(self):
        """Creates all required database tables if they do not already exist."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                role TEXT NOT NULL DEFAULT 'customer'
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                isbn TEXT NOT NULL UNIQUE,
                price REAL NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                category TEXT NOT NULL,
                description TEXT,
                available INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS carts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL UNIQUE,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );

            CREATE TABLE IF NOT EXISTS cart_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cart_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (cart_id) REFERENCES carts(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                total_price REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                shipping_address TEXT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
        """)
        conn.commit()

    def seed_data(self):
        """Seeds the database with sample books and an admin account if empty."""
        from werkzeug.security import generate_password_hash

        existing = self.fetchone("SELECT id FROM accounts WHERE role = 'admin'")
        if existing:
            return

        # Seed admin account
        self.execute(
            "INSERT INTO accounts (name, email, password, role) VALUES (?, ?, ?, ?)",
            ("Admin", "admin@favouritebooks.com.au",
             generate_password_hash("Admin@123"), "admin")
        )

        # Seed sample books
        books = [
            ("The Great Gatsby", "F. Scott Fitzgerald", "9780743273565", 19.99, 15, "Classic Fiction",
             "A story of wealth, love, and the American Dream set in the 1920s."),
            ("To Kill a Mockingbird", "Harper Lee", "9780061935466", 17.99, 10, "Classic Fiction",
             "A powerful story of racial injustice and childhood innocence in the American South."),
            ("1984", "George Orwell", "9780451524935", 15.99, 20, "Dystopian Fiction",
             "A chilling portrayal of a totalitarian society under constant surveillance."),
            ("Sapiens", "Yuval Noah Harari", "9780062316097", 24.99, 12, "Non-Fiction",
             "A brief history of humankind, from ancient foragers to modern-day empires."),
            ("Atomic Habits", "James Clear", "9780735211292", 29.99, 18, "Self-Help",
             "Practical strategies for building good habits and breaking bad ones."),
            ("The Midnight Library", "Matt Haig", "9780525559474", 22.99, 8, "Contemporary Fiction",
             "A magical library between life and death where every book is a different life you could have lived."),
            ("Educated", "Tara Westover", "9780399590504", 21.99, 14, "Memoir",
             "A memoir about a young woman who grows up in a survivalist family and eventually escapes to Cambridge."),
            ("Dune", "Frank Herbert", "9780441013593", 18.99, 25, "Science Fiction",
             "An epic tale of politics, religion, and survival on a desert planet."),
            ("The Psychology of Money", "Morgan Housel", "9780857197689", 27.99, 16, "Finance",
             "Timeless lessons on wealth, greed, and happiness told through stories."),
            ("Norwegian Wood", "Haruki Murakami", "9780375704024", 20.99, 9, "Contemporary Fiction",
             "A nostalgic story of loss and sexuality set in Tokyo during the late 1960s."),
        ]

        for book in books:
            self.execute(
                """INSERT INTO products (title, author, isbn, price, stock, category, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                book
            )