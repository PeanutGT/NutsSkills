"use strict";
/* Music Studio dashboard.
   - All text goes in through textContent (h()/put()), never innerHTML, so titles, notes and captions cannot run as markup.
   - The server owns the GPU queue; this page long-polls /api/jobs and renders the dock + engine status from it.
   - The comparison deck decodes each variant once (Web Audio) for its waveform and plays variants on one shared clock. */
const TOKEN = document.querySelector('meta[name="ms-token"]').content;
const S = { state: null, view: "create", form: {}, plan: null, take: null, follow: null, jobs: new Map(), seq: 0, worker: {} };
const $view = document.getElementById("view");
const $ = id => document.getElementById(id);

// ---------------------------------------------------------------- helpers
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "value") el.value = v;
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  el.append(...nodes(kids));
  return el;
}
function nodes(kids) {
  return kids.flat(Infinity).filter(k => k != null && k !== false).map(k => (k.nodeType ? k : document.createTextNode(String(k))));
}
function put(el, ...kids) { if (el) el.replaceChildren(...nodes(kids)); }
async function api(path, method = "GET", body) {
  const res = await fetch("/api/" + path, {
    method, headers: { "Content-Type": "application/json", "X-Token": TOKEN },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}
let toastTimer;
function toast(msg, err = false) {
  const t = $("toast");
  t.textContent = msg; t.className = "toast" + (err ? " err" : ""); t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.hidden = true), 4500);
}
const clock = s => (s == null || isNaN(s) ? "--:--" : `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`);
const durOf = st => (st && st.duration && typeof st.duration === "object" ? st.duration : {});
const audioUrl = (take, file) => `/audio/${encodeURIComponent(take)}/${file.split("/").map(encodeURIComponent).join("/")}`;
async function guard(fn) { try { return await fn(); } catch (e) { toast(e.message, true); } }
const nameOf = o => (o ? o.name_zh || o.name || o.id : "");
const descOf = o => (o ? o.description_zh || o.description || "" : "");
const readout = (label, value) => value == null || value === "" ? null : h("div", {}, h("span", {}, label), h("b", {}, value));

// ---------------------------------------------------------------- shell
function show(view) {
  S.view = view;
  document.querySelectorAll(".tabs button").forEach(b => b.setAttribute("aria-selected", String(b.dataset.view === view)));
  deck.stop();
  ({ create: viewCreate, library: viewLibrary, settings: viewSettings })[view]();
}
document.querySelectorAll(".tabs button").forEach(b => b.addEventListener("click", () => show(b.dataset.view)));
document.querySelector(".tabs").addEventListener("keydown", e => {
  const tabs = [...document.querySelectorAll(".tabs button")];
  const i = tabs.indexOf(document.activeElement);
  if (i < 0 || !["ArrowLeft", "ArrowRight"].includes(e.key)) return;
  const n = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
  n.focus(); n.click();
});
async function refreshState() { S.state = await api("state"); S.worker = S.state.worker || {}; renderEngine(); }

function renderEngine() {
  const st = S.state; if (!st) return;
  const w = S.worker || {}, g = st.gpu || {};
  const running = [...S.jobs.values()].find(j => j.status === "running");
  const mock = st.engine === "mock";
  const led = running ? "busy" : (w.models_loaded ? "on" : "");
  const stateText = running ? "生成中" : w.state === "starting" ? "啟動中" : w.models_loaded ? "模型已載入" : mock ? "測試引擎" : "待命（模型未載入）";
  const vram = w.vram_total_gb ? `${w.vram_free_gb ?? "?"} / ${w.vram_total_gb} GB` : g.vram_gb ? `${g.vram_gb} GB` : "無 GPU";
  put($("engine"),
    h("span", { class: "led " + led, "aria-hidden": "true" }),
    h("div", { class: "readout" }, h("b", {}, stateText), h("span", {}, mock ? "mock 引擎" : `ACE-Step · ${st.tier} 等級`)),
    h("div", { class: "readout" }, h("b", { class: "num" }, vram), h("span", {}, w.vram_total_gb ? "可用 / 總顯存" : (g.name || "顯示卡"))),
    w.models_loaded && !running ? h("button", { class: "btn sm quiet", onclick: () => guard(async () => { await api("worker/unload", "POST", {}); toast("已釋放顯存，下次生成會重新載入模型"); }) }, "釋放顯存") : null);
}

// ---------------------------------------------------------------- queue (long poll) + dock
const PHASES = [["loading_models", "載入模型"], ["encoding", "編碼提示"], ["diffusing", "生成"], ["decoding", "解碼音訊"], ["writing", "寫檔"]];
async function pollLoop() {
  for (;;) {
    try {
      const r = await api(`jobs?since=${S.seq}&wait=1`);
      S.seq = r.seq; S.worker = r.worker || S.worker;
      for (const j of r.jobs) onJob(j);
      renderDock(); renderEngine();
    } catch (e) { await new Promise(res => setTimeout(res, 3000)); }
  }
}
function onJob(j) {
  const prev = S.jobs.get(j.id);
  S.jobs.set(j.id, j);
  if (S.follow === j.id) {
    if (j.status === "done" && prev?.status !== "done") {
      S.follow = null;
      guard(async () => { S.take = await api("tracks/" + encodeURIComponent(j.take_id)); if (S.view === "create") renderStage(); toast("生成完成"); });
    } else if (["failed", "cancelled"].includes(j.status) && prev?.status !== j.status) {
      if (S.view === "create") renderStage();
    } else if (S.view === "create" && !S.take) renderStage();
  }
}
function phaseState(j, key) {
  const order = PHASES.map(p => p[0]);
  const cur = order.indexOf(j.phase), me = order.indexOf(key);
  if (j.status === "done") return "done";
  if (key === "decoding" && j.cpu_decode && cur >= me) return cur > me ? "done" : "cpu";
  if (cur < 0) return "todo";
  return me < cur ? "done" : me === cur ? "current" : "todo";
}
function stepList(j) {
  return h("ol", { class: "steps", "aria-label": "生成階段" }, PHASES.map(([k, label]) => {
    const st = phaseState(j, k);
    return h("li", { "data-state": st }, h("span", { class: "led " + (st === "done" ? "on" : st === "current" ? "busy" : st === "cpu" ? "err" : ""), "aria-hidden": "true" }),
      label, st === "cpu" ? "（CPU，很慢）" : null, h("span", { class: "sr-only" }, { done: "完成", current: "進行中", todo: "等待", cpu: "改用 CPU" }[st]));
  }));
}
let dockTimer;
function renderDock() {
  const jobs = [...S.jobs.values()].sort((a, b) => a.created - b.created);
  const run = jobs.find(j => j.status === "running");
  const queued = jobs.filter(j => j.status === "queued");
  const recent = jobs.filter(j => ["done", "failed", "cancelled"].includes(j.status)).slice(-3).reverse();
  const elapsed = run?.started ? Math.max(0, Date.now() / 1000 - run.started) : 0;
  const now = run ? h("div", { class: "now" },
    h("div", { class: "now-top" }, h("b", {}, run.title || run.spec?.title || "未命名"),
      h("span", { class: "num dim" }, clock(elapsed)),
      run.cancelling ? h("span", { class: "dim small" }, "取消中…") : run.detail ? h("span", { class: "dim small" }, run.detail) : null,
      run.warnings?.length ? h("span", { class: "small", style: "color:var(--amber)" }, `${run.warnings.length} 則提示`) : null),
    stepList(run),
    h("div", { class: "meter", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(Math.round((run.pct || 0) * 100)), "aria-label": "整體進度" },
      h("i", { style: `width:${Math.round((run.pct || 0) * 100)}%` })))
    : h("div", { class: "now" }, h("span", { class: "idle" }, queued.length ? "等待開始…" : "佇列是空的。生成的進度會顯示在這裡。"));
  const side = h("div", { class: "side" },
    run ? h("button", { class: "btn sm danger", disabled: run.cancelling, onclick: () => guard(() => api(`jobs/${run.id}/cancel`, "POST", {})) }, "取消這首") : null,
    queued.map(q => h("span", { class: "chipq" }, `排隊 ${q.queue_position ?? ""}：${q.title || ""}`,
      h("button", { "aria-label": `取消排隊中的 ${q.title || ""}`, onclick: () => guard(() => api(`jobs/${q.id}/cancel`, "POST", {})) }, "✕"))),
    recent.map((r, i) => h("button", { class: "chipq" + (i ? " extra" : ""), style: "cursor:pointer", onclick: () => r.take_id ? openTake(r.take_id) : showJobProblem(r) },
      h("span", { class: "led " + (r.status === "done" ? "on" : r.status === "failed" ? "err" : ""), "aria-hidden": "true" }),
      `${r.title || ""}${r.status === "failed" ? "（失敗）" : r.status === "cancelled" ? "（已取消）" : ""}`)));
  put($("dock"), h("div", { class: "dock-in" }, now, side));
  clearTimeout(dockTimer);
  if (run) dockTimer = setTimeout(renderDock, 1000);
}
async function openTake(id) {
  S.take = await guard(() => api("tracks/" + encodeURIComponent(id)));
  if (!S.take) return;
  S.follow = null;
  if (S.view !== "create") show("create"); else renderStage();
}
function showJobProblem(j) { S.follow = j.id; S.take = null; if (S.view !== "create") show("create"); else renderStage(); }

