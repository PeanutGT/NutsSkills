# Changelog

nuts-engineering 套組的版本紀錄。各 skill 自己的版本見 `skills/<name>/CHANGELOG.md`。

## 1.1.0 — 2026-11-06

參考 mattpocock/skills、obra/superpowers v7、addyosmani/agent-skills、google/elephant-goldfish-model 的最新版本改版，內容以自己的話改寫。

- **新增 `fresh-eyes`**：交付 spec／plan、做難以回頭的決策或審查大型 diff 前，讓沒有對話脈絡的 reviewer 冷讀，回饋分四類處理。
- **debug**：先做出會針對這個 bug 變紅的單一指令，才開始猜原因；3–5 個可證偽假設、帶標籤的除錯 log、回歸測試放在真實的 seam。
- **verify**：需求逐條對照；回歸測試要用「還原修正 → 必須失敗」證明；委派的工作要自己看 diff。
- **code-review**：「是否符合 spec」與「是否符合規範」兩軸分開審，回報前每條發現都要對照程式碼查證。
- **repo-map 1.1.0**：`--find` 只列出真正提到該名稱的行；能解析同資料夾的 import。
- **tdd、clarify、spec、plan、design、ship、writing-skills、nutshell**：先決定 seam 與測試反模式、先判斷是否需要提問、builder check、計畫自我檢查等小幅更新。
- 評測結果（Sonnet 與 Opus 對照、更難的 code-review 題、repo-map token 實測）見 `skills/nutshell/evals/RESULTS.md`。

## 1.0.0 — 2026-11-05

- 初版：13 個 skill。路由 `nutshell`（含四條行為底線），加上 clarify、spec、plan、tdd、debug、verify、code-review、design、simplify、ship、writing-skills 與 repo-map。
