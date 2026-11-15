# nuts-engineering

寫程式用的軟體工程流程套組。參考 [obra/superpowers](https://github.com/obra/superpowers)、[mattpocock/skills](https://github.com/mattpocock/skills)、[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) 與 Karpathy 式 CLAUDE.md 的設計，改寫成自己的規則。SKILL.md 用英文寫（模型觸發與遵循最穩定）。

## 安裝

```text
/plugin marketplace add PeanutGT/NutsSkills
/plugin install nuts-engineering@nutsskills
```

## 流程

```
clarify → spec → plan → tdd ⇄ debug → verify → code-review → ship
     repo-map / design / simplify / fresh-eyes 任何時候都可用
```

| Skill | 用途 | 什麼時候觸發 |
|---|---|---|
| [nutshell](SKILL.md) | 路由＋四條行為底線 | 任何工程任務開始時 |
| [repo-map](../repo-map/) | 檔案／符號／依賴地圖（約原始碼的 1/20–1/30），`--find` 列出使用某函式的行 | 陌生或大型 repo、「誰呼叫了 X」 |
| [clarify](../clarify/) | 一次問一題，釐清到沒有歧義 | 需求模糊、新功能想法 |
| [spec](../spec/) | Given/When/Then 驗收條件 | 需求確定後 |
| [plan](../plan/) | 可獨立驗證的垂直切片 | 多步驟、多檔案的工作 |
| [tdd](../tdd/) | 先看到測試失敗才寫程式 | 實作功能或修 bug 前 |
| [debug](../debug/) | 重現 → 隔離 → 假設 → 根因 → 修 | bug、測試失敗、錯誤訊息 |
| [verify](../verify/) | 沒有證據不准說完成 | 要說「好了」「修好了」之前 |
| [code-review](../code-review/) | 給 review（兩輪）＋收 review（先查證） | review diff/PR、收到回饋 |
| [design](../design/) | deep modules、依賴方向、YAGNI、ADR | 新模組、API、架構選擇 |
| [simplify](../simplify/) | 不改行為地刪減與重構 | 功能完成後、程式太複雜 |
| [ship](../ship/) | 分支、commit 訊息、PR、合併前檢查 | commit、開 PR、收尾 |
| [fresh-eyes](../fresh-eyes/) | 讓沒有上下文的 reviewer 冷讀，回饋分四類處理 | 交付 spec／plan、難以回頭的決策、大型 diff |
| [writing-skills](../writing-skills/) | 寫新 skill 與 eval 的方法 | 新增或修改 skill |

## 評測

有／無 skill 的對照結果見 [evals/RESULTS.md](evals/RESULTS.md)。每個 skill 的 `evals/` 有觸發測試（`triggers.json`）與行為案例。
