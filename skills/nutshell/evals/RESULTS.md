# nuts-engineering 評測結果（2026-11-05）

## 方法

- **受測模型**：Claude Sonnet 5.5（subagent），每個情境跑兩次：沒有 skill（baseline）／先讀 skill 再做（with skill）。每組只跑一次（n=1），結果是方向性的，不是統計結論。
- **情境**：每個 skill 一個小型 fixture（Python 迷你商店 app、unittest），題目與預期行為見各 skill 的 `evals/behavior/`。
- **評分**：讀受測 agent 的回報，並直接檢查 fixture 的 `git diff`／`git log`／新檔案，不只採信自述。
- **觸發測試**：把 12 個 skill 的 description 交給另一個 agent，判斷 60 個打亂順序的 prompt 各該載入哪些 skill，和各 skill 的 `evals/triggers.json` 對答案。repo-map 是之後才加的，沒有包含在這次觸發測試裡。

## 觸發：60 / 60

每個 skill 的 3 個「應觸發」、2 個「不應觸發」全部判斷正確。

## 行為

| Skill | 沒有 skill | 有 skill | 結果 |
|---|---|---|---|
| debug | 在 `total()` 加 `if items is None: return 0`，修的是症狀 | 改 `load_items()` 對缺檔回傳 `[]`，修在根因 | **明顯改善** |
| design | 直接做出 plugin registry（decorator、5 個新測試），沒有需求卻先做擴充點 | 指出 YAGNI，給三個選項，問具體的第二種格式是什麼 | **明顯改善** |
| clarify | 一次丟 6 個問題，再附一個猜測的實作方案 | 一次只問一題，附 A–D 選項與推薦 | **明顯改善** |
| ship | 直接在 `main` commit，訊息只有標題沒有原因 | 開 `feat/csv-export-subtotal` 分支，`feat:` 標題＋說明原因的內文，只 stage 指定檔案 | **明顯改善** |
| verify | 跑測試、拒絕宣稱完成 | 同左，另外用 `git diff` 抓到一個被改名而停用的測試 | 小幅改善 |
| simplify | 行為不變、跑測試、新舊函式隨機等價比對 | 同左，並在重構前先補 5 個特徵測試 | 小幅改善 |
| plan | 詳細切片、假設清單 | 切片附 AC 對照、最不確定的先做、每片有驗證指令、「Later」清單 | 小幅改善 |
| tdd | 先寫測試、看到失敗，但一次寫 5 個 | 一次一個測試、每個都紅→綠；**但因此沒寫空字串、純符號等邊界測試** | 改善＋發現漏洞 |
| spec | 117 行，有 Given/When/Then 與假設 | 43 行，有 Given/When/Then 與 `OPEN:` 標記，存到 `docs/specs/` | 持平（較精簡） |
| code-review | 查證後拒絕錯誤的 review 建議 | 同左 | 無差異（baseline 已經做得好） |
| writing-skills | 直接做出 migration skill＋eval＋路由登記 | 堅持先要 baseline 證據，只提問、沒有產出 | **退步** |

兩組 ship 都自行刪掉了使用者留下的 debug `print`，也都有在回報裡說明；兩組都沒有把 `.env` 加進 commit。

## 依結果做的修正

- **tdd**：新增「邊界測試第一次就通過也要寫，可暫時改壞程式確認它會失敗」，完成條件加上邊界案例。
- **writing-skills**：鐵則改為「每個 skill 都要有 eval，跑過 baseline 才能宣稱有幫助」；使用者要求新增 skill 時先做出草稿與 eval，baseline 標為待跑，不擋住使用者。

## 修正後重跑

| Skill | 修正後的行為 | 結果 |
|---|---|---|
| tdd | 3 個核心測試逐一紅→綠；另寫 4 個邊界測試（連續符號、數字、空字串、純符號），第一次就通過後，暫時改壞程式三次確認它們會變紅，再還原。最終 7 個測試全過（已在 fixture 實際重跑確認） | 漏洞已補 |
| writing-skills | 直接產出 migration skill、eval（4 應觸發／3 不應觸發／2 行為情境）、路由登記與 README，並明確標示 baseline 待跑 | 不再擋住使用者 |

## 第二輪（2026-11-05）：Opus、更難的 code-review、repo-map 行為

### Opus 重跑（第一輪效果最大的 5 個）

| Skill | Opus 沒有 skill | Opus 有 skill | 結果 |
|---|---|---|---|
| design | 直接做出 plugin registry 與 5 個測試 | 指出 YAGNI，給三個選項並詢問第二種格式 | **改善仍成立** |
| clarify | 一次丟 4 個問題，再附預設方案 | 一次一題，附 A–D 選項與推薦 | **改善仍成立** |
| ship | 在 `main` commit，debug print 一起進 commit，訊息沒有原因 | 開分支、`feat:` 標題＋原因、commit 前移除 debug print | **改善仍成立** |
| debug | 改 `load_items()` 修在根因 | 同左，另外先執行驗證假設 | 無差異 |
| verify | 跑測試、抓到被停用的測試 | 同左，並附測試輸出 | 無差異 |

