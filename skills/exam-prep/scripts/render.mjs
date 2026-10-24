#!/usr/bin/env node
// exam-prep renderer: study Markdown (+ math, callouts, question cards) -> themed PDF.
//
// Usage:
//   node render.mjs <input.md> <output.pdf> [--theme modern|textbook|cheatsheet] [--html out.html]
//
// Front matter (optional, at top of file):
//   ---
//   title: 線性代數 期中考 重點整理
//   subtitle: Ch1–Ch4 · 矩陣、行列式、向量空間
//   course: 線性代數 CE2005
//   kind: notes | practice | answers | cheatsheet
//   exam_date: 2026-11-05
//   ---
//
// See ../references/markdown-format.md for the full syntax.

import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SKILL_DIR = path.resolve(HERE, "..");
const DEPS_DIR = path.join(os.homedir(), ".exam-prep-deps");

// ---------- dependency resolution (katex, marked, playwright) ----------
function tryRequire(name) {
  const bases = [HERE, DEPS_DIR, ...(process.env.NODE_PATH || "").split(path.delimiter).filter(Boolean)];
  for (const b of bases) {
    try {
      const req = createRequire(path.join(b, "noop.js"));
      return { mod: req(name), resolved: req.resolve(name) };
    } catch {}
    try {
      const req = createRequire(path.join(b, "node_modules", "noop.js"));
      return { mod: req(name), resolved: req.resolve(name) };
    } catch {}
  }
  return null;
}
function need(name) {
  let r = tryRequire(name);
  if (!r) {
    console.error(`[exam-prep] installing ${name} into ${DEPS_DIR} ...`);
    fs.mkdirSync(DEPS_DIR, { recursive: true });
    execSync(`npm install --silent --prefix "${DEPS_DIR}" ${name}`, { stdio: "inherit" });
    r = tryRequire(name);
  }
  if (!r) throw new Error(`Cannot load ${name}`);
  return r;
}

const { mod: katex, resolved: katexPath } = need("katex");
const { mod: markedMod } = need("marked");
const marked = markedMod.marked || markedMod;
const katexCss = (() => {
  // .../katex/dist/katex.js -> .../katex/dist/katex.min.css
  let dir = path.dirname(katexPath);
  while (!fs.existsSync(path.join(dir, "katex.min.css")) && dir !== path.dirname(dir)) {
    if (fs.existsSync(path.join(dir, "dist", "katex.min.css"))) { dir = path.join(dir, "dist"); break; }
    dir = path.dirname(dir);
  }
  return path.join(dir, "katex.min.css");
})();

// ---------- args ----------
const args = process.argv.slice(2);
if (args.length < 2) {
  console.error("usage: node render.mjs <input.md> <output.pdf> [--theme modern|textbook|cheatsheet] [--html out.html]");
  process.exit(1);
}
const [inPath, outPath] = args;
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const THEMES = ["modern", "textbook", "cheatsheet"];
let theme = opt("--theme", "modern");
if (!THEMES.includes(theme)) { console.error(`unknown theme ${theme}, using modern`); theme = "modern"; }
const htmlOut = opt("--html", null);

