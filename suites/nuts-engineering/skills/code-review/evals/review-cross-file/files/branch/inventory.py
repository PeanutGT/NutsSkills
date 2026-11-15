def reserve(conn, item_id, qty):
    """Take qty units off stock. Returns the units left, or None if there are not enough."""
    cur = conn.execute(
        "UPDATE items SET stock = stock - ? WHERE id = ? AND stock >= ?", (qty, item_id, qty)
    )
    if cur.rowcount != 1:
        return None
    return conn.execute("SELECT stock FROM items WHERE id = ?", (item_id,)).fetchone()[0]


def stock_levels(conn, item_ids):
    """Units in stock per item id, for the "only N left" badge."""
    marks = ",".join("?" * len(item_ids))
    rows = conn.execute(f"SELECT id, stock FROM items WHERE id IN ({marks})", list(item_ids)).fetchall()
    return dict(rows)