// ---------------------------------------------------------------- plan preview
function formBody() {
  const f = S.form;
  return { style: f.style, description: f.description, moods: f.moods || [], workflow: f.workflow, quality: f.quality,
    duration: f.duration, bpm: f.bpm, key: f.key, variants: f.variants, seed: f.seed, title: f.title,
    caption_extra: f.caption_extra, caption: f.caption,
    instruments: f.instr ? Object.keys(f.instr).filter(i => f.instr[i] === "use") : null,
    avoid_instruments: f.instr ? Object.keys(f.instr).filter(i => f.instr[i] === "avoid") : [],
    engine_params: Object.fromEntries(Object.entries(f.engine_params || {}).filter(([, v]) => v !== "" && v != null)) };
}
let planTimer, planSeq = 0;
function schedulePlan() { clearTimeout(planTimer); planTimer = setTimeout(refreshPlan, 350); }
async function refreshPlan() {
  const box = $("sendout"); if (!box) return;
  const seq = ++planSeq;
  try { const r = await api("plan", "POST", formBody()); if (seq === planSeq) { S.plan = r; renderSendout(r); } }
  catch (e) { if (seq === planSeq) put($("so-info") || box, h("div", { class: "note err", role: "alert" }, e.message)); }
}
function renderSendout(r) {
  const box = $("sendout"); if (!box) return;
  const spec = r.spec, p = r.params, parts = spec.caption_parts || {};
  const groups = [["override", "你寫的 caption"], ["description", "來自你的描述"], ["extra", "額外標籤"], ["instruments", "樂器"], ["moods", "情緒"], ["style", "風格"]];
  const kept = new Set(spec.caption.split(", ").map(t => t.toLowerCase()));
  const yours = new Set(["override", "description", "extra", ...(spec.instruments?.mode === "custom" ? ["instruments"] : [])]);
  const rows = groups.map(([k, label]) => {
    const tags = (parts[k] || []).filter(t => kept.has(t.toLowerCase()));
    return tags.length ? h("div", { class: "tagrow" }, h("span", { class: "src" }, label), tags.map(t => h("span", { class: "tag" + (yours.has(k) ? " yours" : "") }, t))) : null;
  });
  const lm = p.thinking && p.lm_model ? String(p.lm_model).replace("acestep-5Hz-lm-", "") : "不使用";
  if (!$("so-info")) put(box, h("div", { id: "so-info" }), h("div", { id: "so-edit" }));
  put($("so-info"), h("h3", {}, "會送給 ACE-Step 的內容"), rows,
    h("div", { class: "readouts" }, readout("BPM", spec.bpm), readout("調性", spec.key), readout("長度", `${spec.duration} 秒`),
      readout("版本", p.batch_size), readout("模型", String(p.dit_model).replace("acestep-v15-", "")), readout("步數", p.inference_steps),
      readout("CFG", p.guidance_scale), readout("shift", p.shift), readout("語言模型", lm), readout("量化", p.quantization ? "int8" : "無")),
    Object.keys(spec.engine_params || {}).length ? h("p", { class: "dim small" }, "這首單獨調整：" +
      Object.entries(spec.engine_params).map(([k, v]) => `${k} = ${v}`).join("、")) : null,
    [...(spec.warnings || []), ...(r.warnings || [])].map(w => h("div", { class: "note" }, w)));
  renderCaptionEditor();
  renderKnobPlaceholders(r);
}
function renderCaptionEditor() {
  const f = S.form, host = $("so-edit"); if (!host) return;
  const editing = f.caption != null;
  if (host.dataset.mode === String(editing)) return;  // keep the textarea (and its focus) while typing
  host.dataset.mode = String(editing);
  if (editing) {
    put(host, h("label", { for: "f-caption" }, "手動 caption（英文標籤，逗號分隔，最多 512 字）"),
      h("textarea", { id: "f-caption", oninput: e => { f.caption = e.target.value; schedulePlan(); } }, f.caption),
      h("button", { class: "btn sm quiet", onclick: () => { f.caption = null; renderCaptionEditor(); refreshPlan(); } }, "改回自動產生"));
  } else {
    put(host, h("button", { class: "btn sm quiet", style: "margin-top:8px", onclick: () => { f.caption = S.plan?.spec.caption || ""; renderCaptionEditor(); setTimeout(() => $("f-caption")?.focus(), 50); } }, "自己改 caption"));
  }
}

