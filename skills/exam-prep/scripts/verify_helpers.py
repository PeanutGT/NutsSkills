"""Helpers for verifying exam-prep answers.

Usage in a verify.py:

    import sys; sys.path.insert(0, "<skill-dir>/scripts")
    from verify_helpers import check, is_eigvec, summary
    import sympy as sp

    check("Q1 A^-1", sp.Matrix([[1, 2], [3, 4]]).inv(), sp.Matrix([[-2, 1], [1.5, -0.5]]))
    summary()   # prints ALL OK or the list of mismatches; exit code 1 on mismatch
"""
import sys

import sympy as sp

_results: dict[str, bool] = {}


def same(a, b, tol=1e-9):
    """Compare two answers: bools, dicts, lists/tuples, sets, sympy matrices, exact or float numbers."""
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, dict) or isinstance(b, dict):
        return dict(a) == dict(b)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (set, frozenset)) or isinstance(b, (set, frozenset)):
        return set(a) == set(b)
    a, b = sp.sympify(a), sp.sympify(b)
    if isinstance(a, sp.MatrixBase) or isinstance(b, sp.MatrixBase):
        if not (isinstance(a, sp.MatrixBase) and isinstance(b, sp.MatrixBase)) or a.shape != b.shape:
            return False
        return all(same(x, y, tol) for x, y in zip(a, b))
    if a.is_number and b.is_number and (a.has(sp.Float) or b.has(sp.Float)):
        return abs(complex(sp.N(a)) - complex(sp.N(b))) < tol
    return sp.simplify(a - b) == 0


def check(qid, got, expected, tol=1e-9):
    ok = bool(same(got, expected, tol))
    _results[qid] = ok
    print(f"{qid}: {'OK ' if ok else 'MISMATCH'}  got={got}  expected={expected}")
    return ok


def is_eigvec(A, v, lam):
    """True if v is a nonzero eigenvector of A for eigenvalue lam."""
    A, v = sp.Matrix(A), sp.Matrix(v)
    return (not v.is_zero_matrix) and sp.simplify(A * v - lam * v).is_zero_matrix


def summary():
    bad = [k for k, v in _results.items() if not v]
    if bad:
        print("\nFIX NEEDED: " + ", ".join(bad))
        sys.exit(1)
    print(f"\nALL OK ({len(_results)} checks)")
