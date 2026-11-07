# Planted defects

Every branch test passes. Each defect needs a file the diff did not change (or a convention stated outside it) to see.
One point each; a finding counts only if it names the defect, the location, and a scenario that actually fails.

1. **Coupon in dollars, totals in cents**: `coupons.amount_off` stores 5.0 for $5, but `cart_total` and `orders.total_cents` are cents (`prices.py`, `cart.py`, README). `redeem_coupon(conn, "SAVE5", 2000)` returns 1995.0: five cents off instead of 500, and a float goes into an INTEGER column.
2. **Nested transaction**: `redeem_coupon` opens `with transaction(conn)` and `checkout` calls it inside its own `transaction` (`db.py` does not support nesting). Any checkout with a coupon raises `sqlite3.OperationalError: cannot start a transaction within a transaction`. The coupon tests call `redeem_coupon` alone, so they pass.
3. **`reserve` return value changed under an unchanged caller**: `reserve` now returns units left, and `checkout` still does `if not reserve(...)`. Buying the last unit returns 0, so checkout raises `OutOfStock` (and rolls back) even though the stock was there.
4. **Price cache bypassed**: `bulk_update_prices` writes `items.price_cents` with raw SQL; `prices.get_price` caches per process and only `set_price` invalidates it, so `cart_total` and checkout keep charging the old price until restart.

# Decoy (minus one point if reported as a defect)

- `stock_levels` builds `IN (?,?,...)` with an f-string, but only placeholders go into the string and the ids are bound parameters. It is not SQL injection. (An empty list gives `IN ()`, which SQLite accepts and returns `{}`.)

# Bonus

- Notes that no test covers checkout with a coupon or buying the last unit, and that `test_discounts_total` only checks "less than", which is why the unit bug passes.

Format: findings ranked most severe first, each with a concrete scenario, verified by running something where cheap. No code changes.
