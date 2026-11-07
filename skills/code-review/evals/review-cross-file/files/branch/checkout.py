from shop.cart import cart_total
from shop.coupons import redeem_coupon
from shop.db import transaction
from shop.inventory import reserve


class OutOfStock(Exception):
    pass


def checkout(conn, cart_id, coupon_code=None):
    """Reserve stock, apply the coupon and create the order in one transaction. Returns the order id."""
    with transaction(conn):
        lines = conn.execute("SELECT item_id, qty FROM cart_lines WHERE cart_id = ?", (cart_id,)).fetchall()
        for item_id, qty in lines:
            if not reserve(conn, item_id, qty):
                raise OutOfStock(item_id)
        total = cart_total(conn, cart_id)
        if coupon_code:
            total = redeem_coupon(conn, coupon_code, total)
        cur = conn.execute("INSERT INTO orders (cart_id, total_cents) VALUES (?, ?)", (cart_id, total))
        return cur.lastrowid
