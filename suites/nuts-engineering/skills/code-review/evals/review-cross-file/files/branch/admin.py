def bulk_update_prices(conn, changes):
    """Apply {item_id: new_price_cents} from the nightly supplier feed in one batch."""
    conn.executemany(
        "UPDATE items SET price_cents = ? WHERE id = ?",
        [(cents, item_id) for item_id, cents in changes.items()],
    )