// ---------------------------------------------------------------- create view
function viewCreate() {
  const st = S.state, f = S.form;
  st.styles.sort((x, y) => (y.id === "from-description") - (x.id === "from-description"));
  f.style = f.style || st.styles[0]?.id;
  f.workflow = f.workflow ?? st.defaults.workflow;
  f.quality = f.quality ?? "";
  f.moods = f.moods || [];
  const styleObj = () => st.styles.find(s => s.id === f.style);
  const styleHint = h("p", { class: "dim small", style: "margin:6px 0 0" });
  const durationInput = h("input", { type: "number", id: "f-duration", min: "10", step: "5", value: f.duration ?? "", oninput: e => (f.duration = e.target.value) });
  // instruments: tri-state chips (use / avoid / neutral), seeded from the style until the person touches one
  const instrState = () => {
    if (f.instr) return f.instr;
    const si = styleObj()?.instruments || {}, m = {};
    (si.suggest || []).forEach(i => (m[i] = "use")); (si.avoid || []).forEach(i => (m[i] = "avoid"));
    return m;
  };
  const instrBox = h("div", { class: "ichips", role: "group", "aria-labelledby": "instr-l" });
  const instrSum = h("span", { class: "dim small" });
  const renderInstr = () => {
    const m = instrState(), lab = id => st.instruments.find(x => x.id === id)?.label || id;
    const use = Object.keys(m).filter(i => m[i] === "use"), avoid = Object.keys(m).filter(i => m[i] === "avoid");
    instrSum.textContent = `${f.instr ? "自訂" : "依風格"}：${use.map(lab).join("、") || "不指定"}${avoid.length ? `；避免 ${avoid.map(lab).join("、")}` : ""}`;
    put(instrBox, (st.instruments || []).map(x => {
      const v = m[x.id];
      return h("button", { type: "button", class: "ichip" + (v ? " " + v : ""), "aria-pressed": v === "use" ? "true" : v === "avoid" ? "mixed" : "false",
        title: `${x.tags}（點一下切換：使用 → 避免 → 不指定）`,
        onclick: () => { f.instr = { ...instrState() }; f.instr[x.id] = v === "use" ? "avoid" : v === "avoid" ? undefined : "use";
          if (!f.instr[x.id]) delete f.instr[x.id]; renderInstr(); schedulePlan(); } },
        (v === "use" ? "✓ " : v === "avoid" ? "✕ " : "") + x.label);
    }), f.instr ? h("button", { type: "button", class: "btn sm quiet", onclick: () => { f.instr = null; renderInstr(); schedulePlan(); } }, "改回依風格") : null);
  };
  const updateHint = () => {
    const s = styleObj(), d = durOf(s);
    styleHint.textContent = descOf(s);
    durationInput.placeholder = d.default ? `風格預設 ${d.default}` : `預設 ${st.defaults.duration}`;
  };
  const text = (id, key, label, ph, type = "text") => [
    h("label", { for: id }, label),
    h("input", { type, id, placeholder: ph, value: f[key] ?? "", oninput: e => (f[key] = e.target.value) })];
  const wfHint = h("p", { class: "dim small", style: "margin:6px 0 0" }, descOf(st.workflows.find(w => w.id === f.workflow)));
  const genBtn = h("button", { class: "btn go", id: "gen", onclick: () => guard(() => generate(genBtn)) }, "開始生成");

  const form = h("section", { class: "module", "aria-labelledby": "h-new" },
    h("h2", { id: "h-new" }, "新作品"),
    h("label", { for: "f-desc" }, "想要什麼樣的音樂", h("span", { class: "hint" }, "（中英文都可以）")),
    h("textarea", { id: "f-desc", placeholder: "例：遊戲失敗畫面，稀疏的鋼琴，有點落寞但不絕望", oninput: e => (f.description = e.target.value) }, f.description || ""),
    h("label", { for: "f-style" }, "風格"),
    h("select", { id: "f-style", onchange: e => { f.style = e.target.value; f.instr = null; updateHint(); renderInstr(); } },
      st.styles.map(s => h("option", { value: s.id, selected: s.id === f.style }, nameOf(s)))), styleHint,
    h("span", { class: "lbl", id: "moods-l" }, "情緒"),
    h("div", { class: "switches", role: "group", "aria-labelledby": "moods-l" },
      st.moods.map(m => h("label", { class: "switch", style: "margin:0" },
        h("input", { type: "checkbox", checked: f.moods.includes(m.id), onchange: e => { f.moods = e.target.checked ? [...f.moods, m.id] : f.moods.filter(x => x !== m.id); } }),
        h("span", { title: m.caption }, m.label_zh || m.id)))),
    h("details", { class: "instr" }, h("summary", { id: "instr-l" }, h("span", { style: "white-space:nowrap;margin-right:8px" }, "樂器"), instrSum), instrBox),
    h("div", { class: "row" },
      h("div", {}, h("label", { for: "f-workflow" }, "用途"),
        h("select", { id: "f-workflow", onchange: e => { f.workflow = e.target.value; wfHint.textContent = descOf(st.workflows.find(w => w.id === f.workflow)); } },
          st.workflows.map(w => h("option", { value: w.id, selected: w.id === f.workflow }, nameOf(w))))),
      h("div", {}, h("label", { for: "f-duration" }, "長度（秒）"), durationInput)), wfHint,
    h("details", {}, h("summary", {}, "進階：品質、BPM、調性、版本數、種子"),
      h("div", { class: "row" },
        h("div", {}, h("label", { for: "f-quality" }, "品質"),
          h("select", { id: "f-quality", onchange: e => (f.quality = e.target.value) },
            h("option", { value: "" }, "依用途"), st.qualities.map(q => h("option", { value: q, selected: q === f.quality }, q)))),
        h("div", {}, text("f-bpm", "bpm", "BPM", "自動", "number")),
        h("div", {}, text("f-key", "key", "調性", "例：D minor"))),
      h("div", { class: "row" },
        h("div", {}, text("f-variants", "variants", "版本數", "依品質", "number")),
        h("div", {}, text("f-seed", "seed", "種子", "隨機", "number"))),
      text("f-title", "title", "標題", "自動"),
      text("f-extra", "caption_extra", "額外英文標籤", "例：felt piano, distant drone")),
    h("details", { id: "knob-panel" }, h("summary", {}, "進階：生成參數（步數、CFG、shift、語言模型）"),
      h("p", { class: "dim small" }, "只影響這一首。空白 = 用設定裡的值（灰字）。全部參數的說明與預設值在「設定」分頁。"),
      h("div", { id: "knob-fields" }, "載入中…")),
    h("div", { id: "sendout", class: "sendout" }, h("p", { class: "dim small", style: "margin:0" }, "整理中…")),
    h("div", { class: "actions" }, genBtn, h("span", { class: "dim small" }, "可以連續送出，會依序排隊")));
  form.addEventListener("input", schedulePlan); form.addEventListener("change", schedulePlan);
  updateHint(); renderInstr(); setTimeout(refreshPlan, 0); loadHealth();
  put($view, h("div", { id: "health" }), h("div", { class: "split" }, form, h("div", { id: "stage" })));
  renderStage();
  renderKnobFields();
}
async function loadHealth() {
  let r; try { r = await api("check"); } catch (e) { return; }
  const box = $("health"); if (!box || !box.isConnected) return;
  const mock = S.state.engine === "mock";
  const items = [...(r.problems || []).filter(p => !(mock && /ace_step_dir|checkpoints|models for this tier|no NVIDIA/.test(p))), ...(r.config_problems || [])];
  const notes = r.notes || [];
  if (!items.length && !notes.length) return put(box);
  put(box, h("div", { class: items.length ? "banner" : "banner soft", role: items.length ? "alert" : "status" },
    h("b", {}, items.length ? "環境還沒準備好，真的生成可能會失敗" : "提醒"),
    h("ul", {}, [...items, ...notes].map(x => h("li", {}, x))),
    items.length ? h("p", { class: "small dim", style: "margin:6px 0 0" }, "完整報告：", h("code", {}, "python scripts/engine.py check"), "。也可以請 Claude 直接幫你修。") : null));
}
async function generate(btn) {
  btn.disabled = true;
  try {
    const r = await api("jobs", "POST", formBody());
    S.follow = r.job; S.take = null;
    toast(r.position > 1 ? `已排入佇列，第 ${r.position} 位` : "已開始");
    renderStage();
  } finally { btn.disabled = false; }
}

// ---------------------------------------------------------------- stage: following job or a take on the deck
function renderStage() {
  const host = $("stage"); if (!host) return;
  if (S.take) return renderTake(S.take, host);
  const j = S.follow && S.jobs.get(S.follow);
  if (j && ["failed", "cancelled"].includes(j.status)) {
    return put(host, h("section", { class: "module" }, h("h2", {}, j.status === "failed" ? "這首沒有生成成功" : "已取消"),
      j.error ? h("div", { class: "note err", role: "alert" }, j.error.message || j.error.code, j.error.hint ? h("div", { class: "small dim" }, j.error.hint) : null) : null,
      (j.warnings || []).map(w => h("div", { class: "note" }, w)),
      h("details", { open: j.status === "failed" }, h("summary", {}, "引擎記錄"), h("div", { class: "log", id: "joblog" }, "載入中…")),
      h("div", { class: "actions" }, h("button", { class: "btn", onclick: () => { S.follow = null; renderStage(); } }, "關閉"))))
      , guard(async () => { const full = await api("jobs/" + j.id); put($("joblog"), (full.log || []).slice(-80).join("\n") || "（沒有記錄）"); });
  }
  if (j) {
    return put(host, h("section", { class: "module", "aria-live": "polite" },
      h("h2", {}, j.status === "queued" ? `排隊中（第 ${j.queue_position ?? "?"} 位）` : "生成中"),
      h("p", { class: "caption-line", style: "margin-left:8px" }, j.spec?.caption || ""),
      stepList(j),
      (j.warnings || []).map(w => h("div", { class: "note" + (/CPU|cpu/.test(w) ? " err" : "") }, w)),
      h("p", { class: "dim small" }, "完成後會直接出現在這裡，可以比較版本、挑選、後製。")));
  }
  put(host, h("section", { class: "module" }, h("div", { class: "empty-deck" },
    h("b", {}, "生成的版本會在這裡並排比較"),
    "所有版本對齊在同一條時間軸，播放時用數字鍵切換，會從同一個位置接著聽。")));
}

