"""
Person hierarchy models for Favourite Books Online Bookstore.
Implements abstract Person base class with Customer and Administrator subclasses.

Coding standard: PEP 8 (https://peps.python.org/pep-0008/)
"""

from abc import ABC, abstractmethod
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import Database


class Person(ABC):
    """
    Abstract base class representing any person who interacts with the system.
    Stores shared contact information used by both Customer and Administrator.
    """

    def __init__(self, person_id, name, email, phone=None, address=None):
        self._id = person_id
        self._name = name
        self._email = email
        self._phone = phone
        self._address = address

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def email(self):
        return self._email

    @property
    def phone(self):
        return self._phone

    @property
    def address(self):
        return self._address

    @abstractmethod
    def get_role(self):
        """Returns the role string for this person type."""
        pass


class Customer(Person):
    """
    Represents a registered customer of Favourite Books.
    Inherits contact information from Person and adds customer-specific behaviour.
    """

    def __init__(self, person_id, name, email, phone=None, address=None):
        super().__init__(person_id, name, email, phone, address)

    def get_role(self):
        return "customer"

    @staticmethod
    def register(name, email, password, phone=None, address=None):
        """
        Registers a new customer account.
        Returns the new account id on success, or None if the email already exists.
        """
        db = Database()
        existing = db.fetchone("SELECT id FROM accounts WHERE email = ?", (email,))
        if existing:
            return None

        hashed = generate_password_hash(password)
        cursor = db.execute(
            "INSERT INTO accounts (name, email, password, phone, address, role) VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, hashed, phone, address, "customer")
        )
        account_id = cursor.lastrowid

        # Create a shopping cart for the new customer
        db.execute("INSERT INTO carts (account_id) VALUES (?)", (account_id,))
        return account_id

    @staticmethod
    def get_by_id(account_id):
        """Fetches a Customer instance by account ID."""
        db = Database()
        row = db.fetchone("SELECT * FROM accounts WHERE id = ? AND role = 'customer'", (account_id,))
        if row:
            return Customer(row["id"], row["name"], row["email"], row["phone"], row["address"])
        return None


class Administrator(Person):
    """
    Represents an administrator of Favourite Books.
    Inherits contact information from Person and has catalogue/report management access.
    """

    def __init__(self, person_id, name, email, phone=None, address=None):
        super().__init__(person_id, name, email, phone, address)

    def get_role(self):
        return "admin"

    @staticmethod
    def get_by_id(account_id):
        """Fetches an Administrator instance by account ID."""
        db = Database()
        row = db.fetchone("SELECT * FROM accounts WHERE id = ? AND role = 'admin'", (account_id,))
        if row:
            return Administrator(row["id"], row["name"], row["email"], row["phone"], row["address"])
        return None


class Account:
    """
    Manages account authentication and session-related behaviour.
    Acts as the entry point for both Customer and Administrator login.
    """

    @staticmethod
    def authenticate(email, password):
        """
        Verifies login credentials against stored records.
        Returns a dict with account data on success, or None on failure.
        """
        db = Database()
        row = db.fetchone("SELECT * FROM accounts WHERE email = ?", (email,))
        if row and check_password_hash(row["password"], password):
            return {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "role": row["role"]
            }
        return None

    @staticmethod
    def update_profile(account_id, name, phone, address):
        """Updates the name, phone, and address for an existing account."""
        db = Database()
        db.execute(
            "UPDATE accounts SET name = ?, phone = ?, address = ? WHERE id = ?",
            (name, phone, address, account_id)
        )

    @staticmethod
    def get_by_id(account_id):
        """Returns raw account row data by ID."""
        db = Database()
        return db.fetchone("SELECT * FROM accounts WHERE id = ?", (account_id,))