# report.py - SalesReport class for admin reporting
# pulls order and payment data from db and summarises it
# Coding standard: PEP 8 - https://peps.python.org/pep-0008/

from models.database import Database


class SalesReport:

    def __init__(self):
        self._db = Database()

    def get_summary(self, period="all"):
        date_filter = self._get_date_filter(period)

        revenue_row = self._db.fetchone(
            f"""SELECT COALESCE(SUM(total_price), 0) as revenue, COUNT(*) as order_count
                FROM orders WHERE status = 'paid' {date_filter}"""
        )

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
        filters = {
            "today": "AND DATE(created_at) = DATE('now')",
            "week": "AND created_at >= DATE('now', '-7 days')",
            "month": "AND created_at >= DATE('now', '-30 days')",
            "all": ""
        }
        return filters.get(period, "")