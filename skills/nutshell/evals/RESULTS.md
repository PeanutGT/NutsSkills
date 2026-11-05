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

## 限制與待辦

- n=1、只用 Sonnet 測；用 Opus 當受測者時 baseline 可能更好，差距會縮小。
- 觸發測試是模擬判斷，不是真實 Claude Code 的 skill 載入流程。
- code-review 情境太簡單（baseline 已過關），需要更難的案例，例如 review 一段有 N+1 查詢或權限漏洞的 diff。
- repo-map 只有單元測試與大小實測（NutsSkills 19.8 倍、Python 標準庫 email 29.9 倍、asyncio 21.2 倍、json 26.2 倍），還沒有行為 eval。
