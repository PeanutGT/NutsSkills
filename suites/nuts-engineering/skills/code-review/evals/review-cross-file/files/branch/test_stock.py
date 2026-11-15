import unittest
from shop.admin import bulk_update_prices
from shop.db import connect
from shop.inventory import reserve, stock_levels


class StockTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect()
        self.conn.executemany("INSERT INTO items VALUES (?,?,?,?)", [(1, "pen", 250, 5), (2, "book", 1500, 0)])

    def test_reserve_returns_units_left(self):
        self.assertEqual(reserve(self.conn, 1, 2), 3)

    def test_reserve_not_enough(self):
        self.assertIsNone(reserve(self.conn, 2, 1))

    def test_stock_levels(self):
        self.assertEqual(stock_levels(self.conn, [1, 2]), {1: 5, 2: 0})

    def test_bulk_update_prices(self):
        bulk_update_prices(self.conn, {1: 300})
        self.assertEqual(self.conn.execute("SELECT price_cents FROM items WHERE id = 1").fetchone()[0], 300)
