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