// ---------------------------------------------------------------- the comparison deck
const PEAKS = new Map();
let AC;
async function peaksFor(url, buckets = 1200) {
  if (PEAKS.has(url)) return PEAKS.get(url);
  const p = (async () => {
    AC = AC || new (window.AudioContext || window.webkitAudioContext)();
    const buf = await (await fetch(url)).arrayBuffer();
    const audio = await AC.decodeAudioData(buf);
    const ch = [...Array(audio.numberOfChannels).keys()].map(i => audio.getChannelData(i));
    const n = audio.length, step = Math.max(1, Math.floor(n / buckets)), out = new Float32Array(buckets * 2);
    for (let b = 0; b < buckets; b++) {
      let lo = 0, hi = 0;
      const start = b * step, end = Math.min(n, start + step);
      for (let i = start; i < end; i += 4) for (const c of ch) { const v = c[i]; if (v < lo) lo = v; if (v > hi) hi = v; }
      out[b * 2] = lo; out[b * 2 + 1] = hi;
    }
    return { peaks: out, duration: audio.duration };
  })();
  PEAKS.set(url, p);
  return p.catch(e => { PEAKS.delete(url); throw e; });
}
function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function drawWave(canvas, data, active) {
  const dpr = window.devicePixelRatio || 1, w = canvas.clientWidth, hgt = canvas.clientHeight;
  canvas.width = Math.round(w * dpr); canvas.height = Math.round(hgt * dpr);
  const g = canvas.getContext("2d"); g.scale(dpr, dpr); g.clearRect(0, 0, w, hgt);
  if (!data) return;
  const n = data.peaks.length / 2, mid = hgt / 2, amp = hgt * 0.44;
  g.fillStyle = active ? css("--wave-hot") : css("--wave");
  for (let x = 0; x < w; x++) {
    const b = Math.floor(x / w * n);
    const lo = data.peaks[b * 2], hi = data.peaks[b * 2 + 1];
    g.fillRect(x, mid - hi * amp, 1, Math.max(1, (hi - lo) * amp));
  }
}
function drawRuler(canvas, duration, bpm, beats) {
  const dpr = window.devicePixelRatio || 1, w = canvas.clientWidth, hgt = canvas.clientHeight;
  canvas.width = Math.round(w * dpr); canvas.height = Math.round(hgt * dpr);
  const g = canvas.getContext("2d"); g.scale(dpr, dpr); g.clearRect(0, 0, w, hgt);
  if (!duration) return;
  g.font = `500 12px ${css("--font-dial")}`; g.textBaseline = "top";
  const dim = css("--ink-dim"), rail = css("--rail");
  if (bpm) {  // bar lines: musicians count bars, not seconds
    const bar = 60 / bpm * (beats || 4), every = Math.max(1, Math.ceil(40 / (bar / duration * w)));
    for (let i = 0, t = 0; t <= duration + 1e-6; i++, t = i * bar) {
      const x = Math.round(t / duration * w) + .5;
      const major = i % every === 0;
      g.fillStyle = major ? dim : rail;
      g.fillRect(x, major ? 8 : 16, 1, major ? 18 : 10);
      if (major && x < w - 18) g.fillText(String(i + 1), x + 3, 2);
    }
  } else {
    for (let t = 0; t <= duration; t += 10) {
      const x = Math.round(t / duration * w) + .5;
      g.fillStyle = dim; g.fillRect(x, 10, 1, 16); if (x < w - 28) g.fillText(clock(t), x + 3, 2);
    }
  }
}

const deck = {
  take: null, lanes: [], active: 0, raf: 0, duration: 0,
  stop() {
    cancelAnimationFrame(this.raf);
    for (const l of this.lanes) { try { l.audio.pause(); } catch (e) { /* ignore */ } }
    this.lanes = []; this.take = null;
  },
  mount(take, host, picked) {
    this.stop();
    this.take = take;
    const variants = take.variants.filter(v => v.exists !== false);
    const spec = take.spec || {};
    this.duration = spec.duration || 0;
    const ruler = h("canvas", { "aria-hidden": "true" });
    const playhead = h("div", { class: "playhead", "aria-hidden": "true" });
    const lanesEl = variants.map((v, i) => {
      const canvas = h("canvas", { role: "img", "aria-label": `版本 ${v.index} 波形` });
      const audio = new Audio(); audio.preload = "auto"; audio.src = audioUrl(take.id, v.file);
      const el = h("div", { class: "lane" + (v.index === picked ? " picked" : ""), "data-i": String(i) },
        h("div", { class: "tagside" }, h("b", {}, `v${v.index}`), h("span", { class: "num" }, `種子 ${v.seed ?? "-"}`),
          (v.qc || []).length ? h("span", { class: "qcflag", title: v.qc.map(issueText).join("\n") }, `⚠ ${v.qc.length} 項提示`) : null),
        h("div", { class: "wavebox" }, canvas));
      el.addEventListener("click", e => {
        const box = canvas.getBoundingClientRect();
        const inWave = e.clientX >= box.left;
        const t = inWave ? (e.clientX - box.left) / box.width * (this.duration || audio.duration || 0) : null;
        this.select(i, t);
      });
      const lane = { v, el, canvas, audio, data: null };
      audio.addEventListener("loadedmetadata", () => { if (!this.duration || i === 0) this.duration = audio.duration || this.duration; this.redraw(); });
      audio.addEventListener("ended", () => { if (this.lanes[this.active] === lane) this.paint(); });
      peaksFor(audio.src).then(d => { lane.data = d; if (!this.duration) this.duration = d.duration; this.redraw(); }).catch(() => {});
      return lane;
    });
    this.lanes = lanesEl;
    this.active = Math.max(0, variants.findIndex(v => v.index === picked));
    const playBtn = h("button", { class: "btn go play", "aria-label": "播放 / 暫停（空白鍵）", onclick: () => this.toggle() }, "▶");
    const time = h("span", { class: "time", "aria-live": "off" }, "0:00");
    const box = h("div", { class: "deck", tabindex: "0", "aria-label": "版本比較台。空白鍵播放，數字鍵切換版本，左右鍵快轉" },
      h("div", { class: "ruler" }, h("div", {}), h("div", { class: "wavebox" }, ruler)),
      lanesEl.map(l => l.el), playhead);
    box.addEventListener("keydown", e => {
      if (e.key === " ") { e.preventDefault(); this.toggle(); }
      else if (/^[1-9]$/.test(e.key) && this.lanes[+e.key - 1]) this.select(+e.key - 1, null);
      else if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); const a = this.cur(); this.seek(a.currentTime + (e.key === "ArrowRight" ? 5 : -5)); }
    });
    this.ui = { ruler, playhead, playBtn, time, box };
    put(host, box, h("div", { class: "transport" }, playBtn, time,
      h("span", { class: "keys" }, "空白鍵 播放／暫停　數字鍵 切換版本（同一位置接著聽）　← → 快轉 5 秒")));
    this.redraw();
    if (!this._resize) { this._resize = () => this.redraw(); window.addEventListener("resize", this._resize); }
  },
  cur() { return this.lanes[this.active].audio; },
  redraw() {
    if (!this.ui || !this.lanes.length) return;
    const spec = this.take?.spec || {};
    drawRuler(this.ui.ruler, this.duration, spec.bpm, parseInt(spec.time_signature || "4", 10));
    this.lanes.forEach((l, i) => { l.el.classList.toggle("active", i === this.active); drawWave(l.canvas, l.data, i === this.active); });
    this.paint();
  },
  paint() {
    if (!this.ui || !this.lanes.length) return;
    const a = this.cur(), canvas = this.lanes[0].canvas;
    const frac = this.duration ? Math.min(1, a.currentTime / this.duration) : 0;
    this.ui.playhead.style.transform = `translateX(${frac * canvas.clientWidth}px)`;
    this.ui.time.textContent = `${clock(a.currentTime)} / ${clock(this.duration)}`;
    this.ui.playBtn.textContent = a.paused ? "▶" : "❚❚";
  },
  loop() { this.paint(); if (!this.cur().paused) this.raf = requestAnimationFrame(() => this.loop()); },
  toggle() {
    const a = this.cur();
    if (a.paused) { a.play().then(() => this.loop()).catch(e => toast("無法播放：" + e.message, true)); } else { a.pause(); this.paint(); }
  },
  seek(t) { const a = this.cur(); a.currentTime = Math.max(0, Math.min(this.duration || a.duration || 0, t)); this.paint(); },
  select(i, t) {
    const prev = this.cur(), wasPlaying = !prev.paused, at = t ?? prev.currentTime;
    if (i !== this.active) { prev.pause(); this.active = i; this.redraw(); }
    const a = this.cur();
    a.currentTime = Math.min(at, (a.duration || this.duration || at));
    if (wasPlaying || t != null && !prev.paused) a.play().then(() => this.loop()).catch(() => {});
    this.paint();
  },
};

