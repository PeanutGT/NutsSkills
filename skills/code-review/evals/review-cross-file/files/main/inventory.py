def reserve(conn, item_id, qty):
    """Take qty units off stock. Returns False if there are not enough."""
    cur = conn.execute(
        "UPDATE items SET stock = stock - ? WHERE id = ? AND stock >= ?", (qty, item_id, qty)
    )
    return cur.rowcount == 1
