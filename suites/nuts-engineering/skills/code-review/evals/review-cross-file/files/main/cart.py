from shop.prices import get_price


def cart_total(conn, cart_id):
    """Cart total in cents."""
    lines = conn.execute("SELECT item_id, qty FROM cart_lines WHERE cart_id = ?", (cart_id,)).fetchall()
    return sum(get_price(conn, item_id) * qty for item_id, qty in lines)
