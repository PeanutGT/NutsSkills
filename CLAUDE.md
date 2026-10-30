# NutsSkills — Claude Code 工作說明

PeanutGT（曹萬生）的 Claude Skills 合集，公開於 https://github.com/PeanutGT/NutsSkills ，有其他人在使用。和使用者溝通用**繁體中文**。

## 先讀哪裡

| 要做什麼 | 先讀 |
|---|---|
| 任何 exam-prep 的工作 | `skills/exam-prep/progress.md`（現況、決策、待辦） |
| 任何 music-studio 的工作 | `skills/music-studio/progress.md` |
| 新增 skill、發版流程 | `CONTRIBUTING.md` |

## 規則（使用者明確要求）

- **git commit 作者只有使用者**：`PeanutGT <peanutgttw@gmail.com>`。不加 `Co-Authored-By`、不加任何 Claude／session 連結的 trailer 行。commit 前確認 `git config user.name` / `user.email`
- 授權 Apache-2.0；每個 SKILL.md frontmatter 要有 `license: Apache-2.0`
- 不要在 issue、範例或測試檔中放有版權的課程講義或考卷

## Repo 結構與慣例

- `skills/<name>/`：資料夾名＝SKILL.md 的 `name`。frontmatter 只能用 `name`、`description`、`license`、`allowed-tools`、`metadata`、`compatibility`（Claude.ai 上傳限制）；`description` ≤ 1024 字且不可有 `<` `>`
- 版本號在 `metadata.version`（語意化版本），每次改版同時在該 skill 的 `CHANGELOG.md` 最上方加條目
- 新 skill 要加進 `README.md`、`README.en.md` 的表格與 `.claude-plugin/marketplace.json`
- `evals/` 是測試案例，不會打包進 Release zip
- `docs/images/` 放 README 用圖，不打包

## 常用指令

```bash
pip install pyyaml && python tools/validate_skills.py        # 格式檢查（CI 也會跑）
python tools/smoke_test.py --out dist/smoke                  # exam-prep 端到端：三主題渲染＋ingest＋preview
python tools/build_zip.py exam-prep                          # 打包 dist/exam-prep-<版本>.zip
```

smoke test 需要 Node.js、Chromium（Playwright）、poppler、Noto CJK 字型、Python 的 matplotlib／scipy／sympy／pillow／python-pptx。

## 發版

改 `metadata.version` → 寫 CHANGELOG → 推上 main 且 CI 綠燈 → 任一：
- GitHub → Actions → **Release** → Run workflow → 輸入 skill 名稱
- 或 `git tag exam-prep-v2.2.0 && git push origin exam-prep-v2.2.0`（tag 版本須與 metadata.version 一致）

CI：`.github/workflows/validate.yml`（每次 push／PR），`release.yml`（建立 Release 並附 zip）。
