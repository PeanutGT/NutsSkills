# music-studio 更新紀錄

格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，版本號遵循 [語意化版本](https://semver.org/lang/zh-TW/)。

## [3.1.1] - 2026-10-29

### 修正
- 從 GitHub 全新 clone 後有 2 項測試失敗：假 ACE-Step 的模型資料夾是空目錄，git 不會保存，現在改由測試自己建立
- CI 新增 music-studio 單元測試（Linux + ffmpeg + numpy）

## [3.1.0] - 2026-10-25

### 新增
- 儀表板改為深色錄音室機架風格；主畫面是版本比較台（所有版本疊在同一條小節時間軸上，共用播放頭，數字鍵切換）
- 底部佇列列出五個生成階段與經過時間，取消會真的停止顯卡上的工作
- `msclient.py`：Claude 與儀表板透過同一個伺服器排隊，模型常駐顯存，閒置 10 分鐘自動釋放
- `ace_worker.py`：常駐的 ACE-Step 工作程序，顯存保護與 CPU 解碼偵測；解碼退到 CPU 時警告，並自動收緊下一首的設定
- 詞庫補上遊戲常用詞（失敗、落寞、戰爭、遊戲等），並修正「畫面」等贅字造成的未匹配問題

### 變更
- 失敗或取消的工作不留下空的作品資料夾（會移到工作區的 `trash`）
- 低階顯卡（<8 GB）預設將擴散模型移出顯卡（`offload_dit_to_cpu`）
- 文字對比達 AA、手機版無橫向捲動、支援鍵盤操作與 `prefers-reduced-motion`

### 注意
- 常駐引擎已對照 ACE-Step 最新原始碼撰寫，尚未在各種顯卡上完整實測；舊的 `engine.py generate` 仍可作為後備。
