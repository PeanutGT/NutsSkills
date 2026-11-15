import unittest
from orders.db import connect
from orders.service import User, get_order_details

class DetailsTest(unittest.TestCase):
    def test_returns_items(self):
        conn = connect()
        conn.execute("INSERT INTO orders VALUES (1, 7, 15.0, 'paid')")
        conn.executemany("INSERT INTO items VALUES (?,?,?)", [(1, "pen", 5.0), (2, "book", 10.0)])
        conn.executemany("INSERT INTO order_items VALUES (?,?)", [(1, 1), (1, 2)])
        d = get_order_details(conn, User(7, "amy"), 1)
        self.assertEqual([i["name"] for i in d["items"]], ["pen", "book"])
