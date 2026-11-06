#!/usr/bin/env bash
# Builds the review fixture: a git repo whose feat/order-details branch has five planted defects.
# Usage: bash place-files.sh <target-dir>
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"; t="$1"
mkdir -p "$t/orders" "$t/tests"; cd "$t"
touch orders/__init__.py tests/__init__.py
echo 'Order service. Tests: `python -m unittest discover -s tests -t .`' > README.md
cp "$here/files/main/db.py" orders/db.py
cp "$here/files/main/service.py" orders/service.py
cp "$here/files/main/test_service.py" tests/test_service.py
git init -q -b main && git add -A && git -c user.name=eval -c user.email=eval@example.com commit -q -m initial
git switch -q -c feat/order-details
cp "$here/files/branch/service.py" orders/service.py
cp "$here/files/branch/test_details.py" tests/test_details.py
git add -A && git -c user.name=eval -c user.email=eval@example.com commit -q -m "Add order details and search"
