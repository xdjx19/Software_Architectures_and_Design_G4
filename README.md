# Software_Architectures_and_Design_G4

to install all the intial dependencies, run the following command in your console:
pip install -r requirements.txt
---------------------------------------------------------
to run programme type this in the terminal and enter the given link or use live extension:
python app.py
---------------------------------------------------------
admin login details:
email - admin@favouritebooks.com.au password - Admin@123
---------------------------------------------------------
to use an user account, use the ui interface to create one
---------------------------------------------------------
project structure:
Software_Architectures_and_Design_G4/
├── app.py                  # Main Flask app, all routes
├── requirements.txt        # Python dependencies
├── favouritebooks.db       # SQLite database (auto-generated)
├── models/
│   ├── database.py         # Singleton Database class
│   ├── account.py          # Person, Customer, Administrator, Account
│   ├── catalogue.py        # Catalogue, Product
│   ├── cart.py             # ShoppingCart, CartItem
│   ├── order.py            # Order, Payment, Receipt, CheckoutFacade
│   └── report.py           # SalesReport
├── templates/
│   ├── base.html           # Shared navbar and layout
│   ├── index.html          # Homepage
│   ├── catalogue.html      # Browse books
│   ├── book_detail.html    # Individual book page
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── cart.html           # Shopping cart
│   ├── checkout.html       # Checkout and payment
│   ├── order_confirmation.html
│   ├── my_orders.html      # Customer order history
│   ├── order_detail.html   # Individual order view
│   └── admin/
│       ├── base_admin.html # Admin sidebar layout
│       ├── dashboard.html  # Admin overview
│       ├── manage_books.html
│       ├── book_form.html  # Add/edit book form
│       ├── orders.html     # All customer orders
│       └── reports.html    # Sales reports
└── static/
    └── css/
        └── style.css       # All styling