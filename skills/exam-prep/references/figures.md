# 圖示指南

圖不是裝飾。一張好的教學圖，要讓讀者「看一眼就懂」一個用文字要講三段的事情。

## 什麼時候要畫圖

每個概念都問：**這個東西有形狀、有分布、有流程、有空間關係嗎？** 有就畫。

| 內容 | 該畫的圖 | 工具 |
|---|---|---|
| 概念之間的依賴 | 概念地圖 | Mermaid（`:::map`） |
| 解題流程、決策（選哪個檢定、能否對角化） | 流程圖／決策樹 | Mermaid `flowchart LR` |
| 多階段機率、條件機率 | 機率樹 | Mermaid `flowchart LR`，邊上標機率 |
| 時間順序、演算法步驟 | 流程圖 | Mermaid |
| 離散分布（Binomial、Poisson、Geometric…） | 機率質量長條圖，事件用顏色標出 | `figures.pmf_bar` |
| 連續分布、機率 = 面積 | 密度曲線＋陰影面積 | `figures.pdf_area` |
| 近似（Binomial ≈ Poisson、CLT）、參數比較 | 2–3 條並列 | `figures.compare_curves` |
| CDF | 階梯圖（開/閉端點） | `figures.cdf_step` |
| 樣本資料的分布 | 直方圖（可疊上理論密度） | `figures.histogram` |
| 四分位數、IQR、離群值 | 標註式盒鬚圖 | `figures.boxplot_annotated` |
| 相關、迴歸、殘差 | 散佈圖＋迴歸線（可畫殘差） | `figures.scatter_regression` |
| 事件關係、排容原理 | 文氏圖 | `figures.venn2` |
| 線性變換、特徵向量、基底 | 變換前後對照圖 | `figures.linear_map_2d` |
| 函數、極限、導數、積分 | 函數圖 | `figures.function_plot` |
| 電路、電子、數位邏輯 | 電路圖、邏輯閘圖 | `figures.schematic`（schemdraw，見下方） |
| 圖論、樹、狀態機 | 節點與邊 | Mermaid `flowchart`／`stateDiagram-v2` |
| 力圖、幾何圖形 | 用 matplotlib 畫 | `figures._setup()` 後自己畫 |
| 其他 | 用 matplotlib 自己畫，但沿用 `figures.py` 的配色與 `_setup()` | — |

統計科目尤其要多用圖：每個分布至少一張圖，每個檢定的拒絕域用 `pdf_area` 畫出來，每個描述統計量（平均、中位數、IQR、標準差）都在圖上標出它在哪裡。

## 怎麼畫

```python
import sys; sys.path.insert(0, "<skill-dir>/scripts")
import figures as F
from scipy.stats import binom, norm

F.pmf_bar(range(11), [binom.pmf(k, 10, .3) for k in range(11)], "figs/binom.svg",
          highlight=lambda k: k <= 2, highlight_label="P(X ≤ 2)", mean=3, xlabel="命中次數 k")
F.pdf_area(norm.pdf, (-3.5, 3.5), "figs/z95.svg", shade=(-1.96, 1.96), shade_label="95%",
           marks={-1.96: "−1.96", 1.96: "1.96"}, xlabel="z", ylabel="φ(z)")
F.linear_map_2d([[2, 1], [1, 2]], "figs/eigen.svg", vectors={"v₁": (1, 1), "v₂": (1, -1)})
```

- 圖檔存在 Markdown 同一層的 `figs/` 資料夾，用相對路徑引用；渲染器會自動解析
- 所有函式都輸出 SVG（文字保持清晰）；各函式參數見 `scripts/figures.py` 的 docstring
- 需要 `matplotlib`、`numpy`，統計分布用 `scipy.stats`：`pip install --break-system-packages -q matplotlib scipy`

放進文件：

```markdown
:::fig Binomial(10, 0.3)：橘色長條的總和就是 P(X ≤ 2)
![](figs/binom.svg)
:::
```

- 圖會自動編號（圖 1、圖 2…），內文可寫「見圖 3」
- **圖說要說出重點**，不是只寫圖名：寫「橘色面積 = 95%，所以兩側各剩 2.5%」，而不是「標準常態分布」

Mermaid 機率樹範例：

````markdown
```mermaid
flowchart LR
  S(( )) -- "0.01" --> D["有病"]
  S -- "0.99" --> H["健康"]
  D -- "0.95" --> DP["陽性<br/>0.0095"]:::hot
  D -- "0.05" --> DN["陰性<br/>0.0005"]
  H -- "0.10" --> HP["陽性<br/>0.099"]:::hot
  H -- "0.90" --> HN["陰性<br/>0.891"]
```
````

