# account.py - Person hierarchy and Account authentication
# Person is abstract, Customer and Administrator extend it
# Coding standard: PEP 8 - https://peps.python.org/pep-0008/

from abc import ABC, abstractmethod
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import Database


class Person(ABC):
    # abstract base class - stores shared info for customers and admins

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
        pass


class Customer(Person):

    def __init__(self, person_id, name, email, phone=None, address=None):
        super().__init__(person_id, name, email, phone, address)

    def get_role(self):
        return "customer"

    @staticmethod
    def register(name, email, password, phone=None, address=None):
        db = Database()
        # check email not already taken
        existing = db.fetchone("SELECT id FROM accounts WHERE email = ?", (email,))
        if existing:
            return None

        hashed = generate_password_hash(password)
        cursor = db.execute(
            "INSERT INTO accounts (name, email, password, phone, address, role) VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, hashed, phone, address, "customer")
        )
        acc_id = cursor.lastrowid
        # every customer gets a cart on registration
        db.execute("INSERT INTO carts (account_id) VALUES (?)", (acc_id,))
        return acc_id

    @staticmethod
    def get_by_id(account_id):
        db = Database()
        row = db.fetchone("SELECT * FROM accounts WHERE id = ? AND role = 'customer'", (account_id,))
        if row:
            return Customer(row["id"], row["name"], row["email"], row["phone"], row["address"])
        return None


class Administrator(Person):

    def __init__(self, person_id, name, email, phone=None, address=None):
        super().__init__(person_id, name, email, phone, address)

    def get_role(self):
        return "admin"

    @staticmethod
    def get_by_id(account_id):
        db = Database()
        row = db.fetchone("SELECT * FROM accounts WHERE id = ? AND role = 'admin'", (account_id,))
        if row:
            return Administrator(row["id"], row["name"], row["email"], row["phone"], row["address"])
        return None


class Account:
    # handles login and profile updates

    @staticmethod
    def authenticate(email, password):
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
        db = Database()
        db.execute(
            "UPDATE accounts SET name = ?, phone = ?, address = ? WHERE id = ?",
            (name, phone, address, account_id)
        )

    @staticmethod
    def get_by_id(account_id):
        db = Database()
        return db.fetchone("SELECT * FROM accounts WHERE id = ?", (account_id,))