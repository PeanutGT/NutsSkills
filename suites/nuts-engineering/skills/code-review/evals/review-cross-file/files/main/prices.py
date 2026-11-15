"""Item prices, in integer cents, cached per process. Every price write goes through set_price."""
_cache = {}


def get_price(conn, item_id):
    if item_id not in _cache:
        row = conn.execute("SELECT price_cents FROM items WHERE id = ?", (item_id,)).fetchone()
        _cache[item_id] = row[0]
    return _cache[item_id]


def set_price(conn, item_id, cents):
    conn.execute("UPDATE items SET price_cents = ? WHERE id = ?", (cents, item_id))
    _cache.pop(item_id, None)


def clear():
    _cache.clear()
