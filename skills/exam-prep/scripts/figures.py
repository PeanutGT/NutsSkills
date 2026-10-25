"""exam-prep figure helpers: consistent, print-ready teaching figures (SVG).

Every function saves an SVG and returns its path. Embed it in the Markdown with

    :::fig Binomial(10, 0.3) 的機率質量函數
    ![](figs/binom.svg)
    :::

Usage:
    import sys; sys.path.insert(0, "<skill-dir>/scripts")
    import figures as F
    F.pmf_bar(range(11), [binom.pmf(k, 10, .3) for k in range(11)], "figs/binom.svg",
              highlight=lambda k: k <= 2, highlight_label="P(X ≤ 2)")

Design rules baked in (from the dataviz method): one hue per job, categorical slots in
fixed order (max 3 series per chart), 2px lines, recessive grid, direct labels instead of
a legend where possible, text in ink colours (never in the series colour).
"""
from __future__ import annotations

import os
import warnings
from typing import Callable, Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
warnings.filterwarnings("ignore", message="Glyph .* missing from font")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

# ---------------------------------------------------------------- style
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # categorical slots 1-3 (validated all-pairs)
SOFT = ["#cde2fb", "#fbd9c9", "#c9eedf"]  # light fills of the same hues
INK, INK2, MUTED, GRID = "#1f2430", "#4b5262", "#8a8f98", "#e3e5ea"
HIGHLIGHT, BASE = SERIES[1], "#b7d3f6"  # emphasised bars vs the rest

_FONT_SET = False


def _setup():
    global _FONT_SET
    if _FONT_SET:
        return
    families = []
    for name in ["Noto Sans CJK TC", "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", "Noto Sans CJK JP"]:
        try:
            font_manager.findfont(name, fallback_to_default=False)
            families.append(name)
        except Exception:
            pass
    plt.rcParams.update({
        "font.family": "sans-serif",
        # DejaVu first: it has subscripts, ŷ, x̄ etc.; CJK characters fall back to the Noto CJK family
        "font.sans-serif": ["DejaVu Sans"] + families,
        "axes.unicode_minus": False,
        "mathtext.fontset": "cm",
        "font.size": 10,
        "axes.edgecolor": MUTED, "axes.linewidth": 0.8,
        "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
        "axes.axisbelow": True, "axes.titleweight": "bold", "axes.titlesize": 11,
        "axes.titlecolor": INK, "legend.frameon": False,
        "svg.fonttype": "none",  # keep text as text (crisp, searchable in the PDF)
        "figure.dpi": 100,
    })
    _FONT_SET = True


def _fig(w=6.0, h=3.2):
    _setup()
    fig, ax = plt.subplots(figsize=(w, h))
    return fig, ax


def _save(fig, out):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)
    return out


def _label_end(ax, x, y, text, color=INK, dx=4, dy=0, ha="left", va="center"):
    ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, va=va, color=color, fontsize=9)


