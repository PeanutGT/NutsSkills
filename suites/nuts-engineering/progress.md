# nuts-engineering 進度與交接

開發用筆記，不會打包進 Release zip。上半部是**設計決策**（很少改），下半部是**現況與待辦**（每次改版更新）。

---

## 一、設計決策

- 套組 = 路由 `nutshell`（四條行為底線＋挑選下一個 skill）＋各階段一個 skill：clarify、spec、plan、tdd、debug、verify、code-review、design、simplify、ship、writing-skills、fresh-eyes，加上工具型的 `repo-map`
- 每個 skill 獨立可用，彼此只用「Related: …」互相指引，不互相 import
- 參考外部頂尖 skill（mattpocock/skills、obra/superpowers、addyosmani/agent-skills、google/elephant-goldfish-model）時**以自己的話改寫**，不複製原文
- 每個 skill 都要有 `evals/triggers.json`（3 應觸發／2 不應觸發）與 `evals/behavior/`；宣稱「有幫助」前要跑過沒有 skill 的 baseline
- 評測結果集中寫在 `skills/nutshell/evals/RESULTS.md`，每輪標日期、受測模型與 n
- 發版：各 skill 的 `metadata.version`／CHANGELOG 照常維護，套組版本寫在 `suites/nuts-engineering/CHANGELOG.md`，推 `nuts-engineering-v<版本>` tag 或手動觸發 Release，每個 skill 各一個 zip

---

## 二、現況

- **最新套組版本：1.1.0**（2026-11-06 已發布 Release `nuts-engineering-v1.1.0`）。各 skill 1.1.0，`simplify`、`fresh-eyes` 為 1.0.0
- 有效的部分（Sonnet、Opus 都有改善）：design、clarify、ship。debug、verify 對 Opus 沒有額外效果
- 2026-11-07：新增更難的 code-review 評測題 `skills/code-review/evals/review-cross-file/`（4 個要讀 diff 以外的檔案才看得到的錯誤＋1 個誘答）。每個錯誤都已在 fixture 實際重現，**還沒跑有／無 skill 對照**

## 三、待辦（依優先順序）

1. 跑 `review-cross-file`：Sonnet、Opus 各跑有／無 skill，結果寫進 RESULTS.md
2. 重跑觸發測試：1.1.0 改寫了 nutshell 與 code-review 的 description，改寫後沒有重跑（上次 nutshell 0/3）
3. 重跑改版後 debug、verify、code-review 的行為 eval（1.1.0 改版後沒重跑）
4. repo-map：沒有明顯關鍵字的結構題（例如「改這個欄位會影響哪些地方」），測 `--find` 是否比 grep 省
