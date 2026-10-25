# exam-prep

[繁體中文](README.md) | English

Turns study materials into beautifully laid-out, printable PDFs — for learning the material or preparing for an exam. Output is in Traditional Chinese by default (practice questions can be English or bilingual).

![Pattern cards, Cornell recall notes and layered notes](../../docs/images/exam-prep/overview.png)
<sub>Left to right: pattern cards, Cornell recall notes, layered notes — all generated from one photo of probability lecture notes.</sub>

## What makes it different

It doesn't just rewrite the textbook chapter by chapter — it **reorganizes the knowledge**:

1. **Concept analysis** — prerequisites, sources, past-exam frequency and question types for every concept
2. **Organization styles** (pick any; one PDF each)

   | Style | Answers the question |
   |---|---|
   | Chapter handout (detailed) | What is this topic actually about? |
   | Chapter notes (concise) | What do I need to remember? |
   | Pattern cards | How will the exam ask, and how do I solve it? (recognise → steps → example → traps) |
   | Cornell recall notes | Do I really remember it? (cover the right column and self-test) |
   | Layered notes | What should I read with 30 seconds / 5 minutes / plenty of time? |

3. **Concept maps** — a whole-scope map and one per chapter, showing prerequisites and frequently tested ideas
4. **Figures** — distribution bar charts, shaded probability areas, histograms, annotated box plots, regression, Venn diagrams, probability trees, linear maps…
5. **Verified numbers** — answers, worked examples and numbers on figures are recomputed with SymPy / SciPy

Also: practice questions (Chinese / English / bilingual), a separate answer key, a two-column cheat sheet. Three themes: modern, textbook, cheat-sheet.

## Inputs

Lecture slides (PDF / PPT), textbook chapters, photos of handwritten notes, past exams, homework — uploaded directly or as Google Drive file / folder links (requires the Google Drive connector).

## Install

See the [install guide](../../README.en.md#install). On Claude.ai, download `exam-prep-<version>.zip` from [Releases](https://github.com/PeanutGT/NutsSkills/releases) and upload it.

## Usage

Just describe what you need, e.g.

- "My linear algebra midterm is next Thursday — here are the slides and past exams. Make pattern cards and 12 practice questions."
- "Turn these probability lecture slides into a detailed study handout."

Claude reads everything first, then asks about scope, organization style, theme, question types and language before producing the PDFs.

## Requirements

On Claude.ai, **code execution** must be enabled (Settings → Capabilities); missing packages are installed automatically. With Claude Code on your own machine you need:

- Node.js 18+ (`katex`, `marked`, `playwright`, `mermaid` are auto-installed into `~/.exam-prep-deps`)
- Chromium for Playwright (auto-installed on first run if missing), Noto Sans/Serif CJK TC fonts recommended
- Python 3 with `sympy`, `scipy`, `matplotlib`
- `pdftoppm` (poppler) for layout checks

## Known limitations

- Output is primarily Traditional Chinese
- Poor scans or messy handwriting can be misread; Claude asks you to confirm uncertain key values
- Proofs and essay answers can't be verified in code and are marked as such
- Google Drive input needs the connector; generated PDFs are not saved back to Drive automatically

See [CHANGELOG.md](CHANGELOG.md) for version history.