# ---------------------------------------------------------------- probability / statistics
def pmf_bar(xs: Iterable, ps: Sequence[float], out: str, *, title="", xlabel="k", ylabel="P(X = k)",
            highlight: Callable | None = None, highlight_label="", highlight_value: float | None = None,
            show_values=False, mean: float | None = None):
    """Discrete distribution (Binomial, Poisson, Geometric...). `highlight(k)` colours an event, e.g. P(X ≤ 2).

    The boxed value is the sum of the *plotted* highlighted bars. If the event has a tail beyond the plotted
    range (e.g. P(X > 3) for Geometric/Poisson), pass the exact probability as `highlight_value` — otherwise the
    printed number is too small. A warning is raised when the plotted bars don't sum to ~1."""
    xs, ps = list(xs), list(ps)
    fig, ax = _fig()
    cols = [HIGHLIGHT if highlight and highlight(x) else BASE for x in xs]
    ax.bar(xs, ps, width=0.72, color=cols, edgecolor="white", linewidth=1)
    if show_values:
        for x, p in zip(xs, ps):
            if p >= max(ps) * 0.04:
                ax.text(x, p, f"{p:.3f}", ha="center", va="bottom", fontsize=7.5, color=INK2)
    if highlight and highlight_label:
        tot = sum(p for x, p in zip(xs, ps) if highlight(x))
        if highlight_value is not None:
            tot = highlight_value
        elif sum(ps) < 0.999:
            warnings.warn(f"pmf_bar: plotted probabilities sum to {sum(ps):.4f} < 1; the highlighted total may miss a "
                          f"tail. Pass highlight_value= with the exact probability.", stacklevel=2)
        ax.text(0.98, 0.95, f"{highlight_label} = {tot:.4f}", transform=ax.transAxes, ha="right", va="top",
                fontsize=10, color=INK, bbox=dict(boxstyle="round,pad=0.35", fc="#fff4e6", ec=HIGHLIGHT, lw=1))
    if mean is not None:
        ax.axvline(mean, color=INK2, lw=1.2, ls="--")
        ax.text(mean, max(ps) * 1.06, f"E[X] = {mean:g}", ha="center", va="bottom", fontsize=9, color=INK2,
                bbox=dict(fc="white", ec="none", pad=1.5))
        ax.set_ylim(top=max(ps) * 1.18)
    ax.set_xticks(xs if len(xs) <= 21 else xs[:: max(1, len(xs) // 15)])
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    ax.grid(axis="x", visible=False)
    return _save(fig, out)


def pdf_area(f: Callable, x_range: tuple, out: str, *, shade: tuple | None = None, shade_label="",
             title="", xlabel="x", ylabel="f(x)", marks: dict | None = None):
    """Continuous density with a shaded probability, e.g. normal P(a < X < b). `marks` = {x: "label"} vertical guides."""
    x = np.linspace(*x_range, 600)
    y = np.array([f(v) for v in x])
    fig, ax = _fig()
    ax.plot(x, y, color=SERIES[0], lw=2)
    if shade:
        a, b = max(shade[0], x_range[0]), min(shade[1], x_range[1])
        m = (x >= a) & (x <= b)
        ax.fill_between(x[m], y[m], color=SOFT[1], edgecolor=HIGHLIGHT, linewidth=0)
        if shade_label:
            xm = (a + b) / 2
            ax.text(xm, f(xm) * 0.42, shade_label, ha="center", va="center", fontsize=10, color=INK, fontweight="bold")
    for xv, lab in (marks or {}).items():
        ax.axvline(xv, color=MUTED, lw=1, ls="--")
        ax.text(xv, ax.get_ylim()[1] * 0.98 if ax.get_ylim()[1] else max(y), lab, ha="center", va="top", fontsize=8.5,
                color=INK2, bbox=dict(fc="white", ec="none", pad=1))
    ax.set_ylim(bottom=0)
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    return _save(fig, out)


def compare_curves(series: Sequence[tuple], out: str, *, title="", xlabel="x", ylabel="", discrete=False):
    """Up to 3 series [(xs, ys, "label"), ...] — e.g. Binomial vs Poisson approximation, or normals with different σ.
    Labels are placed directly at the end of each curve (no legend box)."""
    assert len(series) <= 3, "max 3 series per chart; facet instead"
    fig, ax = _fig()
    n = len(series)
    for i, (xs, ys, lab) in enumerate(series):
        xs, ys = np.asarray(list(xs), float), np.asarray(list(ys), float)
        if discrete:
            w = 0.8 / n
            ax.bar(xs + (i - (n - 1) / 2) * w, ys, width=w, color=SERIES[i], edgecolor="white", linewidth=0.8, label=lab)
        else:
            ax.plot(xs, ys, color=SERIES[i], lw=2)
            j = int(np.argmax(ys))
            _label_end(ax, xs[j], ys[j], lab, INK, dx=6, dy=4, va="bottom")
    if discrete:
        ax.legend(loc="upper right", fontsize=9)
        ax.grid(axis="x", visible=False)
    ax.set_ylim(bottom=0)
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    return _save(fig, out)


def cdf_step(xs: Sequence[float], ps: Sequence[float], out: str, *, title="", xlabel="x", ylabel="F(x)"):
    """Step CDF of a discrete distribution with open/closed endpoints."""
    xs, ps = list(xs), list(ps)
    cum = np.cumsum(ps)
    fig, ax = _fig()
    lo, hi = xs[0] - 1, xs[-1] + 1
    edges = [lo] + xs + [hi]
    levels = [0] + list(cum)
    for i in range(len(levels)):
        ax.hlines(levels[i], edges[i], edges[i + 1], color=SERIES[0], lw=2)
    ax.plot(xs, cum, "o", color=SERIES[0], ms=5)  # closed (value attained)
    ax.plot(xs, [0] + list(cum[:-1]), "o", mfc="white", mec=SERIES[0], ms=5)  # open
    ax.set_ylim(-0.03, 1.08)
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    return _save(fig, out)


def histogram(data: Sequence[float], out: str, *, bins=12, density=False, overlay: Callable | None = None,
              overlay_label="", title="", xlabel="", ylabel=None, show_mean=True):
    """Histogram with optional fitted density overlay and mean marker."""
    data = np.asarray(data, float)
    fig, ax = _fig()
    ax.hist(data, bins=bins, density=density, color=BASE, edgecolor="white", linewidth=1)
    if overlay:
        x = np.linspace(data.min(), data.max(), 400)
        ax.plot(x, [overlay(v) for v in x], color=SERIES[1], lw=2)
        if overlay_label:  # label on the right flank, away from the mean marker
            j = int(len(x) * 0.72)
            _label_end(ax, x[j], overlay(x[j]), overlay_label, INK, dx=10, dy=2, va="bottom")
    if show_mean:
        mu = data.mean()
        ax.axvline(mu, color=INK2, lw=1.2, ls="--")
        top = ax.get_ylim()[1]
        ax.set_ylim(top=top * 1.12)
        ax.text(mu, top * 1.04, f"x̄ = {mu:.2f}", ha="right", va="center", fontsize=9, color=INK2,
                bbox=dict(fc="white", ec="none", pad=1.5))
    ax.grid(axis="x", visible=False)
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel or ("密度" if density else "次數"))
    return _save(fig, out)


def boxplot_annotated(data: Sequence[float], out: str, *, title="", xlabel="", annotate=True):
    """Horizontal box plot with Q1 / median / Q3 / IQR / whiskers / outliers labelled — for teaching how to read one."""
    d = np.sort(np.asarray(data, float))
    q1, med, q3 = np.percentile(d, [25, 50, 75])
    iqr = q3 - q1
    lo_f, hi_f = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    w_lo, w_hi = d[d >= lo_f].min(), d[d <= hi_f].max()
    outl = d[(d < lo_f) | (d > hi_f)]
    fig, ax = _fig(6.2, 2.9)
    ax.add_patch(plt.Rectangle((q1, 0.35), iqr, 0.3, fc=SOFT[0], ec=SERIES[0], lw=1.5))
    ax.plot([med, med], [0.35, 0.65], color=SERIES[0], lw=2.5)
    for a, b in [(w_lo, q1), (q3, w_hi)]:
        ax.plot([a, b], [0.5, 0.5], color=SERIES[0], lw=1.5)
    for w in (w_lo, w_hi):
        ax.plot([w, w], [0.42, 0.58], color=SERIES[0], lw=1.5)
    ax.plot(outl, [0.5] * len(outl), "o", mfc="white", mec=SERIES[1], ms=6, mew=1.5)
    if annotate:
        for v, lab, y in [(w_lo, "下鬚", 0.78), (q1, "Q1", 0.78), (med, "中位數", 0.86), (q3, "Q3", 0.78), (w_hi, "上鬚", 0.78)]:
            ax.text(v, y, f"{lab}\n{v:g}", ha="center", va="bottom", fontsize=9, color=INK2, linespacing=1.15)
        ax.annotate("", xy=(q1, 0.25), xytext=(q3, 0.25), arrowprops=dict(arrowstyle="<->", color=INK2, lw=1))
        ax.text((q1 + q3) / 2, 0.2, f"IQR = {iqr:g}", ha="center", va="top", fontsize=9.5, color=INK2)
        for o in outl:
            ax.text(o, 0.62, f"離群值\n{o:g}", ha="center", va="bottom", fontsize=9, color=INK, linespacing=1.15)
    ax.set_ylim(0, 1.2)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.grid(axis="y", visible=False)
    ax.set(title=title, xlabel=xlabel)
    return _save(fig, out)


def scatter_regression(x: Sequence[float], y: Sequence[float], out: str, *, title="", xlabel="x", ylabel="y",
                       show_line=True, show_residuals=False):
    """Scatter with least-squares line, equation and r; optional residual segments."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    b1, b0 = np.polyfit(x, y, 1)
    r = np.corrcoef(x, y)[0, 1]
    fig, ax = _fig()
    if show_residuals:
        for xi, yi in zip(x, y):
            ax.plot([xi, xi], [yi, b0 + b1 * xi], color=SERIES[1], lw=1, alpha=0.8)
    ax.plot(x, y, "o", color=SERIES[0], ms=6, mec="white", mew=1)
    if show_line:
        xx = np.linspace(x.min(), x.max(), 50)
        ax.plot(xx, b0 + b1 * xx, color=INK2, lw=2)
        ax.text(0.02, 0.96, f"ŷ = {b0:.2f} {'+' if b1 >= 0 else '−'} {abs(b1):.2f}x    r = {r:.3f}", transform=ax.transAxes,
                ha="left", va="top", fontsize=9.5, color=INK, bbox=dict(fc="white", ec=GRID, boxstyle="round,pad=0.3"))
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    return _save(fig, out)


def venn2(out: str, *, a="A", b="B", only_a="", both="", only_b="", outside="", title=""):
    """Two-set Venn diagram with region labels (probabilities or counts as strings)."""
    _setup()
    fig, ax = plt.subplots(figsize=(4.6, 2.9))
    ax.add_patch(plt.Rectangle((-2.3, -1.45), 4.6, 2.9, fill=False, ec=MUTED, lw=1))
    for cx, col, fc in [(-0.55, SERIES[0], SOFT[0]), (0.55, SERIES[1], SOFT[1])]:
        ax.add_patch(plt.Circle((cx, 0), 1.05, fc=fc, ec=col, lw=1.8, alpha=0.6))
    ax.text(-1.25, 0.95, a, fontsize=12, fontweight="bold", color=INK)
    ax.text(1.1, 0.95, b, fontsize=12, fontweight="bold", color=INK)
    for x, t in [(-1.0, only_a), (0, both), (1.0, only_b)]:
        ax.text(x, 0, t, ha="center", va="center", fontsize=10, color=INK)
    ax.text(2.15, -1.3, outside, ha="right", va="bottom", fontsize=9.5, color=INK2)
    ax.set_xlim(-2.4, 2.4); ax.set_ylim(-1.5, 1.5); ax.set_aspect("equal"); ax.axis("off")
    if title:
        ax.set_title(title)
    return _save(fig, out)


# ---------------------------------------------------------------- linear algebra / functions
def linear_map_2d(A, out: str, *, vectors: dict | None = None, eigen=True, title="", show_circle=True):
    """Left: unit circle & vectors; right: their images under A. Real eigen-directions drawn as dashed lines.
    `vectors` = {"v": (1, 2), ...} drawn in both panels."""
    _setup()
    A = np.asarray(A, float)
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.5))
    t = np.linspace(0, 2 * np.pi, 300)
    circ = np.vstack([np.cos(t), np.sin(t)])
    img = A @ circ
    vecs = vectors or {"e₁": (1, 0), "e₂": (0, 1)}
    pts = [circ, img] + [np.array(v, float).reshape(2, 1) for v in vecs.values()] + [A @ np.array(v, float).reshape(2, 1) for v in vecs.values()]
    lim = max(1.3, max(np.abs(p).max() for p in pts) * 1.15)
    eig = []
    if eigen:
        w, V = np.linalg.eig(A)
        eig = [(w[i].real, V[:, i].real) for i in range(2) if abs(w[i].imag) < 1e-12]
    for k, (ax, M, name) in enumerate([(axs[0], np.eye(2), "變換前"), (axs[1], A, "變換後  A·x")]):
        ax.axhline(0, color=MUTED, lw=0.8); ax.axvline(0, color=MUTED, lw=0.8)
        if show_circle:
            c = M @ circ
            ax.plot(c[0], c[1], color=MUTED, lw=1.2)
        for lam, v in eig:
            d = v / np.linalg.norm(v) * lim
            ax.plot([-d[0], d[0]], [-d[1], d[1]], color=SERIES[2], lw=1.3, ls="--")
            if k == 1:
                ax.text(-d[0] * 0.8, -d[1] * 0.8, f"λ = {lam:g}", color=INK, fontsize=8.5, ha="center", va="center",
                        bbox=dict(fc="white", ec="none", pad=1))
        for i, (lab, v) in enumerate(vecs.items()):
            v2 = M @ np.array(v, float)
            col = SERIES[i % 2]
            ax.annotate("", xy=v2, xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=col, lw=2, mutation_scale=12))
            ax.text(v2[0], v2[1], f" {lab}" if k == 0 else f" A{lab}", color=INK, fontsize=9.5, va="bottom")
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect("equal")
        ax.set_title(name, fontsize=10)
        ax.tick_params(labelsize=8)
    if title:
        fig.suptitle(title, fontweight="bold", fontsize=11, color=INK)
    return _save(fig, out)


def function_plot(funcs: Sequence[tuple], x_range: tuple, out: str, *, title="", xlabel="x", ylabel="y",
                  points: dict | None = None):
    """Up to 3 functions [(f, "label"), ...] with directly labelled curves; `points` = {"label": (x, y)}."""
    assert len(funcs) <= 3
    x = np.linspace(*x_range, 500)
    fig, ax = _fig()
    for i, (f, lab) in enumerate(funcs):
        y = np.array([f(v) for v in x])
        ax.plot(x, y, color=SERIES[i], lw=2)
        _label_end(ax, x[-1], y[-1], lab, INK)
    for lab, (px, py) in (points or {}).items():
        ax.plot(px, py, "o", color=INK, ms=5)
        _label_end(ax, px, py, lab, INK, dy=6, va="bottom")
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    return _save(fig, out)
