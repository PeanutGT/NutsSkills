# Changelog

## 1.1.0 — 2026-11-05

- `--find` 改成列出真正提到該名稱的行（`referenced at: 檔案:行`），只看定義檔與匯入它的檔案；以前只列出「匯入了這個檔案」的檔案，會把只 import 卻沒呼叫的檔案（例如 music-studio 的 `pipeline.py`）誤列為呼叫者。
- 修正：腳本互相用 `import common` 這種同資料夾寫法時，import 與「used by」沒有被解析（music-studio、exam-prep 的 scripts 都是這種寫法）。
- SKILL.md：知道名稱就先用 `--find`；大型 repo 不要整份讀 map，只讀相關段落；問題有明確關鍵字時 grep 一樣好。依據是行為 eval：舊版流程在「有關鍵字可 grep」的題目上比不用 skill 多花 2–5% token。

## 1.0.0 — 2026-11-05

- 初版：`scripts/repo_map.py` 產生檔案、公開符號、import 與反向 import 的精簡地圖；`--find` 查符號定義與使用者。屬於 nuts-engineering 套組。
- 實測：NutsSkills 本身 19.8 倍、Python 標準庫 email 29.9 倍、asyncio 21.2 倍、json 26.2 倍（地圖字元數 vs 原始碼字元數）。
