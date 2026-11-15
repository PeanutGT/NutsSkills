import sqlite3
from contextlib import contextmanager

SCHEMA = '''
CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT, price_cents INTEGER, stock INTEGER);
CREATE TABLE IF NOT EXISTS cart_lines (cart_id INTEGER, item_id INTEGER, qty INTEGER);
CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, cart_id INTEGER, total_cents INTEGER);
CREATE TABLE IF NOT EXISTS coupons (code TEXT PRIMARY KEY, amount_off REAL, used INTEGER DEFAULT 0);  -- SAVE5: amount_off = 5.0 (five dollars)
'''


def connect(path=":memory:"):
    conn = sqlite3.connect(path, isolation_level=None)  # transactions are managed by transaction()
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def transaction(conn):
    conn.execute("BEGIN")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
