# NutsSkills

PeanutGT 的 Claude Skills 合集。每個 skill 放在 `skills/<skill-name>/` 底下，資料夾內的 `SKILL.md` 是 skill 本體。

## Skills

| Skill | 說明 |
|---|---|
| [exam-prep](skills/exam-prep/) | 把講義、投影片、課本、手寫筆記照片、考古題（可直接上傳或給 Google Drive 連結）整理成排版精美的 PDF：學習講義、重點整理、練習題、獨立解答本、公式小抄；計算題答案用程式驗算 |

## 安裝

**Claude.ai / Claude 桌面版**
1. 把要用的 skill 資料夾壓縮成 zip（例如 `cd skills && zip -r exam-prep.zip exam-prep`）
2. 到 Settings → Capabilities → Skills 上傳

**Claude Code**

把 skill 資料夾複製到個人或專案的 skills 目錄：

```bash
git clone https://github.com/PeanutGT/NutsSkills.git
cp -r NutsSkills/skills/exam-prep ~/.claude/skills/        # 個人，所有專案可用
# 或
cp -r NutsSkills/skills/exam-prep <your-project>/.claude/skills/   # 只給單一專案
```

## Repo 結構

```
NutsSkills/
├── README.md
└── skills/
    └── <skill-name>/
        ├── SKILL.md        # 必要：frontmatter（name、description）＋ 指示
        ├── README.md       # 給人看的簡介（選用）
        ├── scripts/        # 可執行腳本（選用）
        ├── references/     # 需要時才載入的參考文件（選用）
        ├── assets/         # 範本、樣式等輸出用資源（選用）
        └── evals/          # 測試案例（選用，可用 `claude plugin eval` 執行）
```

## 新增 skill

1. 在 `skills/` 底下建立新資料夾，資料夾名稱與 `SKILL.md` 的 `name` 相同（小寫英文與連字號）
2. 在上方表格加一列