## 電路圖

電路、電子、數位邏輯的題目常常「沒有圖就無法作答」，所以題目要附圖（規則見 question-design.md 的「需要圖的題目」）。用 `figures.schematic`，底層是 schemdraw（`setup.py` 會安裝；手動裝：`pip install --break-system-packages schemdraw`）：

```python
import schemdraw.elements as elm
with F.schematic("figs/q3.svg") as d:
    F.V(20).up()                                  # + 在畫的方向的終點（.up() → + 在上）；.reverse() 反過來
    F.R(1, "R₁").right()
    n1 = elm.Dot().label("v₁", loc="top"); d.push()
    F.R(2).down()
    d.pop()
    r4 = F.R(4).right().label("i →", loc="bottom")
    elm.Dot().label("v₂", loc="top")
    elm.Line().right()
    F.Vdep(lambda c: 2 * c.i(r4), "2i", loc="bottom").down().reverse()   # 相依電源：值由其他元件的電流／電壓算
    elm.Line().left(); elm.Line().left(); elm.Ground(); elm.Line().left()

c = F.solve_circuit(d)              # 直接解「畫出來的」電路（節點分析，精確分數）
check("Q3 v1", c.vat(n1), 12)       # 寫進 verify.py
check("Q3 i", c.i(r4), 2)
```

- **有數值的元件一律用 `F.R`／`F.V`／`F.I`／`F.C`／`F.L`／`F.Vdep`／`F.Idep` 畫**（會自動標上「6 Ω」「R₁ = 1 Ω」），再用 `F.solve_circuit(d)` 驗算解答：`c.i(el)` 是沿著畫的方向流過元件的電流（`.right()` 由左到右、`.down()` 由上到下），`c.v(el)` 是起點減終點的電壓，`c.p(el)` 是吸收功率（負的是提供），`c.vat(dot)` 是某個點對接地符號的電壓。直流穩態下電容當開路、電感當短路
- 為什麼不自己列方程式驗：電源畫反、少一段導線時，手寫的方程式照樣「驗算通過」，但學生看到的圖算出來是別的答案。從圖解就不會有這個落差
- 畫完時 `F.schematic` 會檢查有沒有懸空的端點（多半是少畫一段導線），有就發出警告；刻意留的端子（例如求 a、b 兩端的戴維寧等效）可以忽略
- 其他元件：`Switch`、`Diode`、`Opamp`、`BjtNpn`…（用 `elm.` 畫，`solve_circuit` 不支援，要自己驗）；邏輯閘在 `schemdraw.logic`（`And`、`Or`、`Not`、`Nand`…）
- 標籤用一般文字加 Unicode 下標（R₁、Vₛ、μF）；含中文的標籤不要用 `$...$`，中文會消失
- 標籤放在電路外側：直向元件預設標在左邊，最右邊的支路用 `loc="bottom"` 標到右邊。並聯支路至少隔一個單位寬，標籤才不會疊在一起
- 題幹提到的節點名稱（a、b）、電流方向、電壓極性、開關狀態都要畫出來

```markdown
:::q 3 | 計算題 | ★★☆ | space=6
如圖所示電路，求穩態時的電流 $i$。

![](figs/q3.svg)
:::
```

## 設計規則（已內建在 figures.py，自己畫圖時也要遵守）

- **顏色有固定角色**：藍 `#2a78d6` 是主要資料；橘 `#eb6834` 是「被強調的事件／對照組」；綠 `#1baf7a` 是第三組或特殊方向（例如特徵方向）。同一份文件中顏色意義保持一致
- **一張圖最多 3 組資料**；更多就拆成多張並排
- **只有一個 y 軸**；兩種單位不同的量畫成兩張圖
- 直接在線的末端標名稱，少用圖例框；文字用深灰，不用資料的顏色
- 格線淡、線條 2px、長條之間留白
- 圖上的數字要正確：圖中標的機率、平均、迴歸係數，同樣要寫進 `verify.py` 驗算

## 檢查

渲染後看每一張圖：標籤有沒有互相重疊、文字有沒有被裁掉、陰影區域是否就是題目問的事件、顏色意義是否和圖說一致。電路圖再確認元件數值和題幹一致、電源極性和箭頭方向和解答一致、標籤沒有壓在元件或導線上、每條導線都有接上。
