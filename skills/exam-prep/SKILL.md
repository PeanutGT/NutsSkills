---
name: exam-prep
description: 把講義、投影片、課本、手寫筆記照片、考古題（可上傳或給 Google Drive 連結）重新組織成排版精美的複習 PDF：學習講義、重點整理、題型解題卡、Cornell 回憶筆記、分層講義、練習題與驗算過的解答、公式小抄，附概念地圖與圖表。使用者提到期中考、期末考、小考、複習、整理重點、整理教材、做講義、出練習題、考古題、study guide、exam prep、cheat sheet，或丟了課堂資料想學懂或準備考試時使用。
license: Apache-2.0
compatibility: 需要可執行程式碼的環境（Claude.ai 需開啟程式碼執行；Claude Code、Codex 可直接使用），並能安裝 npm 與 pip 套件。渲染需要 Node.js 18+ 與 Chromium（Playwright），讀取與檢查需要 poppler，圖表與驗算需要 Python 3（matplotlib、sympy、scipy）。
metadata:
  version: "2.2.2"
  author: PeanutGT
  repository: https://github.com/PeanutGT/NutsSkills
---

# Exam Prep — 學習講義與考試複習包產生器

把使用者的學習資料**重新組織**成「印出來就能讀、寫、對答案」的 PDF。特色不是照章節重寫教材，而是：先做概念分析（前置依賴、出處、考古題頻率），再依需求重組知識；每份整理文件都有概念地圖、能畫圖的就畫圖；數字全部用程式驗算。

## 可產出的文件

| 文件 | kind | 檔名 | 用途 |
|---|---|---|---|
| 章節講義（詳盡） | `handout` | `<科目>_學習講義.pdf` | 第一次學、沒聽懂時從頭讀 |
| 章節重點（精簡） | `notes` | `<科目>_重點整理.pdf` | 學過了，考前回顧 |
| 題型解題卡 | `patterns` | `<科目>_題型解題卡.pdf` | 依考試題型重組：辨識 → SOP → 範例 → 陷阱 |
| Cornell 回憶筆記 | `cornell` | `<科目>_回憶筆記.pdf` | 遮住右欄自我測驗 |
| 分層講義 | `layered` | `<科目>_分層講義.pdf` | 30 秒／5 分鐘／完整三層 |
| 練習題 | `practice` | `<科目>_練習題.pdf` | 題目卡，含題型、難度、作答空白 |
| 解答本 | `answers` | `<科目>_解答.pdf` | 與練習題分開，計算題標「✓ 已驗算」 |
| 公式小抄 | `cheatsheet` | `<科目>_公式小抄.pdf` | 雙欄高密度，一頁看完 |

前五種是「整理文件」，可複選、每種一份 PDF，共用同一份概念分析所以彼此一致。整理文件與小抄以繁體中文為主，**術語第一次出現時中英並列**，例如「特徵值 (eigenvalue)」；練習題語言由使用者選。

## 工作流程

`<skill-dir>` 指這份 SKILL.md 所在的資料夾，`scripts/`、`references/` 都相對於它。

### 0. 環境（第一次使用，或出現缺套件、無法連網、沒有寫入權限的錯誤時）

```bash
python <skill-dir>/scripts/setup.py --check   # 只檢查，不安裝，離線也能跑
```

有缺的就執行 `python <skill-dir>/scripts/setup.py` 安裝（需要網路）。有沙箱的代理環境（例如 Codex 預設不能連網、不能寫入工作資料夾以外的地方）要請使用者核准在沙箱外執行，或請使用者自己在終端機跑一次。poppler、Node.js 無法自動安裝，照檢查結果的提示請使用者安裝。

### 1. 讀資料：只讀一次，整理成 materials.md

