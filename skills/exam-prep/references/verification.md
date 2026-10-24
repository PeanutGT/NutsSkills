# 驗算流程

## 為什麼要做

模型在矩陣運算、機率計算、積分、數列等容易出細微錯誤，而使用者會把解答當標準答案。一題錯的解答比沒有解答更糟。所以凡是**有確定答案**的題目，都用程式實際算一次。

## 做法

1. 寫完所有題目與初版解答後，建立一個 `verify.py`，每題一個函式，印出結果並和解答比對
2. 執行；不一致時找出原因：
   - 解答算錯 → 修正解答
   - 題目本身有歧義或無解 → 修改題目（改數字或補條件），再重新驗算
3. 全部通過後，在解答卡標頭加 `✓ 已驗算`；無法驗算的標 `無法程式驗算`

不需要把驗算程式碼放進 PDF；使用者要的是正確答案，不是驗算過程。

## 範本

比較邏輯已寫好在 `scripts/verify_helpers.py`，直接匯入，不用自己寫：

```python
import sys; sys.path.insert(0, "<skill-dir>/scripts")
from verify_helpers import check, is_eigvec, summary
import sympy as sp
from math import comb

# Q1 反矩陣
A = sp.Matrix([[1, 2], [3, 4]])
check("Q1", A.inv(), sp.Matrix([[-2, 1], [sp.Rational(3, 2), sp.Rational(-1, 2)]]))

# Q3 特徵值與特徵向量
B = sp.Matrix([[2, 1], [1, 2]])
check("Q3 eigenvalues", sorted(B.eigenvals()), [1, 3])
check("Q3 v(3)", is_eigvec(B, [1, 1], 3), True)

# Q5 是非題的反例確實成立
C = sp.Matrix([[1, 1], [0, 1]])
check("Q5 invertible but not diagonalizable", (C.det() != 0, C.is_diagonalizable()), (True, False))

# Q7 二項分布 P(X=2), n=5, p=0.3
p = sp.Rational(3, 10)
check("Q7", comb(5, 2) * p**2 * (1 - p)**3, sp.Rational(3087, 10000))

# Q8 近似值答案（解答寫 0.224）
check("Q8", sp.exp(-3) * 3**2 / 2, 0.224, tol=5e-4)

# Q9 積分 / 期望值
x = sp.symbols("x")
check("Q9", sp.integrate(x * 2 * x, (x, 0, 1)), sp.Rational(2, 3))

summary()   # ALL OK，或列出 MISMATCH 並以 exit code 1 結束
```

`check()` 可比較布林、字典、清單、集合、矩陣、符號式與數值；解答寫的是四捨五入值時，用 `tol` 設定容許誤差。
`is_eigvec(A, v, λ)` 確認 v 是 A 對應 λ 的非零特徵向量。

## 各類題目怎麼驗

| 題目類型 | 驗算方式 |
|---|---|
| 矩陣、行列式、秩、特徵值、RREF | `sympy.Matrix`：`.inv() .det() .rank() .eigenvals() .rref()` |
| 線性系統 | `sympy.linsolve` |
| 機率、組合 | 精確分數 `sp.Rational`、`math.comb`；複雜情況加蒙地卡羅模擬作為第二重檢查 |
| 分布的機率/期望/變異數 | `sympy.stats`（`Binomial`, `Normal`, `P`, `E`, `variance`）或 `scipy.stats` |
| 微積分 | `sp.diff`, `sp.integrate`, `sp.limit`, `sp.series` |
| 數值方法 | `numpy` |
| 程式追蹤題 | 實際執行程式碼（Python 直接跑；C 用 `gcc` 編譯） |
| 選擇題 | 對每個選項都算一次，確認恰好一個正確 |
| 是非題 | 錯誤敘述找一個具體反例並用程式確認 |

## 無法程式驗算時

證明題、申論、概念題無法用程式驗證。仍要自我檢查：
- 證明的每一步是否用到了題目給的條件（沒用到的條件常代表證明有漏洞）
- 用一個具體例子代入命題，確認命題本身是對的
- 標記 `無法程式驗算`，讓使用者知道這題要自己多留意
