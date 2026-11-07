import unittest
from shop.coupons import CouponError, redeem_coupon
from shop.db import connect


class CouponTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect()
        self.conn.execute("INSERT INTO coupons (code, amount_off) VALUES ('SAVE5', 5.0)")

    def test_discounts_total(self):
        self.assertLess(redeem_coupon(self.conn, " save5 ", 2000), 2000)

    def test_works_once(self):
        redeem_coupon(self.conn, "SAVE5", 2000)
        with self.assertRaises(CouponError):
            redeem_coupon(self.conn, "SAVE5", 2000)

    def test_unknown_code(self):
        with self.assertRaises(CouponError):
            redeem_coupon(self.conn, "NOPE", 2000)
