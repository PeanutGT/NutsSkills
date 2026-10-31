# 讀取學習資料：整理一次，之後只用整理好的檔案

原則：**原始資料只讀一次**。讀完寫成 `materials.md`，之後的概念分析、每一份文件都只根據 `materials.md` 和 `concepts.md` 寫，不再回頭讀 PDF 或圖片。一次產出好幾份文件時，這樣最省，也能確保每份文件用的內容一致。

寧可讀完，不要只看前幾頁就開始寫——漏掉的章節使用者考試時會遇到。唯一的例外是整本課本（見第 1 節最後）：先問範圍，再把範圍內讀完。

## 1. 執行 ingest

```bash
python <skill-dir>/scripts/ingest.py <所有資料檔> --out ingest/
```

支援 PDF、PPTX、DOCX、Markdown／文字檔、照片。它會：
- 逐頁抽出文字層，存成 `ingest/text/<檔名>.txt`（每頁有 `=== 檔名 p.N ===` 標記，PPTX 連講者備註一起）
- 判斷**哪些頁面需要看圖**：掃描頁、公式被拆碎、含 PDF 公式字元、以圖為主的頁面、照片
- 只把這些頁面用低解析度渲染，每 4 張投影片（或 2 頁直式頁面）拼成一張 `ingest/sheets/*.png`
- 寫一份 `ingest/report.md`，列出每個檔案要讀哪些文字、看哪些 sheet

**先讀 `report.md`**，再讀 `text/`，然後**只看** report 列出的 sheets。沒列出的頁面文字層已經夠用，不要再逐頁轉圖片看——一頁一頁看圖片，每頁大約要 1,000–1,500 tokens。

如果某張 sheet 上的公式小到看不清，只針對那一頁放大：
`pdftoppm -r 110 -f N -l N -png -singlefile file.pdf page_N`，再看 `page_N.png`。

**整本課本**：超過 150 頁的 PDF（`--book-pages` 可改）在報告中標為「整本書」，ingest 不抽全文，只寫 `text/<檔名>-outline.md`：PDF 書籤整理成的目錄，每章附 PDF 頁碼範圍（沒有書籤時改給前 30 頁的文字，目錄通常在那裡）。一本 1,000 頁的課本全文約 50–70 萬 tokens，讀不完也用不著。

1. 讀目錄，把章名列進第 2 步的「範圍」選項，和講義、考古題涵蓋的章節對照推薦
2. 使用者選好後，只讀那幾章（頁碼用 PDF 頁碼，可用逗號接多段；路徑含空格時整個加引號）：
   ```bash
   python <skill-dir>/scripts/ingest.py "課本.pdf:24-55,120-160" --out ingest/
   ```
3. 選定的章節照樣讀完、寫進 `materials.md`；超過約 30 頁就照第 3 節交給子代理

沒有書籤、只有前幾頁文字時，目錄上印的是書本頁碼，和 PDF 頁碼通常差一個固定值：抽一頁（`pdftotext -f 40 -l 40 課本.pdf -`）對照章名就能換算。

## 2. 寫 materials.md

把讀到的內容寫成一份忠實、完整、標好出處的整理稿。**這不是摘要**：定義、定理、公式、例題、老師的說法都要留下，只是去掉版面雜訊並修好公式。

```markdown
# Materials

## Ch5 特徵值與特徵向量（la_slides_ch5.pdf p.2–3）
- 定義：$A\mathbf x=\lambda\mathbf x$，$\mathbf x\neq\mathbf 0$ … [la_slides_ch5 p.2]
- 定理 1：三角矩陣的特徵值是對角線元素 [la_slides_ch5 p.2]
- 例：$A=\begin{pmatrix}2&3\\3&-6\end{pmatrix}$，特徵值 $3,-7$（附推導）[la_slides_ch5 p.3]
- 老師強調：… [筆記照片] / [ch4.pptx 講者備註 p.1]

## 考古題
- 2025 Q2（15%）：判斷上三角矩陣可否對角化 → 概念：對角化判準；題型：判斷可否對角化 [la_pastexam p.1]

## 不確定的地方
- 筆記照片第 3 行的指數看不清，可能是 $p^2$ 或 $p^3$（需要請使用者確認）
```

- 每一條都標出處 `[檔名 p.N]`，之後寫文件時才查得到、也能標 `{{補充}}`
- 公式一律寫成 LaTeX；PDF 文字層破碎的公式，以 sheet 上看到的為準重寫
- 看不清楚或互相矛盾的地方集中列在「不確定的地方」，交付前向使用者確認關鍵數值
- 寫完後刪除不再需要的中間輸出也可以，但 `materials.md` 要保留到最後

## 3. 資料很多時：交給子代理

**能派出子代理的環境**（例如 Claude Code、Claude app 的代理式工作環境），資料超過約 30 頁、或需要看的 sheet 超過 8 張時，把步驟 1–2 交給子代理做，主對話就不會塞滿原始內容：

