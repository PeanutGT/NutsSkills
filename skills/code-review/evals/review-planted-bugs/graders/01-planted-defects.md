# Planted defects

One point each; a finding counts only if it names the defect and the location.

1. **SQL injection**: `get_order_details` builds SQL with an f-string from `order_id`.
2. **Missing authorization (IDOR)**: `get_order_details` never checks that the order belongs to `current_user`.
3. **N+1 queries**: one `SELECT ... FROM items` per order item inside the loop.
4. **Pagination off by one**: `search_orders` uses `offset = page * per_page`, so page 1 skips the first page (`list_orders` uses `page - 1`).
5. **Swallowed errors**: `search_orders` catches every `Exception` and returns `[]`.

Bonus: notes that `search_orders` has no tests and that the details test only covers the owner's happy path.

Format: findings ranked most severe first, each with a concrete scenario (input or state, then wrong result). No code changes.
