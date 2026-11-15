from shop.db import transaction


class CouponError(Exception):
    pass


def redeem_coupon(conn, code, total):
    """Mark a fixed-amount coupon as used and return the discounted total. Each coupon works once."""
    code = code.strip().upper()
    with transaction(conn):
        row = conn.execute("SELECT amount_off, used FROM coupons WHERE code = ?", (code,)).fetchone()
        if row is None or row[1]:
            raise CouponError(code)
        conn.execute("UPDATE coupons SET used = 1 WHERE code = ?", (code,))
    return max(total - row[0], 0)
