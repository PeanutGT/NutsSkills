import unittest
from orders.db import connect
from orders.service import list_orders

class ListOrdersTest(unittest.TestCase):
    def test_first_page(self):
        conn = connect()
        conn.executemany("INSERT INTO orders VALUES (?,?,?,?)", [(1, 7, 10.0, "paid"), (2, 7, 5.0, "new")])
        self.assertEqual([o["id"] for o in list_orders(conn, 7)], [1, 2])