- 給子代理：資料檔路徑、這份 `reading-inputs.md` 的路徑（請它先讀）、輸出路徑 `materials.md`
- 要求它只回報：`materials.md` 的路徑、章節清單與頁數、「不確定的地方」——**不要把整理內容貼回來**
- 資料非常多時可依檔案分給幾個子代理，各寫 `materials-<n>.md`，最後由主對話合併（只合併標題與條目，不重讀原始檔）

**不能派子代理的環境**（例如一般 Claude.ai 聊天）就自己做步驟 1–2，效果一樣，只是主對話會比較長。

## 各類資料的補充說明

- **PDF**：ingest 已處理。沒有 poppler 時：`pip install --break-system-packages pdfplumber` 改用 pdfplumber 抽文字
- **PPTX**：公式常是圖片或 OLE 物件，ingest 會標出這些投影片；需要 LibreOffice（`soffice`）才能轉成圖片。沒有的話請使用者另存成 PDF 上傳
- **DOCX**：ingest 用 pandoc 轉文字；含 Word 方程式時會提醒，可請使用者另存 PDF
- **手寫筆記、照片**：ingest 會縮小到適合閱讀的大小。辨識不確定的字或符號列進「不確定的地方」，不要自行猜測關鍵數值；照片太暗或歪斜看不清時，可用 Pillow 調亮、轉正後再看。手寫筆記和講者備註常反映**老師上課特別強調的地方**，要優先保留

## 考古題、作業

除了讀內容，還要分析：
- 每題考的概念（對應到內容地圖）
- 題型（選擇、計算、證明…）與大致難度
- 出現頻率：多份考古題中重複出現的概念 → `{{常考}}`
- 出題風格：數字複雜度、中英文、是否偏重推導或計算

如果考古題附有答案，可用來校準解答風格；如果沒有，「逐題詳解」時就要自己解並驗算。

## Google Drive 上的資料

使用者常常直接貼 Drive 連結、說「在我 Drive 的線代資料夾」，或丟同學分享的檔案。

### 1. 確認連接器

Google Drive 工具名稱是 `mcp__Google_Drive__*`（可能需要先用 ToolSearch 載入）。如果完全找不到，用 SearchMcpRegistry 搜尋 `["google drive"]`，再用 SuggestConnectors 讓使用者一鍵連接；同時告訴他也可以先把檔案下載後直接上傳到對話。沒有這些工具的平台（例如 Codex）就請使用者把檔案下載到工作資料夾。

### 2. 找到檔案 ID

| 使用者給的東西 | 做法 |
|---|---|
| `drive.google.com/file/d/<ID>/...` | 取 `<ID>` |
| `docs.google.com/document｜presentation｜spreadsheets/d/<ID>/...` | 取 `<ID>` |
| `drive.google.com/drive/folders/<ID>` | 資料夾：`search_files` 用 `parentId = '<ID>'` 列出全部檔案，必要時往子資料夾再列一層 |
| 只有名稱（「線代講義」） | `search_files`：`title contains '線代'`；類型用 `mimeType` 篩選，不要把「簡報」「PDF」寫進 title 搜尋 |
| 同學分享的 | 加上 `sharedWithMe = true` |

不要從檔名猜 ID。找到多個候選、不確定是哪個時，列出檔名與修改日期請使用者選。

### 3. 讀內容：先文字，必要時再看頁面

從 Drive 讀到的內容同樣整理進 `materials.md`，出處寫成 `[Drive: 檔名 p.N]`。

1. **先用 `read_file_content`**——支援 Google 文件/簡報/試算表、PDF、Word、PPT、圖片，回傳文字，成本最低。
   - Google 文件或簡報加 `includeComments: true`：老師或同學留的註解常常就是重點提示
2. **公式或圖表讀不出來時**（文字裡出現破碎的符號、矩陣變成一串數字）：
   - 先用 `get_file_metadata` 看檔案大小
   - **小檔（約 300 KB 以下）**：`download_file_content` 下載。Google 簡報/文件加 `exportMimeType: "application/pdf"` 匯出成 PDF。回傳的 base64 存成檔案後解碼（`base64 -d x.b64 > x.pdf`），再把這個 PDF 交給 ingest 處理
   - **大檔**：base64 會塞爆對話，不要下載整份。請使用者把該檔案直接上傳到對話，或只上傳公式最多的那幾頁的截圖
3. 圖片（手寫筆記照片）：小張的可直接下載解碼後用 Read 看；多張大圖同樣請使用者直接上傳

### 4. 產出要存回 Drive 時

產出的 PDF 每份通常 300 KB 以上，透過連接器上傳等於把整份檔案 base64 塞進對話，容易失敗，**不要用 `create_file` 上傳 PDF**。改成：
- 照一般方式交付（有傳檔工具就用，沒有就給檔案路徑），告訴使用者可以下載後拖進 Drive
- 如果使用者的電腦有連到這個對話，而且裝了 Google Drive 電腦版（同步資料夾），可以把 PDF 直接寫進那個同步資料夾，Drive 會自動同步

## 資料不足時

- 只有考古題沒有講義：從考古題反推考試範圍與概念，重點整理以補充為主，全部標 `{{補充}}`
- 資料只涵蓋部分範圍但使用者選了更大範圍：照實告訴使用者哪些章節沒有資料，詢問要補充還是排除
