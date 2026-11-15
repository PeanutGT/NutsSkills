import sqlite3

SCHEMA = '''
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, total REAL, status TEXT);
CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, price REAL);
CREATE TABLE order_items (order_id INTEGER, item_id INTEGER);
'''

def connect(path=":memory:"):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn
