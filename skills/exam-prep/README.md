# exam-prep

把學習資料整理成排版精美、可列印的 PDF，用來學懂教材或準備考試。

## 可以產出

| 文件 | 用途 |
|---|---|
| 學習講義 | 整合所有教材的詳盡講義：動機、定義、直觀解釋、定理與證明、完整例題、章末自我檢測 |
| 重點整理 | 考前快速回顧：定義、定理、易錯、常考標記、考古題出題分析 |
| 練習題 | 題型、難度、作答空白；可模仿考古題；中文／英文／中英對照可選 |
| 解答本 | 與練習題分開；寫出解題思路，計算題用 SymPy 驗算並標「✓ 已驗算」 |
| 公式小抄 | 雙欄高密度，一頁看完 |

三套主題：現代筆記風、教科書風、精簡小抄風。

## 支援的輸入

投影片 PDF／PPT、課本章節、手寫或手機拍的筆記照片、考古題、作業；可直接上傳，或給 Google Drive 檔案／資料夾連結（需連接 Google Drive）。

## 使用方式

安裝後直接對 Claude 說，例如：

- 「下週四線代期中考，附上講義和考古題，幫我整理重點、出 12 題練習題」
- 「這是機統的上課投影片，幫我整理成一份學習講義」

Claude 會先讀完資料，再詢問範圍、要哪些文件、主題、題型與語言等，然後產出 PDF。

## 執行需求

- Node.js（渲染用；`katex`、`marked`、`playwright` 缺少時會自動安裝到 `~/.exam-prep-deps`）
- Chromium（Playwright 使用）、Noto Sans/Serif CJK TC 字型
- Python 3 + `sympy`（驗算用）
- `pdftoppm`（poppler，排版檢查用）

## 檔案

- `SKILL.md` — skill 本體
- `scripts/render.mjs` — Markdown → 主題化 PDF
- `scripts/verify_helpers.py` — 驗算比較工具
- `assets/themes/` — 主題樣式
- `references/` — 撰寫語法、出題指南、驗算流程、輸入資料讀取方式
- `evals/` — 測試案例
