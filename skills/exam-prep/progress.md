# exam-prep 進度與交接

開發用筆記，不會打包進 Release zip。上半部是**設計決策**（很少改），下半部是**現況與待辦**（每次改版更新）。

---

## 一、設計決策（使用者確認過的）

### 產出
- 輸出 **PDF**；題目和解答**分開**成兩份檔案
- 整理方式**可複選、每種一份 PDF**：章節講義（詳盡）、章節重點（精簡）、題型解題卡、Cornell 回憶筆記、分層講義；另有練習題、解答本、公式小抄
- **概念地圖永遠內建**：每份整理文件有全範圍總圖＋每章章節圖
- **能畫圖就畫圖**，統計科目尤其要多（`scripts/figures.py`）
- 三套主題可選：`modern`（預設）、`textbook`、`cheatsheet`（只用於公式小抄）
- 語言：繁中為主、術語中英並列；**練習題語言執行時讓使用者選**（跟考古題／中文／英文／中英對照）

### 內容規則
- 以使用者資料為主；資料以外的補充**必須**標 `{{補充}}` 或放 `:::extra`
- 考古題用法執行時讓使用者選，不寫死
- 計算答案用 SymPy 驗算並標「✓ 已驗算」；證明題標「無法程式驗算」；**整理文件裡的數字（例題、圖上數值、配分統計）也要驗**
- 適用所有科目，理工科自動加公式、計算題與驗算

### 執行流程（2.1.0 起）
- 原始資料只讀一次：`scripts/ingest.py` → 寫成標好出處的 `materials.md` → `concepts.md` → 各文件。之後不再重讀 PDF／圖片
- 只有文字抽不出來的頁面才看圖，多頁拼成低解析度 sheet；排版檢查用 `scripts/preview.py` 縮圖總覽
- 能派子代理的環境，資料多時把讀取交給子代理（一般 Claude.ai 沒有，會自動跳過）
- 瘦身原則：**搬移與重寫，不做電報式壓縮**（避免指示被誤讀）
- 指示不綁定特定工具名稱（「有提問工具就用，沒有就用文字問」）
- 支援 Claude.ai、Claude Code、**OpenAI Codex**（2.2.0 起）。有沙箱擋住網路的平台，執行環境用 `scripts/setup.py` 一次裝好（`--check` 只檢查），不在渲染時臨時安裝

### 輸入
- 投影片 PDF／PPTX、課本、手寫筆記照片、考古題、作業、DOCX
- Google Drive 連結（需連接器）；**產出不透過連接器上傳回 Drive**（PDF 太大，base64 會塞爆 context）

---

## 二、現況

- **最新版本：2.2.2**（2026-10-31，Windows 實測修正）；已發布 Release：`exam-prep-v2.0.0`、`exam-prep-v2.1.0`、`exam-prep-v2.2.1`、`exam-prep-v2.2.2`（2.2.0 沒有單獨發）
- 這個雲端環境的 git 代理不允許推 tag（HTTP 403），發版改用 GitHub Actions 手動觸發 Release workflow
- CI 綠燈：格式檢查＋三主題渲染＋ingest＋preview
- 檔案導覽：`SKILL.md`（約 3.2k tokens）→ `references/`（讀資料、語法、地圖、圖表、出題、驗算）→ `references/styles/`（五種整理方式各一份）

### 實測紀錄
- 1.x：線代（特徵值，英文投影片＋考古題）、機統（手機拍的筆記照片）完整跑過；抓到的問題都已修（選擇題雙正解、考古題配分算錯、標題孤立在頁尾等）
- 2.0：機統照片 → 題型解題卡／Cornell／分層講義三份 PDF，21 項數字驗算全過；抓到 `pmf_bar` 尾端機率漏算（已加警告與 `highlight_value`）
- 2.1：`ingest.py`、`preview.py` 單獨實測過（PDF、PPTX、DOCX、照片）
- 2.2：Codex 的規格是讀 `openai/codex` 原始碼確認的（skill 位置 `~/.codex/skills`、`~/.agents/skills`、專案 `.agents/skills`；frontmatter 只讀 `name`（≤64 字）與 `description`，其他欄位略過；會讀 `.claude-plugin/marketplace.json`）。`setup.py` 在全新 HOME 實測過：npm 套件與 Python 套件能裝、Chromium 下載在雲端環境被網路政策擋住（訊息正確）。**尚未在真的 Codex 上跑過**
- 2.2.1（Windows）：Linux 上用非 UTF-8 語系模擬 Windows：修正前中文 PDF 全部讀取失敗、報告輸出時程式中止；修正後正常
- 2.2.2（Windows 11 實機，MSI，Claude Code，Git Bash＋PowerShell，Python 3.11、Node 24）：`setup.py` 能裝 npm 套件、Chromium、Python 套件，✓／✗ 不會中止；smoke test 全過，三主題 PDF 中文正常（Noto Sans／Serif TC＋微軟正黑體），preview 頁碼標籤清楚；中文檔名＋中文資料夾的 PDF 在兩種 shell 都能 ingest。抓到並修正：Git for Windows 內附 xpdf 版 `pdftotext` 會吃掉中文（不報錯）、缺 poppler 時錯誤訊息看不懂、`validate_skills.py` 與 smoke test 的 cp950 問題。poppler 用 `winget install oschwartz10612.Poppler` 安裝成功（裝好後要開新終端機 PATH 才生效）

---