const ISSUE_TEXT = {
  clipping: i => `${clock(i.at)} 起有削波（爆音）${i.count ? `，共 ${i.count} 處` : ""}`,
  clicks: i => `${clock(i.at)} 有咔噠聲${i.count > 1 ? `，共 ${i.count} 處` : ""}`,
  silence: i => `${clock(i.at)}–${clock(i.end)} 中間有一段靜音`,
  cut_off: i => `結尾像是被切斷（${clock(i.at)} 還在全音量）`,
  near_silent: () => "幾乎沒有聲音",
  low_volume: i => `音量偏小（約 ${i.rms_db} dBFS）`,
  dull: i => `聲音發悶（4 kHz 以上只有 ${i.hf_pct}% 的能量，95% 集中在 ${i.rolloff95_hz} Hz 以下）`,
};
const issueText = i => (ISSUE_TEXT[i.code] || (() => i.code))(i);
function issueList(variants) {
  const rows = variants.filter(v => (v.qc || []).length).flatMap(v => v.qc.map(i => h("li", {}, `v${v.index}：${issueText(i)}`)));
  const checked = variants.some(v => Array.isArray(v.qc));
  if (!checked) return null;
  return rows.length ? h("div", {}, h("p", { class: "small dim", style: "margin:10px 0 0" }, "自動檢查（啟發式，最後以耳朵為準）："), h("ul", { class: "qc" }, rows))
    : h("div", { class: "note ok" }, "自動檢查：各版本都沒有發現爆音、咔噠聲、斷尾或靜音");
}

function renderTake(take, host) {
  const picked = take.annotations?.picked || take.variants[0]?.index;
  const reload = async () => { S.take = take = await api("tracks/" + encodeURIComponent(take.id)); renderTake(take, host); };
  const patch = fields => guard(async () => { await api("tracks/" + encodeURIComponent(take.id), "PATCH", fields); await reload(); });
  const spec = take.spec || {};
  const deckHost = h("div", {});
  const activeIndex = () => deck.lanes[deck.active]?.v.index ?? picked;
  const wfSel = h("select", { id: "fin-wf", "aria-label": "後製用途" },
    S.state.workflows.map(w => h("option", { value: w.id, selected: w.id === (spec.workflow || S.state.defaults.workflow) }, nameOf(w))));
  const loudSel = h("select", { id: "fin-loud", "aria-label": "響度" },
    h("option", { value: "" }, "依用途的設定"),
    (S.state.loudness_presets || []).map(p => h("option", { value: p.id }, `${p.label}（${p.lufs} LUFS）`)));
  const finBtn = h("button", { class: "btn go", onclick: () => guard(async () => {
    const v = activeIndex();
    finBtn.disabled = true; finBtn.textContent = `v${v} 後製中…`;
    try { await api(`tracks/${encodeURIComponent(take.id)}/finalize`, "POST", { variant: v, workflow: wfSel.value, loudness: loudSel.value || null, preview: true }); toast(`v${v} 已匯出`); await reload(); }
    finally { finBtn.disabled = false; finBtn.textContent = "匯出目前這版"; } }) }, "匯出目前這版");

  put(host,
    h("section", { class: "module", "aria-labelledby": "deck-title" },
      h("div", { class: "deck-head" }, h("h2", { id: "deck-title" }, take.title || take.id),
        h("div", { class: "readouts", style: "margin:0" }, readout("風格", nameOf(S.state.styles.find(x => x.id === spec.style)) || spec.style), readout("BPM", spec.bpm), readout("調性", spec.key),
          readout("長度", clock(spec.duration)), readout("耗時", take.elapsed_s != null ? `${take.elapsed_s} 秒` : null))),
      h("p", { class: "caption-line" }, spec.caption || ""),
      (take.warnings || []).map(w => h("div", { class: "note" }, w)),
      deckHost,
      issueList(take.variants || []),
      h("div", { class: "actions" },
        h("button", { class: "btn", onclick: () => patch({ picked: activeIndex() }) }, "選定目前這版"),
        h("button", { class: "btn", onclick: () => refine(take, activeIndex()) }, "用目前這版微調再生"),
        h("span", { class: "stars", role: "group", "aria-label": "評分" },
          [1, 2, 3, 4, 5].map(n => h("button", { "aria-pressed": String((take.annotations?.rating || 0) >= n), "aria-label": `${n} 星`,
            onclick: () => patch({ rating: (take.annotations?.rating || 0) === n ? 0 : n }) }, "★"))),
        h("button", { class: "btn quiet", "aria-pressed": String(!!take.annotations?.favorite), onclick: () => patch({ favorite: !take.annotations?.favorite }) },
          take.annotations?.favorite ? "♥ 已收藏" : "♡ 收藏"))),
    h("section", { class: "module", "aria-labelledby": "fin-h" },
      h("h2", { id: "fin-h" }, "後製與匯出"),
      h("div", { class: "row" }, h("div", {}, h("label", { for: "fin-wf" }, "依用途處理（循環、長度、響度、格式）"), wfSel),
        h("div", {}, h("label", { for: "fin-loud" }, "響度"), loudSel)),
      h("div", { class: "actions" }, finBtn),
      (take.finals || []).slice().reverse().map(fin => renderFinal(take, fin))),
    h("section", { class: "module" },
      h("h2", {}, "筆記與設定"),
      h("label", { for: "t-title" }, "標題"), h("input", { type: "text", id: "t-title", value: take.title || "" }),
      h("label", { for: "t-notes" }, "筆記"), h("textarea", { id: "t-notes", placeholder: "例如：v2 前奏好，但結尾太突然" }, take.annotations?.notes || ""),
      h("div", { class: "actions" },
        h("button", { class: "btn", onclick: () => patch({ title: $("t-title").value, notes: $("t-notes").value }) }, "儲存標題與筆記"),
        h("button", { class: "btn danger", onclick: () => confirm("把這首移到垃圾桶？之後還能從工作區的 trash 資料夾找回。") &&
          guard(async () => { await api("tracks/" + encodeURIComponent(take.id), "DELETE"); S.take = null; toast("已移到垃圾桶"); show("library"); }) }, "移到垃圾桶")),
      renderDiag(take)));
  deck.mount(take, deckHost, picked);
}
function renderDiag(take) {
  const e = take.effective || {}, p = take.params || {}, lm = take.lm_metadata || {};
  const row = (k, v) => v == null || v === "" ? null : h("tr", {}, h("th", {}, k), h("td", {}, String(v)));
  const ignored = e.ignored_settings || [];
  return h("details", { open: ignored.length > 0 || !!e.cpu_decode }, h("summary", {}, "實際使用的設定（音質不對時先看這裡）"),
    ignored.length ? h("div", { class: "note" }, "你的 ACE-Step 版本不認得這些設定，等於沒生效：" + ignored.join("、")) : null,
    e.cpu_decode ? h("div", { class: "note err" }, "這首的解碼退到了 CPU（顯存不足），下一首會自動先把擴散模型移出顯卡。") : null,
    h("table", {}, h("tbody", {},
      row("硬體等級", take.tier), row("品質", take.quality), row("擴散模型", e.dit_model || p.dit_model),
      row("步數 / shift", e.inference_steps != null ? `${e.inference_steps} / ${e.shift ?? "-"}` : `${p.inference_steps} / ${p.shift}`),
      row("語言模型", e.thinking ? `${e.lm_model}（${e.lm_backend || "?"}）` : "沒有使用：caption 完全照你給的標籤"),
      row("量化", e.dit_model ? (e.quantization || "無") : null),
      row("擴散模型移出顯卡", e.dit_model ? (e.offload_dit_to_cpu ? "是" : "否") : null),
      row("顯存", e.vram_gb ? `${e.vram_gb} GB` : null),
      row("語言模型改寫的 caption", lm.caption || lm.cot_caption),
      row("語言模型判斷的 BPM / 調性", (lm.bpm || lm.keyscale) ? `${lm.bpm || "-"} / ${lm.keyscale || "-"}` : null),
      row("CFG / 取樣", `${p.guidance_scale ?? "-"} / ${p.infer_method || "ACE-Step 內建"}`),
      row("這首單獨調整的參數", Object.entries(take.spec?.engine_params || {}).map(([k, v]) => `${k} = ${fmtVal(v)}`).join("、") || null),
      row("送出的 caption", take.spec?.caption))));
}
function refine(take, index) {
  const s = take.spec || {}, v = take.variants.find(x => x.index === index) || take.variants[0] || {};
  S.form = { style: s.style, description: s.description || "", moods: s.moods || [], workflow: s.workflow, quality: s.quality,
    duration: s.duration, bpm: s.bpm, key: s.key, variants: s.variants, seed: v.seed, title: s.title, caption_extra: "", caption: s.caption,
    engine_params: { ...(s.engine_params || {}) } };
  S.take = null; S.follow = null; show("create");
  toast(`已帶入 v${v.index ?? ""} 的種子和 caption。只改一個標籤再生，最容易保留原本的感覺。`);
}
function renderFinal(take, fin) {
  const r = fin.report || {}, seam = r.seam || r.loop_seam || {};
  const n = (v, d = 1, u = "") => (typeof v === "number" ? v.toFixed(d) + u : null);
  const files = fin.files || [];
  const playable = files.find(f => /\.(ogg|mp3|wav|flac)$/i.test(f) && !/loop-preview/.test(f));
  const preview = files.find(f => /loop-preview/.test(f));
  return h("div", { class: "final" },
    h("div", { class: "tagrow" }, h("b", {}, `v${fin.variant} 成品`), h("span", { class: "dim small" }, (fin.applied || []).join("、"))),
    h("div", { class: "readouts" }, readout("響度", n(r.lufs ?? r.integrated_lufs, 1, " LUFS")), readout("真峰值", n(r.true_peak_db, 1, " dB")),
      readout("長度", clock(r.duration)), seam.seam_vs_typical != null && (fin.applied || []).includes("loop") ? readout("循環接縫", n(seam.seam_vs_typical, 2) + "（約 1 為自然）") : null),
    playable ? h("audio", { controls: true, preload: "none", src: audioUrl(take.id, "final/" + playable), style: "width:100%;margin-top:10px", "aria-label": playable }) : null,
    preview ? h("div", { class: "small dim", style: "margin-top:8px" }, "循環試聽（連播兩次，聽接縫）：",
      h("audio", { controls: true, preload: "none", src: audioUrl(take.id, "final/" + preview), style: "width:100%", "aria-label": "循環試聽" })) : null,
    h("div", { class: "files" }, files.filter(f => !/loop-preview/.test(f)).map(f => h("a", { class: "btn sm", href: audioUrl(take.id, "final/" + f) + "?download=1" }, `下載 ${f.split(".").pop()}`))),
    (r.qc || []).length || (r.issues || []).length ? h("ul", { class: "qc" }, (r.qc || []).map(q => h("li", {}, q)).concat((r.issues || []).map(i => h("li", {}, issueText(i)))))
      : h("div", { class: "note ok" }, "品質檢查沒有發現問題"),
    (fin.warnings || []).concat(fin.notes || []).map(w => h("p", { class: "small dim" }, w)));
}

