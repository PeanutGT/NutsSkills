# 貢獻指南

謝謝你願意幫忙！這份文件說明怎麼回報問題、修改現有 skill，或加入新的 skill。

*English: issues and pull requests in English are welcome too. The essentials: run `python tools/validate_skills.py` before opening a PR, bump `metadata.version` in SKILL.md, and add a CHANGELOG entry.*

## 回報問題

請用 [Issue 範本](https://github.com/PeanutGT/NutsSkills/issues/new/choose)，並附上：

- 用的是哪個 skill、哪個版本（SKILL.md 的 `metadata.version`，或下載的 zip 檔名）
- 在哪裡使用（Claude.ai 網頁／桌面版／Claude Code）
- 你對 Claude 說了什麼、預期的結果、實際的結果
- Claude 回報的錯誤訊息（如果有）

**請不要上傳有版權的講義、考卷，或含個人資料的檔案。**

## 開發環境

```bash
git clone https://github.com/PeanutGT/NutsSkills.git
cd NutsSkills
pip install pyyaml                     # 驗證工具需要
python tools/validate_skills.py        # 檢查所有 skill
python tools/build_zip.py exam-prep    # 打包成 dist/exam-prep-<版本>.zip
```

在 Claude Code 測試修改中的 skill：把 `skills/<name>` 以符號連結放進 `~/.claude/skills/`，開新對話即可使用最新內容。

## 修改現有 skill

1. 開一個分支修改
2. 依修改程度調整 `SKILL.md` frontmatter 的 `metadata.version`（[語意化版本](https://semver.org/lang/zh-TW/)）：
   - **修補號**（2.0.0 → 2.0.1）：修 bug、改文字，使用方式不變
   - **次版號**（2.0.0 → 2.1.0）：新增功能，舊用法仍然可用
   - **主版號**（2.0.0 → 3.0.0）：使用方式或產出有不相容的改變
3. 在該 skill 的 `CHANGELOG.md` 最上方新增這個版本的條目
4. 實際讓 Claude 用修改後的 skill 跑一次（可用 `evals/` 裡的測試案例），確認產出正常
5. 執行 `python tools/validate_skills.py`，通過後開 Pull Request

## 新增 skill

1. 建立 `skills/<skill-name>/`，資料夾名稱必須和 SKILL.md 的 `name` 相同（小寫英文、數字、連字號）
2. SKILL.md frontmatter 至少包含：

   ```yaml
   ---
   name: skill-name
   description: 做什麼、什麼時候該用（1024 字以內，不能有 < 或 >）
   license: Apache-2.0
   metadata:
     version: "1.0.0"
     author: 你的名字
   ---
   ```

   frontmatter 只能使用 `name`、`description`、`license`、`allowed-tools`、`metadata`、`compatibility`，其他欄位會讓 Claude.ai 上傳失敗。
3. 加上 `CHANGELOG.md`、`README.md`（可加 `README.en.md`）
4. 在根目錄 `README.md`、`README.en.md` 的 Skills 表格，以及 `.claude-plugin/marketplace.json` 的 `plugins` 各加一筆
5. 建議在 `evals/` 放 2–3 個測試案例（格式見現有 skill）
6. 執行 `python tools/validate_skills.py`

## 發布新版本（維護者）

合併到 `main` 後，推送格式為 `<skill-name>-v<版本>` 的 tag，GitHub Actions 會自動驗證、打包 zip 並建立 Release：

```bash
git tag exam-prep-v2.1.0
git push origin exam-prep-v2.1.0
```

Tag 的版本必須和 SKILL.md 的 `metadata.version` 一致，否則發布會失敗。

## 授權

提交貢獻即表示你同意以 [Apache License 2.0](LICENSE) 授權你的貢獻。
