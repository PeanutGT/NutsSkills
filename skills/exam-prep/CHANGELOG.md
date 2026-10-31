# exam-prep 更新紀錄

格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，版本號遵循 [語意化版本](https://semver.org/lang/zh-TW/)。

## [2.3.0] - 2026-10-31

整本課本不再整本讀進來。

### 新增
- `ingest.py`：超過 150 頁的 PDF（`--book-pages` 可調）當成整本書，不抽全文，改寫 `text/<檔名>-outline.md`：由 PDF 書籤整理的目錄，每章附 PDF 頁碼範圍；沒有書籤時給前 30 頁的文字（印出來的目錄通常在這裡）。實測一本 1,345 頁的課本：原本 80 秒、抽出約 230 萬字（約 70 萬 tokens），現在幾秒內完成、目錄約 20 KB
- `ingest.py`：`"檔案.pdf:起-迄,起-迄"` 只讀指定頁（PDF 頁碼），PPTX 也適用；輸出檔名帶範圍，同一本書可分段讀。超出總頁數時報告會提醒

### 變更
- SKILL.md、reading-inputs.md：「先讀完再問範圍」對整本課本改為先用目錄問範圍，再只讀選定章節
- smoke test 加測整本書模式與範圍讀取

## [2.2.2] - 2026-10-31

在 Windows 11（Claude Code）上實測後的修正。

### 修正
- `ingest.py`：Git for Windows 內附 xpdf 版的 `pdftotext`，在 Git Bash 和 PowerShell 裡都排在 poppler 前面。xpdf 預設輸出 Latin-1，中文會整段消失（不會報錯），數學符號也會變亂碼。現在 poppler 工具一律優先取用和 `pdfinfo` 同資料夾的那一份，並明確指定 `-enc UTF-8`
- `ingest.py`：沒裝 poppler 時，報告寫「找不到 pdfinfo，請安裝 poppler」，不再是看不懂的「[WinError 2] 系統找不到指定的檔案」
- `setup.py --check`：認出 xpdf 版 `pdftotext` 並標 ✗（原本誤判為 ✓），用和 `ingest.py` 相同的方式找 poppler

### 變更
- Windows 安裝 poppler 的提示改以 `winget install oschwartz10612.Poppler` 為主（Windows 11 內建 winget），並提醒裝好後要重開終端機
- smoke test：子程序輸出改以 UTF-8 解碼（原本在 cp950 下讀取執行緒會丟例外）；ingest 多檢查考古題的中文確實有抽出來
- `tools/validate_skills.py`：在 cp950 主控台印 ✓／✗ 會中止，stdout 改為 UTF-8

## [2.2.1] - 2026-10-30

Windows 相容性修正。

### 修正
- `ingest.py`：在 Windows 繁中環境（cp950）讀不了含中文的 PDF／DOCX——poppler 與 pandoc 輸出 UTF-8，但 Python 預設用系統語系解碼，每份檔案都會變成「讀取失敗」；現在固定以 UTF-8 解碼
- `ingest.py`、`preview.py`：輸出被導向時（例如 Claude Code 執行指令），報告中的 `↳` 等符號在 cp950 無法輸出，程式會在最後中止；stdout 改為 UTF-8
- `preview.py`：PDF 資訊同樣固定以 UTF-8 解碼

### 變更
- 總覽圖的頁碼標籤字型加入 Windows、macOS 的路徑；都找不到時改用 22px 的內建字型（原本是 10px）
- 找 LibreOffice 時也檢查 Windows、macOS 的預設安裝位置（通常不在 PATH 裡），`ingest.py` 與 `setup.py` 一致
- README 執行需求補上各平台安裝 poppler 的方式
## [2.2.0] - 2026-10-30

支援 OpenAI Codex。

### 新增
- `scripts/setup.py`：`--check` 列出缺少的執行環境（Node.js、npm 套件、Chromium、Python 套件、poppler、中文字型），不安裝、離線也能跑；不加參數則一次裝好能自動安裝的部分。Codex 預設沙箱不能連網、不能寫入專案以外的地方，可以先在終端機跑一次
- `agents/openai.yaml`：Codex 介面顯示的名稱、簡介與預設提示
- README 加入 Codex 的安裝方式（plugin marketplace 或複製到 `~/.codex/skills/`）

### 變更
- SKILL.md 加入「0. 環境」步驟，並說明 `<skill-dir>` 是 SKILL.md 所在的資料夾
- `render.mjs`：npm 套件裝不起來時（沒有網路或沙箱擋住）直接說明原因並指向 `setup.py`，不再丟出一長串 npm 錯誤
- 交付檔案與 Google Drive 的說明不再假設一定有傳檔工具或連接器，沒有時改給檔案路徑、請使用者把檔案放進工作資料夾

## [2.1.0] - 2026-10-29

減少 token 用量：原始資料只讀一次、只看真正需要看的頁面、只載入需要的說明。

### 新增
- `scripts/ingest.py`：一次讀完所有資料（PDF、PPTX、DOCX、照片、文字檔），抽出文字並自動判斷哪些頁面需要看圖（掃描頁、公式被拆碎、圖表、照片），只把這些頁面以低解析度拼成總覽圖；PPTX 的講者備註也會讀進來
- `materials.md` 流程：讀完寫成一份標好出處的整理稿，之後所有文件都只根據它與 `concepts.md` 撰寫，不再重讀原始檔
- `scripts/preview.py`：整份 PDF 拼成縮圖總覽檢查排版，只放大有問題的頁
- 能派出子代理的環境（Claude Code、Claude app 的代理式工作環境），資料多時把讀取工作交給子代理，主對話只拿回整理結果

### 變更
- description 縮短約一半（每個對話都會載入的部分）
- SKILL.md 從約 4,900 降到約 3,200 tokens；五種整理方式的寫法拆到 `references/styles/`，只讀這次要產出的那幾份
- 指示改用一般說法（「有提問工具就用，沒有就用文字問」），不綁定特定工具名稱

## [2.0.0] - 2026-10-25

### 新增
- **整理方式可複選，每種一份 PDF**：題型解題卡（依考試題型重組：辨識 → SOP → 範例 → 陷阱）、Cornell 回憶筆記（左欄提示、右欄答案）、分層講義（30 秒／5 分鐘／完整）
- **概念分析**：寫文件前先整理每個概念的前置依賴、出處、考古題出現次數；講解順序依依賴關係排列
- **概念地圖**：每份整理文件都有全範圍總圖與每章章節圖（Mermaid）
- **教學圖表**：`scripts/figures.py`（分布長條圖、機率面積、直方圖、盒鬚圖、迴歸、文氏圖、線性變換、函數圖）
- 找不到 Chromium 時自動嘗試安裝，失敗時給出明確的處理方式

### 變更
- 執行時的詢問改為「整理方式」與「章節式詳細程度」分開問
- 圖上的數值也納入驗算；`pmf_bar` 在被標示的機率有尾巴沒畫進圖時會警告

## [1.1.0] - 2026-10-24

### 新增
- 學習講義（詳盡、可自學的章節講義）
- 練習題語言可選：跟考古題一樣／中文／英文／中英對照
- 支援 Google Drive 檔案與資料夾連結作為輸入

## [1.0.0] - 2026-10-24

### 新增
- 第一版：重點整理、練習題、獨立解答本、公式小抄
- 三套主題（現代筆記風、教科書風、精簡小抄風）
- KaTeX 數學公式排版、計算題 SymPy 驗算
