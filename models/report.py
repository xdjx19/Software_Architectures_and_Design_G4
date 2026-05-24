"""
SalesReport model for Favourite Books Online Bookstore.
Generates sales statistics for administrator reporting.

Coding standard: PEP 8 (https://peps.python.org/pep-0008/)
"""

from models.database import Database


class SalesReport:
    """
    Generates sales statistics and reports for administrators.
    Queries order and payment data to produce summaries over specified time periods.
    """

    def __init__(self):
        self._db = Database()

    def get_summary(self, period="all"):
        """
        Generates a sales summary for a given time period.
        period options: 'today', 'week', 'month', 'all'
        Returns a dict containing total revenue, order count, and top-selling books.
        """
        date_filter = self._get_date_filter(period)

        # Total revenue and order count
        revenue_row = self._db.fetchone(
            f"""SELECT COALESCE(SUM(total_price), 0) as revenue,
                       COUNT(*) as order_count
                FROM orders
                WHERE status = 'paid' {date_filter}"""
        )

        # Top-selling books
        top_books = self._db.fetchall(
            f"""SELECT p.title, p.author, SUM(oi.quantity) as units_sold,
                       SUM(oi.quantity * oi.unit_price) as book_revenue
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                JOIN products p ON p.id = oi.product_id
                WHERE o.status = 'paid' {date_filter}
                GROUP BY p.id
                ORDER BY units_sold DESC
                LIMIT 5"""
        )

        # Sales by category
        category_sales = self._db.fetchall(
            f"""SELECT p.category, SUM(oi.quantity) as units_sold,
                       SUM(oi.quantity * oi.unit_price) as category_revenue
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                JOIN products p ON p.id = oi.product_id
                WHERE o.status = 'paid' {date_filter}
                GROUP BY p.category
                ORDER BY units_sold DESC"""
        )

        return {
            "period": period,
            "total_revenue": round(revenue_row["revenue"], 2),
            "order_count": revenue_row["order_count"],
            "top_books": [dict(r) for r in top_books],
            "category_sales": [dict(r) for r in category_sales]
        }

    def _get_date_filter(self, period):
        """Returns an SQL date filter clause for the given period string."""
        filters = {
            "today": "AND DATE(created_at) = DATE('now')",
            "week": "AND created_at >= DATE('now', '-7 days')",
            "month": "AND created_at >= DATE('now', '-30 days')",
            "all": ""
        }
        return filters.get(period, "")