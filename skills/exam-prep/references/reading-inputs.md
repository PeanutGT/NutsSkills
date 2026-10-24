# 讀取各類學習資料

目標是把所有資料都讀進來，建立完整的內容地圖。寧可多讀，不要只看前幾頁就開始寫——漏掉的章節使用者考試時會遇到。

## PDF（講義、投影片、課本）

```bash
pdftotext -layout slides.pdf - | head -200     # 先看文字層
pdfinfo slides.pdf                               # 頁數
```

- 有文字層：用 `pdftotext` 擷取全文
- **數學公式、圖表、示意圖**在文字層常常亂掉或消失。投影片類 PDF 請另外把頁面轉成圖片檢視：
  `pdftoppm -r 80 -png slides.pdf page` 然後用 Read 看圖片，至少看公式密集的頁面
- 沒有文字層（掃描檔）→ 當成圖片處理（見下）
- 頁數很多時分批讀，但要讀完

## PowerPoint (.pptx)

```bash
pip install --break-system-packages -q python-pptx 2>/dev/null
python3 -c "
from pptx import Presentation
import sys
p = Presentation(sys.argv[1])
for i, s in enumerate(p.slides, 1):
    print(f'--- slide {i} ---')
    for sh in s.shapes:
        if sh.has_text_frame: print(sh.text_frame.text)
    if s.has_notes_slide: print('[notes]', s.notes_slide.notes_text_frame.text)
" deck.pptx
```

公式多為圖片或 OLE 物件，文字擷取不到；若內容看起來缺漏，用 LibreOffice 轉 PDF 再轉圖片檢視：
`soffice --headless --convert-to pdf deck.pptx`

## 手寫筆記、手機拍的照片

直接用 Read 檢視圖片，自己辨識文字與公式。
- 辨識不確定的字或符號，寫進重點時依上下文判斷；真的無法判斷就在回覆中列出請使用者確認，不要自行猜測關鍵數值
- 照片歪斜或太暗不影響閱讀時不用處理；看不清楚時可用 Pillow 調亮、轉正、放大後再看
- 手寫筆記常反映**老師上課特別強調的地方**，這些內容在重點整理中應優先保留

## 考古題、作業

除了讀內容，還要分析：
- 每題考的概念（對應到內容地圖）
- 題型（選擇、計算、證明…）與大致難度
- 出現頻率：多份考古題中重複出現的概念 → `{{常考}}`
- 出題風格：數字複雜度、中英文、是否偏重推導或計算

如果考古題附有答案，可用來校準解答風格；如果沒有，「逐題詳解」時就要自己解並驗算。

## Word / 純文字 / Markdown

- `.docx`：`pandoc notes.docx -t markdown`
- `.txt` `.md`：直接讀

## Google Drive 上的資料

使用者常常直接貼 Drive 連結、說「在我 Drive 的線代資料夾」，或丟同學分享的檔案。

### 1. 確認連接器

Google Drive 工具名稱是 `mcp__Google_Drive__*`（可能需要先用 ToolSearch 載入）。如果完全找不到，用 SearchMcpRegistry 搜尋 `["google drive"]`，再用 SuggestConnectors 讓使用者一鍵連接；同時告訴他也可以先把檔案下載後直接上傳到對話。

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

1. **先用 `read_file_content`**——支援 Google 文件/簡報/試算表、PDF、Word、PPT、圖片，回傳文字，成本最低。
   - Google 文件或簡報加 `includeComments: true`：老師或同學留的註解常常就是重點提示
2. **公式或圖表讀不出來時**（文字裡出現破碎的符號、矩陣變成一串數字）：
   - 先用 `get_file_metadata` 看檔案大小
   - **小檔（約 300 KB 以下）**：`download_file_content` 下載。Google 簡報/文件加 `exportMimeType: "application/pdf"` 匯出成 PDF。回傳的 base64 存成檔案後解碼（`base64 -d x.b64 > x.pdf`），再照上面「PDF」的方式轉成圖片檢視
   - **大檔**：base64 會塞爆對話，不要下載整份。請使用者把該檔案直接上傳到對話，或只上傳公式最多的那幾頁的截圖
3. 圖片（手寫筆記照片）：小張的可直接下載解碼後用 Read 看；多張大圖同樣請使用者直接上傳

### 4. 產出要存回 Drive 時

產出的 PDF 每份通常 300 KB 以上，透過連接器上傳等於把整份檔案 base64 塞進對話，容易失敗，**不要用 `create_file` 上傳 PDF**。改成：
- 正常用 SendUserFile 交付，告訴使用者可以下載後拖進 Drive
- 如果使用者的電腦有連到這個對話，而且裝了 Google Drive 電腦版（同步資料夾），可以把 PDF 直接寫進那個同步資料夾，Drive 會自動同步

## 資料不足時

- 只有考古題沒有講義：從考古題反推考試範圍與概念，重點整理以補充為主，全部標 `{{補充}}`
- 資料只涵蓋部分範圍但使用者選了更大範圍：照實告訴使用者哪些章節沒有資料，詢問要補充還是排除
