import unittest
from shop import prices
from shop.checkout import OutOfStock, checkout
from shop.db import connect


def shop_with_cart(stock, qty):
    conn = connect()
    conn.executemany("INSERT INTO items VALUES (?,?,?,?)", [(1, "pen", 250, stock), (2, "book", 1500, 10)])
    conn.executemany("INSERT INTO cart_lines VALUES (?,?,?)", [(1, 1, qty), (1, 2, 1)])
    return conn


class CheckoutTest(unittest.TestCase):
    def setUp(self):
        prices.clear()

    def test_creates_order_with_total(self):
        conn = shop_with_cart(stock=5, qty=2)
        order_id = checkout(conn, 1)
        total = conn.execute("SELECT total_cents FROM orders WHERE id = ?", (order_id,)).fetchone()[0]
        self.assertEqual(total, 2000)

    def test_out_of_stock_rolls_back(self):
        conn = shop_with_cart(stock=1, qty=2)
        with self.assertRaises(OutOfStock):
            checkout(conn, 1)
        self.assertEqual(conn.execute("SELECT stock FROM items WHERE id = 1").fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 0)
