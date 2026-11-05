# Changelog

## 1.0.0 — 2026-11-05

- 初版：`scripts/repo_map.py` 產生檔案、公開符號、import 與反向 import 的精簡地圖；`--find` 查符號定義與使用者。屬於 nuts-engineering 套組。
- 實測：NutsSkills 本身 19.8 倍、Python 標準庫 email 29.9 倍、asyncio 21.2 倍、json 26.2 倍（地圖字元數 vs 原始碼字元數）。
