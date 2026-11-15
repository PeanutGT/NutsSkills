#!/usr/bin/env bash
# Builds the review fixture: a git repo whose feat/coupons branch has four planted defects
# that only show up when the diff is read together with the files it did not change, plus one decoy.
# Usage: bash place-files.sh <target-dir>
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"; t="$1"
mkdir -p "$t/shop" "$t/tests"; cd "$t"
touch shop/__init__.py tests/__init__.py
echo 'Shop backend. Amounts are integer cents. Tests: `python -m unittest discover -s tests -t .`' > README.md
for f in db prices cart inventory checkout; do cp "$here/files/main/$f.py" "shop/$f.py"; done
cp "$here/files/main/test_checkout.py" tests/test_checkout.py
git init -q -b main && git add -A && git -c user.name=eval -c user.email=eval@example.com commit -q -m initial
git switch -q -c feat/coupons
for f in db inventory checkout coupons admin; do cp "$here/files/branch/$f.py" "shop/$f.py"; done
cp "$here/files/branch/test_coupons.py" tests/test_coupons.py
cp "$here/files/branch/test_stock.py" tests/test_stock.py
git add -A && git -c user.name=eval -c user.email=eval@example.com commit -q -m "Add coupons, stock badge and supplier price import"