### code-review 難題（`skills/code-review/evals/review-planted-bugs/`）

diff 裡埋了 5 個問題：SQL injection、越權讀取、N+1、分頁 off-by-one、吞掉例外。

| | 沒有 skill | 有 skill |
|---|---|---|
| Sonnet | 5/5，分成 blocking / non-blocking，沒有實際重現 | 5/5，每條都有 `[blocker]` 等標記、`file:line`，並實際執行重現 |
| Opus | 5/5，實際重現，另找到缺 item 時會崩潰 | 5/5，同樣實際重現，格式統一 |

兩個模型沒有 skill 也全部抓到；skill 只帶來格式一致與（Sonnet）實際重現。

### repo-map 行為（找出 loudness 預設值如何轉成 loudnorm 參數、誰呼叫它）

| | 沒有 skill | repo-map 1.0.0 | repo-map 1.1.0 |
|---|---|---|---|
| Sonnet | 95,473 tokens／11 次工具 | 97,679／11 | **88,797／8（−7%）** |
| Opus | 91,104／8 | 95,997／15 | 92,537／9（+1.6%） |

六次都答對。1.0.0 的 `--find` 只列「匯入了這個檔案」的檔案，兩個模型都被只 import、沒有呼叫的 `pipeline.py` 誤導，只好再 grep 確認，反而更花 token。1.1.0 改成列出真正提到該名稱的行，並在 SKILL.md 改為「先用 `--find`、不要整份讀 map」。token 數含每次約 7 萬的固定啟動成本，探索本身的差距比總數百分比大。

這題有「loudness」這個好搜尋的關鍵字，grep 本來就很有效率；repo-map 的優勢應該在沒有明顯關鍵字的結構性問題，還沒有測到。

### 這輪的結論

- **design、clarify、ship 在 Sonnet 與 Opus 都有效**，是這套 skill 最有價值的部分。
- **debug、verify 在 Opus 上沒有額外效果**，強模型本來就會這樣做；對較弱模型仍有幫助。
- code-review 的難題對兩個模型都還不夠難。

## 第三輪（2026-11-06）：參考最新的頂尖 skill 改版

### 參考來源（2026-11-06 的 GitHub 數據）
mattpocock/skills（316k 星，前一天剛更新）、obra/superpowers（313k，v7.0.2）、addyosmani/agent-skills（114k）、google/elephant-goldfish-model（12.7k，9 月新出、持續更新）。四者最近的共同方向是**讓沒有上下文的 reviewer 冷讀**，因此新增 `fresh-eyes`。其餘改動針對第二輪「對 Opus 沒有效果」的 skill：debug 改成以「先做出會變紅的單一指令」為核心、verify 補上需求逐條對照與回歸測試反證、code-review 改成兩軸並要求查證每條發現、tdd 新增 seam 與反模式、clarify 先判斷是否需要提問、spec 與 plan 加上交付前檢查。內容都以自己的話改寫。

### 精簡 eval（只跑 2 次）
- **觸發：65/70。** 失誤：nutshell 0/3（有具體 skill 時判斷者只挑具體的）、code-review 1 次（「reviewer 說有 N+1，幫我修」被判成 debug）、tdd 1 次（「修分頁 off-by-one」只判 debug，可接受）。已改寫 nutshell 與 code-review 的 description，**改寫後未重跑**。
- **fresh-eyes 冒煙（Sonnet，有 skill）：通過。** reviewer 只拿到 spec、程式碼與問題，沒有對話脈絡；找出埋好的兩個缺口（HTTP 讀哪個 cart、HTTP 遇到缺 cart 怎麼辦）與另外三個；回饋有分類、spec 有更新、使用者問題一次問完。沒有跑 baseline 對照。
- 改版後的 debug、verify、code-review 等**沒有重跑行為 eval**（為了節省 token）；第二輪的結論仍以舊版為準。

## 限制與待辦

- 每組只跑一次（n=1）。
- 觸發測試是模擬判斷，不是真實 Claude Code 的 skill 載入流程。
- 更難的 code-review 案例已加入（2026-11-07）：`skills/code-review/evals/review-cross-file/`，4 個錯誤都要讀 diff 沒改到的檔案才看得到（金額單位不一致、巢狀 transaction、回傳值語意改變而呼叫端沒改、繞過價格快取），另有 1 個看起來像 SQL injection 但其實安全的誘答。每個錯誤都已實際重現，**有／無 skill 對照還沒跑**。
- 還需要沒有明顯關鍵字的 repo-map 結構題。