## 交接：下一步（2026-10-31）

上一個工作階段在雲端（Linux）做完 2.2.0／2.2.1 並發了 Release，接下來要在使用者的 **MSI（Windows）** 上用 Claude Code 實測。所有成果都在 main，沒有未合併的工作；`exam-prep-codex`、`exam-prep-2.1.1-windows` 兩個分支已合併，使用者說可以留著。

### 1. Windows 實測（2026-10-31 完成，結果見上方實測紀錄 2.2.2）

已發 `exam-prep-v2.2.2` Release（本機推 tag 正常）。以下保留原步驟供日後重測：

在 repo 根目錄依序執行，每一步記下結果：

```bash
git config user.name                                   # 必須是 PeanutGT
python skills/exam-prep/scripts/setup.py --check       # 列出缺什麼
python skills/exam-prep/scripts/setup.py               # 裝 npm 套件、Chromium、Python 套件
python skills/exam-prep/scripts/ingest.py skills/exam-prep/evals/la-eigen-full-package/files/la_pastexam_2024-2025.pdf --out %TEMP%/ing
python tools/smoke_test.py --out %TEMP%/smoke           # 三主題渲染＋ingest＋preview＋setup --check
```

（在 Git Bash 裡 `%TEMP%` 改用 `$TEMP`。）

通過標準：
- `setup.py --check` 不會因為 `✓`／`✗` 符號中止，缺的項目提示看得懂；poppler 用 `scoop install poppler` 或 conda 裝
- ingest 的 `report.md` 沒有「讀取失敗」，`text/la_pastexam_2024-2025.txt` 第一行是「線性代數 期中考 (2025 Fall) — Eigen 部分」
- 再拿一份**檔名含中文**的 PDF 測 ingest（要確認 Windows 版 poppler 能開中文路徑；這是 2.2.1 唯一沒辦法在 Linux 模擬的部分）
- smoke test 產出的 PDF 打開來中文正常、沒有方框（Chromium 在 Windows 會用微軟正黑體）
- `preview.py` 總覽圖上的頁碼標籤清楚（Windows 用 `arialbd.ttf`）

有問題就修、在 CHANGELOG 加 2.2.2，跑 `python tools/validate_skills.py` 與 smoke test 後再推。

### 2. 從 GitHub 安裝實測

- Claude.ai：Release 的 `exam-prep-2.2.1.zip` 上傳
- Claude Code：`/plugin marketplace add PeanutGT/NutsSkills` → `/plugin install exam-prep@nutsskills`
- Codex：`codex plugin marketplace add PeanutGT/NutsSkills` → `codex plugin install exam-prep@nutsskills`，再照下面「需要驗證」的 Codex 項目測

### 3. 還沒收尾的小事

- **Release 說明缺 Codex 的部分**：Release workflow 只擷取 CHANGELOG 的 2.2.1 段，2.2.0 沒單獨發過，所以 `exam-prep-v2.2.1` 頁面只有 Windows 修正。請使用者在 GitHub 編輯 Release，最前面補上 2.2.0（Codex 支援、`setup.py`、Codex 安裝指令）。之後若兩版合發，可以考慮讓 release.yml 擷取「上次 Release 之後的所有段落」
- 推 tag 的 403 只發生在雲端環境；在本機可以直接 `git tag exam-prep-vX.Y.Z && git push origin exam-prep-vX.Y.Z`

---

## 三、待辦

### 需要驗證
- [ ] **2.1.0 尚未端到端實跑**：用新流程（ingest → materials.md → 文件）從頭產出一整套，確認 Claude 確實不再重讀原始檔、輸出品質沒有退步。建議用資料結構期中考（Ch1–Ch4）實測
- [x] Windows 本機（Claude Code）實跑（2026-10-31，修正發為 2.2.2）
- [ ] **在真的 Codex 上實跑**：`codex plugin marketplace add` → `install`、`$exam-prep` 觸發、沙箱裡 `setup.py --check`、沙箱外安裝、Chromium 能不能在沙箱內啟動（不行就要核准在沙箱外渲染）

### 可做的改進
- [ ] **ChatGPT 網頁版相容**（使用者問過，尚未決定要不要做；Codex 已在 2.2.0 支援）：
  - 把 KaTeX、Mermaid 打包進 skill，免網路也能渲染（zip 約 50 KB → 5 MB）
  - 沒有 Chromium 時改輸出自含 HTML，讓使用者用瀏覽器列印成 PDF
  - README 加相容性表
- [ ] evals 只有 3 個案例，可加：純文字科目（非理工）、大量投影片（測子代理委派）、英文練習題
- [ ] description 觸發率尚未用 skill-creator 的 `run_loop.py` 最佳化（縮短後更值得測）

### 不做（已評估過）
- 一份外部「token 最佳化研究報告」建議的 IRT 適性測驗、FSRS 間隔重複、滾動式摘要、語意快取、vLLM、LTI：那份報告分析的是另一個同名專案（Candlest/exam-prep-skill，多輪互動式），不適用本 skill 的一次性產出架構；快取 TTL 由平台管理，skill 無法設定

---

## 四、變更紀錄

詳見 `CHANGELOG.md`。重點：1.0 基本複習包 → 1.1 學習講義、練習題語言、Google Drive → 2.0 五種整理方式、概念地圖、圖表、公開化（授權、CI、Release）→ 2.1 省 token（ingest、materials.md、preview、子代理、瘦身）