// ---------------------------------------------------------------- library
async function viewLibrary() {
  const tracks = await guard(() => api("tracks")) || [];
  const q = { text: "", fav: false };
  const list = h("div", { class: "takes" });
  const stage = h("div", { id: "lib-stage" });
  const draw = () => {
    const items = tracks.filter(t => (!q.fav || t.favorite) && (!q.text || `${t.title} ${t.style} ${(t.tags || []).join(" ")}`.toLowerCase().includes(q.text.toLowerCase())));
    put(list, items.length ? items.map(t => h("button", { class: "take-row", onclick: async e => {
      list.querySelectorAll(".take-row").forEach(b => b.removeAttribute("aria-current")); e.currentTarget.setAttribute("aria-current", "true");
      const take = await guard(() => api("tracks/" + encodeURIComponent(t.id)));
      if (take) { S.take = take; renderTake(take, stage); stage.scrollIntoView({ block: "nearest" }); }
    } }, h("span", { class: "t" }, (t.favorite ? "♥ " : "") + (t.title || t.id)), h("span", { class: "r", "aria-label": `${t.rating || 0} 星` }, "★".repeat(t.rating || 0)),
      h("span", { class: "m" }, h("span", {}, t.style || ""), t.bpm ? h("span", { class: "num" }, `${t.bpm} BPM`) : null, t.key ? h("span", {}, t.key) : null,
        h("span", { class: "num" }, clock(t.duration)), h("span", {}, `${t.variants} 版本`), t.finals ? h("span", {}, `${t.finals} 個成品`) : null)))
      : h("div", { class: "empty" }, tracks.length ? "沒有符合的作品。" : "還沒有作品。到「創作」寫一句描述就能開始。"));
  };
  put($view, h("div", { class: "split" },
    h("section", { class: "module" }, h("h2", {}, "作品"),
      h("div", { class: "toolbar" },
        h("input", { type: "text", "aria-label": "搜尋", placeholder: "搜尋標題、風格、標籤", oninput: e => { q.text = e.target.value; draw(); } }),
        h("label", { class: "switch", style: "margin:0" }, h("input", { type: "checkbox", onchange: e => { q.fav = e.target.checked; draw(); } }), h("span", {}, "只看收藏"))),
      list),
    stage));
  put(stage, h("section", { class: "module" }, h("div", { class: "empty-deck" }, h("b", {}, "從左邊選一首"), "會在這裡比較版本、後製、寫筆記。")));
  draw();
}

// ---------------------------------------------------------------- tunable settings (defaults/knobs.json)
const LAYER_LABEL = src => !src ? "ACE-Step 內建" : src === "generation" ? "全域預設" : src === "engine_overrides" ? "強制（engine_overrides）"
  : src.startsWith("preset:") ? `品質預設 ${src.slice(7)}` : src.startsWith("tier:") ? `硬體等級 ${src.slice(5)}` : src === "request" ? "這一首" : src;
const LAYER_RANK = src => !src ? -1 : src === "generation" ? 0 : src.startsWith("tier:") ? 1 : src.startsWith("preset:") ? 2 : src === "engine_overrides" ? 3 : 4;
const fmtVal = v => v == null ? "—" : typeof v === "boolean" ? (v ? "開" : "關") : String(v);
const rangeOf = k => k.type === "bool" ? "開／關" : k.type === "choice" ? k.choices.map(c => c ?? "無").join(" / ")
  : k.min != null ? `${k.min} – ${k.max}${k.unit ? " " + k.unit : ""}` : "文字";