照 `references/reading-inputs.md` 做：先跑 `scripts/ingest.py`，它會抽出所有文字、只挑出真正需要看圖的頁面拼成低解析度的總覽圖，再寫一份標好出處的 `materials.md`。**之後所有步驟只用 `materials.md` 和 `concepts.md`，不再回頭讀原始 PDF 或圖片**，也不要逐頁轉圖片來看。

- **能派出子代理的環境**，資料超過約 30 頁或要看的總覽圖超過 8 張時，把這一步交給子代理，只拿回 `materials.md` 的路徑與摘要（做法見 reading-inputs.md 第 3 節）；不能派就自己做
- 資料在 Google Drive（貼了 `drive.google.com`／`docs.google.com` 連結，或說「在我雲端的某資料夾」）：用 Google Drive 連接器，見 reading-inputs.md 的 Drive 一節
- 先讀完再問問題，因為「範圍」的選項應該是資料裡真的有的章節

### 2. 詢問使用者

有提問工具（例如 AskUserQuestion）就用選項卡，每輪最多 4 題；沒有就用一段文字列出問題。**使用者已經講清楚的項目跳過**，只問和這次產出有關的，超過 4 題就分到下一輪。說「整理教材」「做成講義」「從頭整理」＝已選章節講義；說「題型」「解題技巧」＝已選題型解題卡。

**第一輪**
1. **範圍** — 資料中的實際章節名（可複選）＋「全部」
2. **整理方式**（可複選）— 章節式（講義或重點）／題型解題卡／Cornell 回憶筆記／分層講義；說明欄各用一句話寫適合誰。有考古題時推薦題型解題卡
3. **其他文件**（可複選）— 練習題＋解答／公式小抄／都不需要
4. **主題** — 現代筆記風 `modern`（推薦）／教科書風 `textbook`／精簡小抄風 `cheatsheet`（只套用在公式小抄，其他文件選它時改用教科書風）

**第二輪**（只問相關的）
5. **章節式詳細程度**（選了章節式）— 詳盡學習講義／精簡重點整理／兩份都要
6. **考古題用法**（有考古題，可複選）— 標出常考／練習題模仿考古題／逐題詳解考古題
7. **題型與題數**（要練習題）— 例如「混合 15 題（推薦）」「選擇是非為主 20 題」「計算＋證明為主 10 題」；證明、計算只給理工科
8. **難度與考試日期** — 基礎／混合（推薦）／挑戰；日期用 Other 填或選「不確定」
9. **練習題語言**（要練習題）— 跟考古題一樣（有考古題時推薦，說明欄寫出考古題實際語言）／中文／英文／中英對照。沒有考古題時第一個選項改成「和講義相同」

**沒人可問時的預設**：範圍全部；整理方式＝章節重點，有考古題再加題型解題卡（明顯是要學懂教材時改為學習講義）；另加練習題＋解答；`modern`；混合 12–15 題；難度 4：4：2；考古題兩種用法都做；練習題語言跟考古題（沒有就中文）。回覆開頭一句話說明用了哪些預設。

**考試日期**：≤ 3 天 → 重點精簡、優先常考，建議加小抄或分層講義；選了學習講義照做，但提醒「時間緊可先讀重點」。≥ 14 天 → 可多寫推導與延伸。

### 3. 概念分析（不可省略）

從 `materials.md` 整理出 `concepts.md`：每個概念的類型、**前置概念**、出處、考古題次數、考試題型。格式見 `references/organize-styles.md` 第 1 節。它決定講解順序（前置在前）、概念地圖、`{{前置: …}}` 徽章、常考標記與解題卡分組，以及**每個概念要畫什麼圖**（有形狀、分布、流程、空間關係的就畫）。寫完文件後對照它逐項檢查有沒有漏。

### 4. 寫整理文件

先讀 `references/markdown-format.md`（所有語法），再**只讀這次要產出的整理方式**：`references/styles/` 裡的 `handout.md`（章節講義）、`notes.md`（章節重點）、`patterns.md`（題型解題卡）、`cornell.md`（Cornell）、`layered.md`（分層講義）。