// ---------- parse front matter ----------
let src = fs.readFileSync(inPath, "utf8").replace(/\r\n/g, "\n");
const meta = {};
const fm = src.match(/^---\n([\s\S]*?)\n---\n/);
if (fm) {
  for (const line of fm[1].split("\n")) {
    const m = line.match(/^(\w+)\s*:\s*(.*)$/);
    if (m) meta[m[1]] = m[2].trim().replace(/^["']|["']$/g, "");
  }
  src = src.slice(fm[0].length);
}
const kind = meta.kind || "notes";

// ---------- protect code + math before markdown ----------
const stash = [];
const keep = (html) => `\u0000${stash.push(html) - 1}\u0000`;
// block-level placeholders use a distinct marker so only they get unwrapped from <p>
const keepBlock = (html) => `\u0001${stash.push(html) - 1}\u0001`;
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function renderMath(tex, display) {
  try {
    return katex.renderToString(tex, { displayMode: display, throwOnError: false, strict: "ignore", trust: false, output: "html" });
  } catch (e) {
    return `<code class="math-error">${esc(tex)}</code>`;
  }
}

function protect(text) {
  // fenced code
  text = text.replace(/^```(\w*)\n([\s\S]*?)\n```$/gm, (_, lang, code) =>
    "\n\n" + keepBlock(`<pre class="code"><code class="lang-${lang}">${esc(code)}</code></pre>`) + "\n\n");
  // inline code
  text = text.replace(/`([^`\n]+)`/g, (_, c) => keep(`<code>${esc(c)}</code>`));
  // display math $$...$$ and \[...\]
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, t) => "\n\n" + keepBlock(`<div class="math-display">${renderMath(t.trim(), true)}</div>`) + "\n\n");
  text = text.replace(/\\\[([\s\S]+?)\\\]/g, (_, t) => "\n\n" + keepBlock(`<div class="math-display">${renderMath(t.trim(), true)}</div>`) + "\n\n");
  // inline math $...$ (not $$) and \(...\)
  // trailing punctuation is glued to the formula so it never wraps onto its own line
  const PUNCT = "[.,;:!?，。、；：！？)）」』]*";
  const inline = (t, p) => keep(p ? `<span class="nobr">${renderMath(t, false)}${esc(p)}</span>` : renderMath(t, false));
  text = text.replace(new RegExp(String.raw`(?<![\\$])\$([^\s$](?:[^$\n]*?[^\s$\\])?)\$(?![\d$])(${PUNCT})`, "g"), (_, t, p) => inline(t, p));
  text = text.replace(new RegExp(String.raw`\\\(([\s\S]+?)\\\)(${PUNCT})`, "g"), (_, t, p) => inline(t, p));
  return text;
}

// ---------- inline badges {{常考}} ----------
const BADGE_CLASS = {
  "常考": "hot", "必考": "hot", "補充": "extra", "已驗算": "ok", "✓ 已驗算": "ok",
  "無法程式驗算": "manual", "易錯": "warn", "考古題": "past",
};
function badges(text) {
  return text.replace(/\{\{([^{}\n]{1,30})\}\}/g, (_, raw) => {
    const label = raw.trim();
    if (/^難度\s*[:：]/.test(label)) return keep(`<span class="badge diff">${esc(label)}</span>`);
    const cls = BADGE_CLASS[label] || "neutral";
    const shown = cls === "ok" ? "✓ 已驗算" : label;
    return keep(`<span class="badge ${cls}">${esc(shown)}</span>`);
  });
}

// ---------- block containers :::type header ... ::: ----------
const CALLOUT = {
  def: { cls: "def", label: "定義", icon: "◆" },
  thm: { cls: "thm", label: "定理", icon: "■" },
  formula: { cls: "formula", label: "公式", icon: "ƒ" },
  example: { cls: "example", label: "例題", icon: "✎" },
  warn: { cls: "warn", label: "易錯", icon: "!" },
  hot: { cls: "hot", label: "常考", icon: "★" },
  tip: { cls: "tip", label: "技巧", icon: "➜" },
  extra: { cls: "extra", label: "補充", icon: "+" },
  summary: { cls: "summary", label: "本章摘要", icon: "≡" },
  past: { cls: "past", label: "考古題分析", icon: "⌕" },
};

let qCounter = 0;
function md(text) { return marked.parse(text, { gfm: true, breaks: false }); }

function containers(text) {
  // innermost-first so nesting works
  const re = /^:::(\w+)[ \t]*([^\n]*)\n((?:(?!^:::\w)[\s\S])*?)^:::[ \t]*$/m;
  let guard = 0;
  while (re.test(text) && guard++ < 2000) {
    text = text.replace(re, (_, type, header, body) => {
      header = header.trim();
      const inner = md(body);
      if (type === "q" || type === "a") return "\n\n" + keepBlock(questionCard(type, header, inner)) + "\n\n";
      if (type === "cols") return "\n\n" + keepBlock(`<div class="cols">${inner}</div>`) + "\n\n";
      const c = CALLOUT[type] || { cls: "note", label: type, icon: "•" };
      const title = header ? `<span class="c-title">${md(header).replace(/^<p>|<\/p>\s*$/g, "")}</span>` : "";
      return "\n\n" + keepBlock(
        `<div class="callout ${c.cls}"><div class="c-head"><span class="c-icon">${c.icon}</span><span class="c-label">${c.label}</span>${title}</div><div class="c-body">${inner}</div></div>`
      ) + "\n\n";
    });
  }
  return text;
}

// header: "3 | 計算題 | ★★☆ | 2 頁空白" (number optional/auto) ; for answers: "3 | ✓ 已驗算"
function questionCard(type, header, inner) {
  const parts = header.split("|").map((s) => s.trim()).filter(Boolean);
  let num;
  if (parts.length && /^\d+[a-z]?$/i.test(parts[0])) num = parts.shift();
  else num = String(++qCounter);
  if (type === "q") qCounter = Math.max(qCounter, parseInt(num) || qCounter);
  let space = 0;
  const tags = [];
  for (const p of parts) {
    const sm = p.match(/^space\s*=\s*(\d+)$/i);
    if (sm) { space = +sm[1]; continue; }
    let cls = "neutral";
    if (/^[★☆]+$/.test(p)) cls = "diff";
    else if (/驗算/.test(p) && !/無法/.test(p)) cls = "ok";
    else if (/無法/.test(p)) cls = "manual";
    else if (/補充/.test(p)) cls = "extra";
    else if (/考古/.test(p)) cls = "past";
    tags.push(`<span class="badge ${cls}">${esc(p)}</span>`);
  }
  const lines = space ? `<div class="answer-space" style="height:${space * 1.6}em"></div>` : "";
  return `<section class="qcard ${type === "a" ? "acard" : ""}"><div class="q-head"><span class="q-num">${type === "a" ? "解 " : ""}${esc(num)}</span>${tags.join("")}</div><div class="q-body">${inner}${lines}</div></section>`;
}

// ---------- pipeline ----------
let body = src;
body = body.replace(/^\s*(?:<!--\s*pagebreak\s*-->|\\newpage)\s*$/gm, () => "\n\n" + keepBlock('<div class="pagebreak"></div>') + "\n\n");
body = protect(body);
body = badges(body);
body = containers(body);
let html = md(body);
// restore stash (repeat for nested placeholders)
// block placeholders get wrapped in <p> by marked; unwrap them so cards/callouts are real siblings of headings
const unwrapP = (s) => s.replace(/<p>\s*(\u0001\d+\u0001)\s*<\/p>/g, "$1");
for (let i = 0; i < 6 && /[\u0000\u0001]/.test(html); i++) html = unwrapP(html).replace(/[\u0000\u0001](\d+)[\u0000\u0001]/g, (_, n) => stash[+n]);

// TOC from h2 (for notes with enough sections)
const h2s = [];
html = html.replace(/<h2>([\s\S]*?)<\/h2>/g, (_, inner) => {
  const id = `sec-${h2s.length + 1}`;
  h2s.push({ id, text: inner.replace(/<[^>]+>/g, "") });
  return `<h2 id="${id}">${inner}</h2>`;
});
const wantToc = (kind === "notes" && h2s.length >= 4 && theme !== "cheatsheet") || meta.toc === "true";
const toc = wantToc
  ? `<nav class="toc"><div class="toc-title">目錄</div><ol>${h2s.map((h) => `<li><a href="#${h.id}">${esc(h.text)}</a></li>`).join("")}</ol></nav>`
  : "";

const KIND_LABEL = { notes: "重點整理", practice: "練習題", answers: "解答本", cheatsheet: "公式小抄" };
const today = new Date().toISOString().slice(0, 10);
let countdown = "";
if (meta.exam_date && /^\d{4}-\d{2}-\d{2}$/.test(meta.exam_date)) {
  const d = Math.ceil((new Date(meta.exam_date) - new Date(today)) / 86400000);
  if (d >= 0) countdown = `<span class="meta-chip">距考試 ${d} 天</span>`;
}
const banner = `
<header class="banner kind-${kind}">
  <div class="banner-kind">${KIND_LABEL[kind] || ""}${meta.course ? ` · ${esc(meta.course)}` : ""}</div>
  <h1 class="banner-title">${esc(meta.title || "")}</h1>
  ${meta.subtitle ? `<div class="banner-sub">${esc(meta.subtitle)}</div>` : ""}
  <div class="banner-meta">${meta.exam_date ? `<span class="meta-chip">考試日 ${esc(meta.exam_date)}</span>` : ""}${countdown}<span class="meta-chip">產出 ${today}</span></div>
</header>`;

const readCss = (f) => fs.readFileSync(path.join(SKILL_DIR, "assets", "themes", f), "utf8");
const css = readCss("base.css") + "\n" + readCss(`${theme}.css`);

const doc = `<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<title>${esc(meta.title || "exam-prep")}</title>
<link rel="stylesheet" href="${pathToFileURL(katexCss).href}">
<style>${css}</style></head>
<body class="theme-${theme} kind-${kind}">${banner}${toc}<main class="content">${html}</main></body></html>`;

const tmpHtml = htmlOut || path.join(os.tmpdir(), `exam-prep-${process.pid}.html`);
fs.writeFileSync(tmpHtml, doc);

// ---------- print with Chromium ----------
const { mod: pw } = need("playwright");
const browser = await pw.chromium.launch();
const page = await browser.newPage();
await page.goto(pathToFileURL(path.resolve(tmpHtml)).href, { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
// keep every heading on the same page as the block that follows it
await page.evaluate(() => {
  for (const h of document.querySelectorAll("main.content h2, main.content h3, main.content h4")) {
    const next = h.nextElementSibling;
    if (!next || /^H[2-4]$/.test(next.tagName)) continue;
    const wrap = document.createElement("div");
    wrap.className = "keep-with-next";
    h.parentNode.insertBefore(wrap, h);
    wrap.append(h, next);
  }
});
const footerTitle = esc(`${meta.title || ""}`);
await page.pdf({
  path: outPath,
  format: "A4",
  printBackground: true,
  displayHeaderFooter: true,
  headerTemplate: `<div></div>`,
  footerTemplate: `<div style="width:100%;font-size:8px;color:#8a8f98;padding:0 14mm;display:flex;justify-content:space-between;font-family:'Noto Sans CJK TC','Noto Sans TC',sans-serif;"><span>${footerTitle}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`,
  margin: theme === "cheatsheet"
    ? { top: "10mm", bottom: "12mm", left: "10mm", right: "10mm" }
    : { top: "16mm", bottom: "18mm", left: "16mm", right: "16mm" },
});
await browser.close();
if (!htmlOut) fs.rmSync(tmpHtml, { force: true });
console.log(`[exam-prep] wrote ${outPath} (theme=${theme}, kind=${kind})`);