function parseKnob(k, raw) {
  if (raw === "") return k.type === "string" ? null : "";
  if (k.type === "bool") return raw === "true";
  if (k.type === "int" || k.type === "float") return Number(raw);
  if (k.type === "choice") return raw === "null" ? null : raw;
  return raw;
}
function knobInput(k, id, value, onchange, emptyLabel) {
  if (k.type === "bool" || k.type === "choice") {
    const opts = k.type === "bool" ? [true, false] : k.choices;
    return h("select", { id, onchange },
      emptyLabel != null ? h("option", { value: "" }, emptyLabel) : null,
      opts.map(o => h("option", { value: String(o), selected: value !== undefined && value !== "" && String(o) === String(value) }, k.type === "bool" ? fmtVal(o) : o ?? "無")));
  }
  return h("input", { id, type: k.type === "string" ? "text" : "number", min: k.min, max: k.max, step: k.step || (k.type === "int" ? 1 : "any"),
    value: value ?? "", oninput: onchange });
}
async function loadKnobs(quality) {
  const q = quality ? "?quality=" + encodeURIComponent(quality) : "";
  return api("knobs" + q);
}
async function renderKnobFields() {
  const host = $("knob-fields"); if (!host) return;
  const t = S.knobs || (S.knobs = await guard(() => loadKnobs()));
  if (!t) return;
  const f = S.form; f.engine_params = f.engine_params || {};
  const per = t.knobs.filter(k => k.per_request);
  const groups = [...new Set(per.map(k => k.group))];
  put(host, groups.map(g => h("div", {},
    h("h3", { class: "small" }, t.groups[g] || g),
    h("div", { class: "row" }, per.filter(k => k.group === g).map(k => h("div", {},
      h("label", { for: "kp-" + k.key, title: k.help }, k.label, h("span", { class: "hint dim" }, `（${rangeOf(k)}）`)),
      knobInput(k, "kp-" + k.key, f.engine_params[k.key], e => { f.engine_params[k.key] = parseKnob(k, e.target.value); schedulePlan(); }, "依設定"),
      h("div", { class: "dim small", id: "kh-" + k.key }, k.help)))))),
    h("button", { type: "button", class: "btn sm quiet", onclick: () => { f.engine_params = {}; renderKnobFields(); schedulePlan(); } }, "全部改回依設定"));
  if (Object.keys(f.engine_params).length) $("knob-panel").open = true;
  if (S.plan) renderKnobPlaceholders(S.plan);
}
function renderKnobPlaceholders(r) {
  (S.knobs?.knobs || []).filter(k => k.per_request).forEach(k => {
    const el = $("kp-" + k.key); if (!el) return;
    const v = r.params?.[k.key], src = r.sources?.[k.key];
    if (el.tagName === "SELECT") el.options[0].textContent = `依設定（${fmtVal(v)}）`; else el.placeholder = fmtVal(v);
    const hint = $("kh-" + k.key);
    if (hint) hint.textContent = (v == null ? "沒設定，用 ACE-Step 內建值。" : `依設定：${fmtVal(v)}，來自${LAYER_LABEL(src)}。`) + k.help;
  });
}
function knobTable(t, refresh) {
  const save = (k, target, raw) => guard(async () => {
    const v = parseKnob(k, raw);
    if (v === "") return toast("請先填一個值", true);
    const r = await api("config", "PUT", { set: { [`${target}.${k.key}`]: v } });
    S.knobs = null; toast(r.problems.length ? "已儲存，但設定還有問題：" + r.problems[0] : `已把 ${k.label} 設為 ${fmtVal(v)}`, !!r.problems.length); refresh();
  });
  const reset = k => guard(async () => {
    await api("config", "PUT", { unset: k.user_paths }); S.knobs = null; toast(`${k.label} 已還原為內建`); refresh();
  });
  const targets = k => k.layer === "tier" ? [[`hardware.tiers.${t.tier}`, `硬體等級 ${t.tier}`]]
    : [["generation", "全域預設"], [`quality.presets.${t.quality}`, `只有品質 ${t.quality}`], ["engine_overrides", "強制所有品質"]];
  const row = k => {
    const id = "kt-" + k.key, ts = targets(k);
    const def = ts.find(([p]) => k.path && k.path.startsWith(p + ".")) || ts[0];
    const input = knobInput(k, id, k.value, () => {}, k.type === "bool" || k.type === "choice" ? "（選一個）" : null);
    const target = h("select", { "aria-label": "存到哪一層" }, ts.map(([p, l]) => h("option", { value: p, selected: p === def[0] }, l)));
    const shadow = h("div", { class: "dim small" });
    const checkShadow = () => {
      const rank = target.value === "generation" ? 0 : target.value.startsWith("hardware") ? 1 : target.value.startsWith("quality") ? 2 : 3;
      shadow.textContent = LAYER_RANK(k.source) > rank ? `注意：目前生效的是「${LAYER_LABEL(k.source)}」，存到這一層會被它蓋過。` : "";
    };
    target.addEventListener("change", checkShadow); checkShadow();
    return h("tr", {},
      h("td", {}, h("b", {}, k.label), h("div", {}, h("code", { class: "small" }, k.key)), h("div", { class: "dim small" }, k.help)),
      h("td", { style: "white-space:nowrap" }, h("b", {}, fmtVal(k.value)),
        h("div", { class: "dim small" }, LAYER_LABEL(k.source) + (k.from_user ? "（你改過）" : "")),
        k.adjusted_from != null ? h("div", { class: "dim small" }, `設定是 ${fmtVal(k.adjusted_from)}，依硬體自動調整`) : null,
        h("div", { class: "dim small" }, "範圍 " + rangeOf(k))),
      h("td", {}, input, target, shadow,
        h("div", { class: "actions", style: "margin-top:4px" },
          h("button", { class: "btn sm", onclick: () => save(k, target.value, input.value) }, "儲存"),
          k.user_paths.length ? h("button", { class: "btn sm quiet", title: k.user_paths.join("\n"), onclick: () => reset(k) }, "還原內建") : null)));
  };
  const groups = [...new Set(t.knobs.map(k => k.group))];
  return groups.map(g => [h("h3", {}, t.groups[g] || g),
    h("table", { class: "knobs" }, h("thead", {}, h("tr", {}, h("th", {}, "參數"), h("th", {}, "目前值"), h("th", {}, "修改"))),
      h("tbody", {}, t.knobs.filter(k => k.group === g).map(row)))]);
}
function layerTables(t) {
  const pkeys = [...new Set(Object.values(t.presets).flatMap(Object.keys))];
  const tkeys = [...new Set(Object.values(t.tiers).flatMap(Object.keys))];
  const ov = Object.entries(t.engine_overrides || {}).filter(([k]) => !k.startsWith("_"));
  return [
    h("h3", {}, "品質預設的內容"),
    h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "品質"), pkeys.map(k => h("th", {}, k)))),
      h("tbody", {}, Object.entries(t.presets).map(([q, p]) => h("tr", {}, h("td", {}, h("b", {}, q), q === t.quality ? "（目前）" : null), pkeys.map(k => h("td", {}, fmtVal(p[k]))))))),
    h("h3", {}, "硬體等級表"),
    h("table", {}, h("thead", {}, h("tr", {}, h("th", {}, "等級"), tkeys.map(k => h("th", {}, k)))),
      h("tbody", {}, Object.entries(t.tiers).map(([n, c]) => h("tr", {}, h("td", {}, h("b", {}, n), n === t.tier ? "（你的顯卡）" : null), tkeys.map(k => h("td", {}, fmtVal(c[k]))))))),
    h("p", { class: "dim small" }, ov.length ? "engine_overrides（強制所有品質）：" + ov.map(([k, v]) => `${k} = ${fmtVal(v)}`).join("、") : "engine_overrides 目前是空的（建議保持空白，否則會蓋過所有品質預設）。"),
    t.not_passed.length ? h("details", {}, h("summary", {}, `ACE-Step 還有、但 Music Studio 尚未接上的 ${t.not_passed.length} 組參數`),
      h("ul", {}, t.not_passed.map(x => h("li", {}, h("code", {}, x.key), "：", x.label)))) : null];
}
async function renderKnobSection(host, quality) {
  const t = await guard(() => loadKnobs(quality)); if (!t) return;
  const qSel = h("select", { id: "kq", onchange: e => renderKnobSection(host, e.target.value) },
    Object.keys(t.presets).map(q => h("option", { value: q, selected: q === t.quality }, q)));
  put(host, h("h2", {}, "所有可調的生成參數"),
    h("p", { class: "dim small" }, "每個參數的值依序由這幾層決定，後面的蓋過前面的：全域預設 → 硬體等級 → 品質預設 → 強制（engine_overrides）→ 這一首（建立頁的「進階」）。改動只寫進你的工作區 config.json。"),
    h("div", { class: "row" }, h("div", {}, h("label", { for: "kq" }, "看哪個品質預設下的值"), qSel), h("div", {}, h("span", { class: "lbl" }, "硬體等級"), h("div", {}, h("b", {}, t.tier)))),
    (t.warnings || []).map(w => h("div", { class: "note" }, w)),
    knobTable(t, () => renderKnobSection(host, t.quality)), layerTables(t));
}