每份整理文件都要有：
- **概念地圖**：第一個 `##` 前一張全範圍總圖，每章開頭一張章節圖（organize-styles 第 2 節）
- **圖表**：用 `scripts/figures.py` 產生 SVG 放進 `:::fig`，統計科目尤其要多；見 `references/figures.md`
- **來源規則**：以使用者資料為主；資料以外的補充一律放 `:::extra` 或加 `{{補充}}`
- 標題不手動編號；多份文件用同樣的符號與例子

### 5. 練習題與解答

見 `references/question-design.md`。題目依「重要性 × 常考程度」分配；有解題卡時每種題型至少一題並標出題型；不和講義例題、自我檢測、解題卡範例重複；兩份文件題號一致；計算與證明題加 `space=N`；解答先寫思路再算。

### 6. 驗算（不可省略）

```bash
pip install --break-system-packages -q sympy numpy scipy matplotlib 2>/dev/null
```

用 `scripts/verify_helpers.py`（`check`、`is_eigvec`、`summary`）寫一份 `verify.py`，流程見 `references/verification.md`。每個有確定答案的題目都重算，不符就修正解答或題目；通過標 `✓ 已驗算`，證明與申論標 `無法程式驗算`；選擇題確認恰好一個選項正確。**整理文件裡的數字也要驗**：例題結果、圖上標的數值、考古題配分統計。

### 7. 渲染

```bash
node <skill-dir>/scripts/render.mjs patterns.md 線性代數_題型解題卡.pdf --theme modern
```

公式小抄一律 `--theme cheatsheet`，其他文件用使用者選的主題（選了 cheatsheet 則用 textbook）。缺少的 npm 套件與 Chromium 會自動安裝；環境已有全域安裝時先設 `NODE_PATH`。出現 `mermaid error` 代表某張圖語法錯誤（常見：節點文字含未加引號的括號、用了 LaTeX）。`--html out.html` 可保留中間 HTML 除錯。

### 8. 檢查排版，再交付

```bash
python <skill-dir>/scripts/preview.py out/線性代數_題型解題卡.pdf          # 整份縮圖總覽（每張最多 12 頁）
python <skill-dir>/scripts/preview.py out/線性代數_題型解題卡.pdf --page 5 # 只放大有問題的頁
```

先看總覽找版面問題，只放大看起來有問題的頁；**不要逐頁轉圖片看**，文字內容在 Markdown 裡校對。常見問題：公式顯示成紅色原始碼（KaTeX 不支援，改寫）；概念地圖擠成一長條或文字被截（減少節點、換 TD/LR、拆成兩張）；圖表標籤重疊；表格或公式超出頁寬（拆開或用 `aligned`）；幾乎空白的頁（卡片或圖太高，調整或拆開）。

交付 PDF 時用一兩句話說明涵蓋範圍、每份頁數或題數、有幾題無法程式驗算、`materials.md` 裡「不確定的地方」有哪些需要使用者確認。把檔案交給使用者（有傳檔工具就用，沒有就告訴使用者檔案路徑），不要在對話中重述文件內容。

## 檔案

- `scripts/ingest.py` 讀資料與挑出需要看圖的頁　`scripts/render.mjs` Markdown → PDF　`scripts/preview.py` 排版總覽　`scripts/figures.py` 教學圖表　`scripts/verify_helpers.py` 驗算工具　`scripts/setup.py` 檢查與安裝執行環境
- `references/reading-inputs.md` 讀資料、materials.md、子代理、Google Drive
- `references/markdown-format.md` 撰寫語法（寫 Markdown 前必讀）
- `references/organize-styles.md` 概念分析與概念地圖（共同基礎）　`references/styles/*.md` 五種整理方式各自的寫法
- `references/figures.md` 圖表　`references/question-design.md` 出題與語言　`references/verification.md` 驗算
