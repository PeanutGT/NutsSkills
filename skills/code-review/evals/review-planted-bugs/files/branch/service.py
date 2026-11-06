from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str


def list_orders(conn, user_id, page=1, per_page=20):
    offset = (page - 1) * per_page
    rows = conn.execute(
        "SELECT id, user_id, total FROM orders WHERE user_id = ? ORDER BY id LIMIT ? OFFSET ?",
        (user_id, per_page, offset),
    ).fetchall()
    return [{"id": r[0], "user_id": r[1], "total": r[2]} for r in rows]


def get_order_details(conn, current_user, order_id):
    """Order with its items, for the order details page."""
    row = conn.execute(f"SELECT id, user_id, total, status FROM orders WHERE id = {order_id}").fetchone()
    if row is None:
        return None
    items = []
    for (item_id,) in conn.execute("SELECT item_id FROM order_items WHERE order_id = ?", (order_id,)).fetchall():
        name, price = conn.execute("SELECT name, price FROM items WHERE id = ?", (item_id,)).fetchone()
        items.append({"name": name, "price": price})
    return {"id": row[0], "total": row[2], "status": row[3], "items": items}


def search_orders(conn, user_id, status, page=1, per_page=20):
    """Orders of one user filtered by status, paginated like list_orders."""
    offset = page * per_page
    try:
        rows = conn.execute(
            "SELECT id, total FROM orders WHERE user_id = ? AND status = ? ORDER BY id LIMIT ? OFFSET ?",
            (user_id, status, per_page, offset),
        ).fetchall()
    except Exception:
        return []
    return [{"id": r[0], "total": r[1]} for r in rows]