// ---------------------------------------------------------------- settings
async function viewSettings() {
  const { config, sources } = await guard(() => api("config")) || {};
  if (!config) return;
  const src = key => (sources && sources[key]) || "default";
  const field = (key, label, type = "text", opts) => {
    const cur = key.split(".").reduce((o, k) => (o ? o[k] : undefined), config);
    const id = "c-" + key.replace(/\./g, "-");
    const input = opts ? h("select", { id }, opts.map(o => h("option", { value: o, selected: String(o) === String(cur) }, o)))
                       : h("input", { type, id, value: cur ?? "" });
    input.dataset.key = key; input.dataset.type = type;
    return [h("label", { for: id }, label, h("span", { class: "hint" }, src(key) === "default" ? "（預設）" : "（你改過）")), input];
  };
  const save = h("button", { class: "btn go", onclick: () => guard(async () => {
    const set = {};
    document.querySelectorAll("[data-key]").forEach(el => { const v = el.value.trim(); if (v !== "") set[el.dataset.key] = el.dataset.type === "number" ? Number(v) : v; });
    const r = await api("config", "PUT", { set });
    await refreshState(); toast(r.problems.length ? "已儲存，但設定還有問題" : "已儲存設定"); viewSettings();
  }) }, "儲存設定");
  const reset = key => guard(async () => { await api("config", "PUT", { unset: [key] }); toast(`${key} 已還原為預設`); viewSettings(); });
  const editor = h("section", { class: "module", id: "style-editor", hidden: true });
  function editStyle(s) {
    const d = durOf(s), bpm = [].concat(s.bpm || []);
    const v = { id: s.id, name: nameOf(s), description: descOf(s), caption: s.caption || "", avoid: s.avoid || "",
      bmin: bpm[0] ?? "", bmax: bpm[bpm.length - 1] ?? "", keys: (s.keys || []).join(", "), dur: d.default ?? "" };
    const inp = (k, label, type = "text") => [h("label", { for: "se-" + k }, label), h("input", { type, id: "se-" + k, value: v[k], oninput: e => (v[k] = e.target.value) })];
    editor.hidden = false;
    put(editor, h("h2", {}, `編輯風格：${nameOf(s)}`), h("p", { class: "dim small" }, "存到你的工作區，不會改到內建風格。改 ID 就是另存一份新的。"),
      inp("id", "ID（英文、數字、- _）"), inp("name", "名稱"), inp("description", "說明"),
      h("label", { for: "se-caption" }, "Caption（英文標籤，逗號分隔）"), h("textarea", { id: "se-caption", oninput: e => (v.caption = e.target.value) }, v.caption),
      inp("avoid", "要避免的"), h("div", { class: "row" }, h("div", {}, inp("bmin", "BPM 下限", "number")), h("div", {}, inp("bmax", "BPM 上限", "number")), h("div", {}, inp("dur", "預設長度（秒）", "number"))),
      inp("keys", "調性（逗號分隔）"),
      h("div", { class: "actions" }, h("button", { class: "btn go", onclick: () => guard(async () => {
        const obj = { ...s, id: v.id, name: s.name || v.name, name_zh: v.name, description: s.description || v.description, description_zh: v.description, caption: v.caption, avoid: v.avoid, keys: v.keys.split(",").map(x => x.trim()).filter(Boolean) };
        delete obj.source; delete obj._source;
        if (v.bmin !== "" && v.bmax !== "") obj.bpm = [Number(v.bmin), Number(v.bmax)];
        if (v.dur !== "") obj.duration = { ...durOf(s), default: Number(v.dur) };
        await api("styles/" + encodeURIComponent(v.id), "PUT", obj); await refreshState(); toast("已儲存風格"); viewSettings();
      }) }, "儲存風格"), h("button", { class: "btn quiet", onclick: () => (editor.hidden = true) }, "取消")));
    editor.scrollIntoView({ block: "nearest" });
  }
  const knobHost = h("section", { class: "module", id: "knobs", style: "margin-top:16px" }, "載入參數表…");
  const userKeys = Object.keys(sources || {}).filter(k => sources[k] && sources[k] !== "default");
  put($view, h("div", { class: "two" },
    h("section", { class: "module" }, h("h2", {}, "常用設定"),
      field("hardware.tier", "硬體等級", "text", ["auto", "low", "mid", "high", "ultra"]),
      field("engine", "引擎", "text", ["ace", "mock"]),
      field("ace_step_dir", "ACE-Step 資料夾"),
      field("generation.duration", "預設長度（秒）", "number"),
      field("quality.default", "預設品質", "text", Object.keys(config.quality.presets)),
      field("workflow.default", "預設用途", "text", S.state.workflows.map(w => w.id)),
      field("engine_idle_unload_minutes", "閒置幾分鐘後釋放顯存（0 = 不釋放）", "number"),
      field("postprocess.loudness_lufs", "目標響度（LUFS）", "number"),
      field("postprocess.true_peak_db", "真峰值上限（dB）", "number"),
      field("postprocess.loop_crossfade", "循環交叉淡化（秒）", "number"),
      h("div", { class: "actions" }, save),
      userKeys.length ? h("details", {}, h("summary", {}, `你改過的 ${userKeys.length} 個項目`),
        h("table", {}, h("tbody", {}, userKeys.map(k => h("tr", {}, h("td", {}, h("code", {}, k)), h("td", {}, h("button", { class: "btn sm quiet", onclick: () => reset(k) }, "還原")))))) ) : null,
      h("p", { class: "dim small" }, "擴散、語言模型、硬體等級和品質預設的每個參數都列在下方「所有可調的生成參數」。後製步驟可以直接改工作區的 config.json，或在對話裡跟 Claude 說「以後預設用…」。")),
    h("section", { class: "module" }, h("h2", {}, "風格庫"),
      h("table", {}, h("tbody", {}, S.state.styles.map(s => h("tr", {},
        h("td", {}, h("b", {}, nameOf(s)), h("div", { class: "dim small" }, (s.source || "").includes("user") ? "你的風格" : "內建")),
        h("td", { style: "text-align:right;white-space:nowrap" }, h("button", { class: "btn sm", onclick: () => editStyle(s) }, "編輯"),
          (s.source || "").includes("user") ? h("button", { class: "btn sm danger", style: "margin-left:6px", onclick: () => confirm(`刪除「${s.name || s.id}」？`) && guard(async () => {
            await api("styles/" + encodeURIComponent(s.id), "DELETE"); await refreshState(); viewSettings(); }) }, "刪除") : null)))))),
    editor), knobHost);
  renderKnobSection(knobHost);
}

// ---------------------------------------------------------------- boot
(async () => {
  try { await refreshState(); show("create"); renderDock(); pollLoop(); }
  catch (e) { put($view, h("div", { class: "banner", role: "alert" }, "連不到本機伺服器：" + e.message + "。請重新執行 start_dashboard.bat。")); }
})();
