#!/usr/bin/env python3
"""Build submission-oriented schematics and result figures for Paper 1."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATASET_DIR = PROJECT_DIR / "paper1_dataset"
OUT_DIR = PROJECT_DIR / "paper1_submission" / "manuscript_latex" / "figures"

BLUE = "#0F4D92"
BLUE_LIGHT = "#DCE8F5"
GREEN = "#2E7D4F"
GREEN_LIGHT = "#DDF0E3"
RED = "#B64342"
RED_LIGHT = "#F5DAD8"
GOLD = "#D6A21E"
GOLD_LIGHT = "#F7EDC8"
TEAL = "#32828B"
TEAL_LIGHT = "#DAEEEF"
VIOLET = "#75519B"
VIOLET_LIGHT = "#E9E1F1"
NEUTRAL = "#6A6A6A"
NEUTRAL_LIGHT = "#EDEDED"
DARK = "#222222"
VECTOR_RASTER_DPI = 1200
RASTER_EXPORT_DPI = 600


def setup_style():
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "font.size": 8,
            "axes.titlesize": 8,
            "axes.titleweight": "bold",
            "axes.labelsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.spines.right": False,
            "axes.spines.top": False,
            "axes.linewidth": 0.8,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def wilson_interval(successes, n, z=1.96):
    """Wilson score interval for a binomial proportion."""

    if n <= 0:
        return 0.0, 1.0
    proportion = successes / n
    denominator = 1.0 + z**2 / n
    center = (proportion + z**2 / (2 * n)) / denominator
    half_width = (
        z
        * np.sqrt(
            proportion * (1.0 - proportion) / n + z**2 / (4 * n**2)
        )
        / denominator
    )
    return max(0.0, center - half_width), min(1.0, center + half_width)


def mean_metric(rows, field):
    if not rows:
        raise ValueError(f"No rows available for {field}")
    return float(np.mean([float(row[field]) for row in rows]))


def save_figure(fig, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        OUT_DIR / f"{name}.svg",
        dpi=VECTOR_RASTER_DPI,
        bbox_inches="tight",
        pad_inches=0.04,
    )
    fig.savefig(
        OUT_DIR / f"{name}.pdf",
        dpi=VECTOR_RASTER_DPI,
        bbox_inches="tight",
        pad_inches=0.04,
    )
    fig.savefig(
        OUT_DIR / f"{name}.png",
        dpi=RASTER_EXPORT_DPI,
        bbox_inches="tight",
        pad_inches=0.04,
    )
    fig.savefig(
        OUT_DIR / f"{name}.tiff",
        dpi=RASTER_EXPORT_DPI,
        bbox_inches="tight",
        pad_inches=0.04,
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)


def panel_label(ax, label, x=0.012, y=0.985):
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8,
        fontweight="bold",
        color=DARK,
    )


def add_box(
    ax,
    x,
    y,
    width,
    height,
    title,
    detail="",
    face=BLUE_LIGHT,
    edge=BLUE,
    title_size=7.0,
    detail_size=6.1,
):
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.008,rounding_size=0.012",
        linewidth=1.0,
        edgecolor=edge,
        facecolor=face,
    )
    ax.add_patch(patch)
    ax.text(
        x + width / 2,
        y + height * (0.63 if detail else 0.5),
        title,
        ha="center",
        va="center",
        fontsize=title_size,
        fontweight="bold",
        color=DARK,
        linespacing=1.05,
    )
    if detail:
        ax.text(
            x + width / 2,
            y + height * 0.28,
            detail,
            ha="center",
            va="center",
            fontsize=detail_size,
            color=NEUTRAL,
            linespacing=1.05,
        )


def add_arrow(ax, start, end, color=NEUTRAL, style="-|>", rad=0.0):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle=style,
        mutation_scale=9,
        linewidth=0.9,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
    )
    ax.add_patch(arrow)


def add_decision(ax, x, y, width, height, text, face=GOLD_LIGHT, edge=GOLD):
    vertices = np.asarray(
        [
            [x, y + height / 2],
            [x + width / 2, y],
            [x, y - height / 2],
            [x - width / 2, y],
        ]
    )
    ax.add_patch(
        plt.Polygon(
            vertices,
            closed=True,
            facecolor=face,
            edgecolor=edge,
            linewidth=1.0,
        )
    )
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=6.3,
        color=DARK,
        linespacing=1.08,
    )


def add_flow_box(ax, x, y, width, height, text, fontsize=7.0):
    ax.add_patch(
        Rectangle(
            (x - width / 2, y - height / 2),
            width,
            height,
            facecolor="white",
            edgecolor=DARK,
            linewidth=1.1,
        )
    )
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=DARK,
        linespacing=1.08,
    )


def add_flow_diamond(ax, x, y, width, height, text, fontsize=6.7):
    vertices = np.asarray(
        [
            [x, y + height / 2],
            [x + width / 2, y],
            [x, y - height / 2],
            [x - width / 2, y],
        ]
    )
    ax.add_patch(
        plt.Polygon(
            vertices,
            closed=True,
            facecolor="white",
            edgecolor=DARK,
            linewidth=1.1,
        )
    )
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=DARK,
        linespacing=1.08,
    )


def add_orthogonal_arrow(ax, points, color=DARK, linewidth=1.0):
    points = [tuple(point) for point in points]
    if len(points) < 2:
        return
    for start, end in zip(points[:-2], points[1:-1]):
        ax.plot(
            [start[0], end[0]],
            [start[1], end[1]],
            color=color,
            linewidth=linewidth,
            solid_capstyle="butt",
        )
    add_arrow(ax, points[-2], points[-1], color=color)


def make_figure1():
    fig, ax = plt.subplots(figsize=(7.2, 9.4))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.09, 1.02)
    ax.axis("off")
    main_x = 0.48
    main_w = 0.40
    reject_x = 0.87
    reject_y = 0.20

    image_path = (
        SCRIPT_DIR
        / "results_visual_evidence"
        / "multimethod"
        / "portrait_original.png"
    )
    if image_path.exists():
        ax.imshow(
            load_rgb_image(image_path),
            extent=(0.445, 0.515, 0.935, 0.995),
            aspect="auto",
            interpolation="nearest",
        )
        ax.add_patch(
            Rectangle(
                (0.445, 0.935),
                0.070,
                0.060,
                fill=False,
                edgecolor=DARK,
                linewidth=1.0,
            )
        )
        ax.text(
            0.48,
            0.925,
            "Input image",
            ha="center",
            va="top",
            fontsize=6.2,
            color=DARK,
        )
        add_orthogonal_arrow(ax, [(0.48, 0.935), (0.48, 0.8975)])

    add_flow_box(ax, main_x, 0.875, main_w, 0.045, "Generation event")
    add_flow_box(
        ax,
        main_x,
        0.79,
        main_w,
        0.055,
        "Construct payload\n"
        "platform / generation / model /\ntime / content / CRC",
    )
    add_flow_box(
        ax,
        main_x,
        0.705,
        main_w,
        0.055,
        "Protect payload\nRS(32,16) + 4-repeat = 1024 bits",
    )
    add_flow_box(
        ax,
        main_x,
        0.62,
        main_w,
        0.055,
        "DWT-DCT embedding\nY channel, 8 x 8 DCT, alpha=28",
    )
    add_flow_diamond(
        ax,
        main_x,
        0.545,
        0.36,
        0.055,
        "All selected blocks\nprocessed?",
    )
    add_orthogonal_arrow(
        ax,
        [
            (main_x - 0.20, 0.545),
            (0.18, 0.545),
            (0.18, 0.62),
            (main_x - main_w / 2, 0.62),
        ],
    )
    ax.text(0.20, 0.555, "No: next block", fontsize=6, color=DARK)
    ax.text(main_x + 0.018, 0.505, "Yes", fontsize=6, color=DARK)

    add_flow_box(
        ax,
        main_x,
        0.465,
        main_w,
        0.055,
        "Release image and register\ngeneration record",
    )
    add_flow_box(
        ax,
        main_x,
        0.38,
        main_w,
        0.055,
        "Propagation\nedit / crop / recompress / capture",
    )
    add_flow_box(
        ax,
        main_x,
        0.310,
        main_w,
        0.060,
        "Recover payload\nblind extraction + majority vote + RS decode",
    )
    add_flow_diamond(
        ax,
        main_x,
        0.232,
        0.38,
        0.055,
        "CRC and RS valid?",
    )
    add_flow_diamond(
        ax,
        main_x,
        0.158,
        0.38,
        0.055,
        "Registered generation\nID matches?",
    )
    add_flow_diamond(
        ax,
        main_x,
        0.084,
        0.38,
        0.055,
        "Content binding\npasses?",
    )
    add_flow_diamond(
        ax,
        main_x,
        0.010,
        0.38,
        0.055,
        "Trust score\nnot low?",
    )

    add_flow_box(
        ax,
        reject_x,
        reject_y,
        0.20,
        0.09,
        "REJECT attribution\nkeep diagnostics",
        fontsize=6.8,
    )
    for source_y in (0.232, 0.158, 0.084, 0.010):
        add_orthogonal_arrow(
            ax,
            [
                (main_x + 0.20, source_y),
                (0.74, source_y),
                (0.74, reject_y),
                (reject_x - 0.10, reject_y),
            ],
            color=RED,
        )
        ax.text(0.705, source_y + 0.008, "No", fontsize=6.0, color=RED)

    add_flow_box(
        ax,
        main_x,
        -0.065,
        main_w,
        0.045,
        "ACCEPT attribution\nhigh / medium diagnostic trust",
        fontsize=6.8,
    )
    for start_y, end_y in (
        (0.8525, 0.8175),
        (0.7625, 0.7325),
        (0.6775, 0.6475),
        (0.5925, 0.5725),
        (0.5175, 0.4925),
        (0.4375, 0.4075),
        (0.3525, 0.3375),
        (0.2825, 0.2595),
        (0.2045, 0.1855),
        (0.1305, 0.1115),
        (0.0565, 0.0375),
        (-0.0175, -0.0425),
    ):
        add_orthogonal_arrow(ax, [(main_x, start_y), (main_x, end_y)])

    ax.text(0.03, 0.90, "Generation", fontsize=7.5, fontweight="bold", color=DARK)
    ax.text(0.03, 0.43, "Verification", fontsize=7.5, fontweight="bold", color=DARK)
    save_figure(fig, "fig1_framework")


def make_figure2():
    fig = plt.figure(figsize=(7.0, 3.0))
    grid = fig.add_gridspec(3, 1, height_ratios=[1.0, 0.8, 0.8], hspace=0.65)
    ax0 = fig.add_subplot(grid[0])
    fields = [
        ("Ver.", 4, "#DCE8F5"),
        ("Platform", 8, "#DDF0E3"),
        ("Generation", 48, "#F7EDC8"),
        ("Model", 8, "#E9E1F1"),
        ("Time", 24, "#DAEEEF"),
        ("Content", 16, "#F5DAD8"),
        ("Rsv.", 4, "#EDEDED"),
        ("CRC", 16, "#D9D9D9"),
    ]
    left = 0
    for label, bits, color in fields:
        ax0.barh(0, bits, left=left, height=0.55, color=color, edgecolor="white")
        center = left + bits / 2
        rotation = 0 if bits >= 8 else 90
        ax0.text(
            center,
            0.38,
            label,
            ha="center",
            va="bottom",
            fontsize=6.2,
            rotation=rotation,
            rotation_mode="anchor",
        )
        ax0.text(center, -0.38, str(bits), ha="center", va="top", fontsize=6.0)
        left += bits
    ax0.set_xlim(0, 128)
    ax0.set_ylim(-0.8, 0.9)
    ax0.set_yticks([])
    ax0.set_xticks([0, 32, 64, 96, 128])
    ax0.set_xlabel("Payload bit position")
    ax0.set_title("128-bit structured payload")
    panel_label(ax0, "a")

    ax1 = fig.add_subplot(grid[1])
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis("off")
    add_box(ax1, 0.03, 0.22, 0.22, 0.58, "16 bytes", "message", *[(GOLD_LIGHT, GOLD)][0])
    add_arrow(ax1, (0.25, 0.51), (0.36, 0.51), GOLD)
    add_box(ax1, 0.36, 0.22, 0.22, 0.58, "CRC-16", "integrity check", *[(GREEN_LIGHT, GREEN)][0])
    add_arrow(ax1, (0.58, 0.51), (0.69, 0.51), GOLD)
    add_box(ax1, 0.69, 0.22, 0.28, 0.58, "RS(32,16)", "256 coded bits", *[(BLUE_LIGHT, BLUE)][0])
    ax1.text(0.5, 0.04, "Error correction", ha="center", fontsize=6.2, color=NEUTRAL)
    panel_label(ax1, "b")

    ax2 = fig.add_subplot(grid[2])
    ax2.set_xlim(0, 1024)
    ax2.set_ylim(0, 1)
    ax2.set_yticks([])
    ax2.set_xlabel("Coded watermark length (bits)")
    for repeat in range(4):
        ax2.add_patch(
            Rectangle(
                (repeat * 256, 0.25),
                256,
                0.45,
                facecolor=[BLUE_LIGHT, TEAL_LIGHT, GOLD_LIGHT, GREEN_LIGHT][repeat],
                edgecolor="white",
                linewidth=1,
            )
        )
        ax2.text(repeat * 256 + 128, 0.475, f"copy {repeat + 1}", ha="center", va="center", fontsize=6.2)
    ax2.set_title("Fourfold repetition produces exactly 1024 coded bits")
    panel_label(ax2, "c")
    save_figure(fig, "fig2_payload_ecc")


def make_figure3():
    fig = plt.figure(figsize=(7.2, 4.35))
    outer = fig.add_gridspec(2, 1, height_ratios=[0.95, 1.25], hspace=0.35)
    ax = fig.add_subplot(outer[0])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    add_box(ax, 0.02, 0.30, 0.20, 0.52, "RGB image", "512 x 512", BLUE_LIGHT, BLUE)
    add_arrow(ax, (0.22, 0.56), (0.30, 0.56), BLUE)
    add_box(ax, 0.30, 0.30, 0.20, 0.52, "Luminance", "Y channel", TEAL_LIGHT, TEAL)
    add_arrow(ax, (0.50, 0.56), (0.58, 0.56), BLUE)
    add_box(
        ax,
        0.58,
        0.30,
        0.16,
        0.52,
        "1-level Haar\nDWT",
        "LL band",
        VIOLET_LIGHT,
        VIOLET,
    )
    add_arrow(ax, (0.74, 0.56), (0.82, 0.56), BLUE)
    add_box(
        ax,
        0.82,
        0.30,
        0.16,
        0.52,
        "8 x 8 DCT",
        "keyed block order",
        NEUTRAL_LIGHT,
        NEUTRAL,
    )
    panel_label(ax, "a", x=0.0, y=0.96)

    lower = outer[1].subgridspec(1, 2, width_ratios=[1.05, 1.2], wspace=0.35)
    ax_grid = fig.add_subplot(lower[0])
    coefficient_map = np.zeros((8, 8), dtype=int)
    coefficient_map[3, 2] = 1
    coefficient_map[2, 3] = 2
    from matplotlib.colors import ListedColormap

    ax_grid.imshow(
        coefficient_map,
        cmap=ListedColormap([NEUTRAL_LIGHT, BLUE_LIGHT, GOLD_LIGHT]),
        vmin=0,
        vmax=2,
        origin="upper",
    )
    ax_grid.set_xticks(np.arange(8))
    ax_grid.set_yticks(np.arange(8))
    ax_grid.set_xticklabels(["0", "1", "2", "3", "4", "5", "6", "7"])
    ax_grid.set_yticklabels(["0", "1", "2", "3", "4", "5", "6", "7"])
    ax_grid.set_xlabel("DCT horizontal index u")
    ax_grid.set_ylabel("DCT vertical index v")
    ax_grid.set_title("Selected coefficient pair", loc="left", pad=5)
    for row in range(9):
        ax_grid.axhline(row - 0.5, color="white", linewidth=0.7)
        ax_grid.axvline(row - 0.5, color="white", linewidth=0.7)
    ax_grid.add_patch(
        Rectangle((1.5, 2.5), 1, 1, fill=False, edgecolor=BLUE, linewidth=2.0)
    )
    ax_grid.add_patch(
        Rectangle((2.5, 1.5), 1, 1, fill=False, edgecolor=GOLD, linewidth=2.0)
    )
    ax_grid.text(2, 3, "C(3,2)", ha="center", va="center", fontsize=6.2, fontweight="bold")
    ax_grid.text(3, 2, "C(2,3)", ha="center", va="center", fontsize=6.2, fontweight="bold")
    panel_label(ax_grid, "b", x=-0.15, y=1.05)

    ax_flow = fig.add_subplot(lower[1])
    ax_flow.set_xlim(0, 1)
    ax_flow.set_ylim(0, 1)
    ax_flow.axis("off")
    add_box(
        ax_flow,
        0.02,
        0.58,
        0.28,
        0.25,
        "Differential\nupdate",
        "b=1: d=+alpha\nb=0: d=-alpha",
        GOLD_LIGHT,
        GOLD,
    )
    add_box(
        ax_flow,
        0.36,
        0.58,
        0.28,
        0.25,
        "Inverse\nDWT-DCT",
        "reconstruct image",
        TEAL_LIGHT,
        TEAL,
    )
    add_box(
        ax_flow,
        0.70,
        0.58,
        0.28,
        0.25,
        "Blind\nextraction",
        "sign(C3,2-C2,3)",
        GREEN_LIGHT,
        GREEN,
    )
    add_arrow(ax_flow, (0.30, 0.705), (0.36, 0.705), GOLD)
    add_arrow(ax_flow, (0.64, 0.705), (0.70, 0.705), TEAL)
    ax_flow.text(
        0.5,
        0.31,
        "C'(3,2) = C(3,2) + delta\n"
        "C'(2,3) = C(2,3) - delta",
        ha="center",
        va="center",
        fontsize=7,
        color=DARK,
    )
    ax_flow.text(
        0.5,
        0.10,
        "alpha = 28; block permutation seed = 20260910",
        ha="center",
        va="center",
        fontsize=6.5,
        color=NEUTRAL,
    )
    panel_label(ax_flow, "c", x=-0.04, y=1.05)
    save_figure(fig, "fig3_dwt_dct")


def make_figure4():
    fig = plt.figure(figsize=(7.2, 4.5))
    outer = fig.add_gridspec(
        3,
        2,
        height_ratios=[0.8, 0.95, 1.05],
        hspace=0.45,
        wspace=0.42,
    )
    ax = fig.add_subplot(outer[0, :])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    add_box(ax, 0.01, 0.24, 0.19, 0.52, "Recovered\npayload", "CRC and RS checks", BLUE_LIGHT, BLUE)
    add_arrow(ax, (0.20, 0.50), (0.28, 0.50), BLUE)
    add_box(ax, 0.28, 0.24, 0.20, 0.52, "Registry\ncandidate", "200 generation records", TEAL_LIGHT, TEAL)
    add_arrow(ax, (0.48, 0.50), (0.56, 0.50), BLUE)
    add_box(ax, 0.56, 0.24, 0.19, 0.52, "Content gate", "hard accept/reject", GOLD_LIGHT, GOLD)
    add_arrow(ax, (0.75, 0.50), (0.82, 0.50), BLUE)
    add_box(ax, 0.82, 0.24, 0.17, 0.52, "Joint score", "graded trust", GREEN_LIGHT, GREEN)
    panel_label(ax, "a", x=0.0, y=0.94)

    gate = fig.add_subplot(outer[1, :])
    gate.set_xlim(0, 1)
    gate.set_ylim(0, 1)
    gate.axis("off")
    add_box(
        gate,
        0.01,
        0.36,
        0.20,
        0.38,
        "Image content",
        "ORB keypoints?",
        NEUTRAL_LIGHT,
        NEUTRAL,
    )
    add_arrow(gate, (0.21, 0.55), (0.32, 0.70), TEAL)
    add_arrow(gate, (0.21, 0.48), (0.32, 0.28), GOLD)
    add_box(
        gate,
        0.32,
        0.60,
        0.30,
        0.30,
        "ORB path",
        "keypoints >= 10: score >= 0.30",
        BLUE_LIGHT,
        BLUE,
    )
    add_box(
        gate,
        0.32,
        0.08,
        0.30,
        0.30,
        "Flat fallback",
        "score >= 0.90",
        GOLD_LIGHT,
        GOLD,
    )
    add_arrow(gate, (0.62, 0.75), (0.75, 0.58), BLUE)
    add_arrow(gate, (0.62, 0.23), (0.75, 0.43), GOLD)
    add_box(
        gate,
        0.75,
        0.36,
        0.23,
        0.38,
        "Content gate",
        "pass / fail",
        GREEN_LIGHT,
        GREEN,
    )
    panel_label(gate, "b", x=0.0, y=0.95)

    components = [
        ("CRC", 0.25, "#DCE8F5"),
        ("RS", 0.20, "#DAEEEF"),
        ("Fields", 0.30, "#E9E1F1"),
        ("Hash", 0.15, "#F7EDC8"),
        ("ID match", 0.10, "#DDF0E3"),
    ]
    ax2 = fig.add_subplot(outer[2, 0])
    left = 0
    for label, weight, color in components:
        ax2.barh(0, weight, left=left, height=0.55, color=color, edgecolor="white")
        ax2.text(left + weight / 2, 0, f"{label}\n{weight:.2f}", ha="center", va="center", fontsize=5.9)
        left += weight
    ax2.set_xlim(0, 1)
    ax2.set_ylim(-0.55, 0.55)
    ax2.set_yticks([])
    ax2.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax2.set_xlabel("Joint-score weight")
    panel_label(ax2, "c", x=-0.10, y=1.08)

    ax3 = fig.add_subplot(outer[2, 1])
    levels = ["Low", "Medium", "High"]
    colors = [RED_LIGHT, GOLD_LIGHT, GREEN_LIGHT]
    bounds = [0, 0.32, 0.55, 1.0]
    for index, label in enumerate(levels):
        ax3.barh(0, bounds[index + 1] - bounds[index], left=bounds[index], color=colors[index], edgecolor="white")
        ax3.text(
            (bounds[index] + bounds[index + 1]) / 2,
            0,
            label,
            ha="center",
            va="center",
            fontsize=6.2,
        )
    ax3.set_xlim(0, 1)
    ax3.set_ylim(-0.55, 0.55)
    ax3.set_yticks([])
    ax3.set_xticks([0, 0.32, 0.55, 1.0])
    ax3.set_xlabel("Trust score")
    panel_label(ax3, "d", x=-0.16, y=1.08)
    ax.text(
        0.5,
        0.98,
        "Joint verification requires payload validity, registry consistency, and image-content consistency",
        ha="center",
        va="top",
        fontsize=7.4,
        fontweight="bold",
        color=DARK,
    )
    save_figure(fig, "fig4_verification")


def make_figure5():
    quality_rows = read_csv(
        SCRIPT_DIR / "results_full_capture_scan" / "quality_metrics.csv"
    )
    quality = sorted(quality_rows, key=lambda row: float(row["psnr"]))
    row = quality[len(quality) // 2]
    metadata = {
        item["generation_id"]: item
        for item in read_csv(DATASET_DIR / "metadata_all.csv")
    }[row["generation_id"]]
    original_path = DATASET_DIR / metadata["relative_path"]
    watermarked_path = Path(row["watermarked_path"])
    if not watermarked_path.is_absolute():
        watermarked_path = PROJECT_DIR / watermarked_path

    with Image.open(original_path) as image:
        original = np.asarray(image.convert("RGB"))
    with Image.open(watermarked_path) as image:
        watermarked = np.asarray(image.convert("RGB"))
    residual = np.abs(
        original.astype(np.int16) - watermarked.astype(np.int16)
    ).astype(np.uint8)
    residual_x10 = np.clip(residual.astype(np.uint16) * 10, 0, 255).astype(np.uint8)

    fig = plt.figure(figsize=(7.2, 4.35))
    grid = fig.add_gridspec(2, 4, height_ratios=[2.1, 1.25], hspace=0.35)
    axes = [fig.add_subplot(grid[0, index]) for index in range(4)]
    panels = [
        (original, "Original", None),
        (
            watermarked,
            f"Watermarked\nPSNR {float(row['psnr']):.2f} dB, SSIM {float(row['ssim']):.4f}",
            None,
        ),
        (residual, "Absolute residual", "gray"),
        (residual_x10, "Residual x10", "gray"),
    ]
    for index, (ax, (image, title, cmap)) in enumerate(zip(axes, panels)):
        if cmap:
            ax.imshow(image, cmap=cmap, interpolation="nearest", vmin=0, vmax=255)
        else:
            ax.imshow(image, interpolation="nearest")
        ax.set_title(title, fontsize=7, pad=4)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.text(
            0.0,
            1.01,
            "abcd"[index],
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=8,
            fontweight="bold",
            color=DARK,
        )
        if index in (0, 1):
            center_y = image.shape[0] // 2
            center_x = image.shape[1] // 2
            half = 48
            x0 = center_x - half
            y0 = center_y - half
            ax.add_patch(
                Rectangle(
                    (x0, y0),
                    2 * half,
                    2 * half,
                    fill=False,
                    edgecolor=GOLD,
                    linewidth=1.2,
                )
            )
            inset = ax.inset_axes([0.68, 0.02, 0.30, 0.30])
            inset.imshow(
                image[y0 : y0 + 2 * half, x0 : x0 + 2 * half],
                interpolation="nearest",
            )
            inset.set_xticks([])
            inset.set_yticks([])
            for spine in inset.spines.values():
                spine.set_edgecolor(GOLD)
                spine.set_linewidth(1.1)

    hist_psnr = fig.add_subplot(grid[1, :2])
    hist_ssim = fig.add_subplot(grid[1, 2:])
    psnr_values = np.asarray(
        [float(item["psnr"]) for item in quality_rows], dtype=float
    )
    ssim_values = np.asarray(
        [float(item["ssim"]) for item in quality_rows], dtype=float
    )
    hist_psnr.hist(psnr_values, bins=20, color=BLUE, alpha=0.82, edgecolor="white")
    hist_psnr.axvline(psnr_values.mean(), color=RED, linestyle="--", linewidth=1.1, label="Mean")
    hist_psnr.set_xlabel("PSNR (dB)")
    hist_psnr.set_ylabel("Images")
    hist_psnr.set_title("e  PSNR distribution (n=200)", loc="left", pad=5)
    hist_psnr.legend(loc="upper left")

    hist_ssim.hist(ssim_values, bins=20, color=TEAL, alpha=0.82, edgecolor="white")
    hist_ssim.axvline(ssim_values.mean(), color=RED, linestyle="--", linewidth=1.1, label="Mean")
    hist_ssim.set_xlabel("SSIM")
    hist_ssim.set_ylabel("Images")
    hist_ssim.set_title("f  SSIM distribution (n=200)", loc="left", pad=5)
    hist_ssim.legend(loc="upper left")

    fig.suptitle(
        "Watermark visibility and full-sample quality",
        fontsize=8.8,
        fontweight="bold",
    )
    save_figure(fig, "fig5_watermark_example")


def make_figure6():
    single = read_json(
        SCRIPT_DIR / "results_full_capture_scan" / "summary.json"
    )["robustness"]
    combined = read_json(
        SCRIPT_DIR / "results_combined_alpha28" / "summary.json"
    )

    single_specs = [
        ("Clean", "clean:{}"),
        ("JPEG90", "jpeg:{'quality': 90}"),
        ("JPEG70", "jpeg:{'quality': 70}"),
        ("JPEG50", "jpeg:{'quality': 50}"),
        ("Resize0.75", "resize:{'scale': 0.75}"),
        ("Resize1.5", "resize:{'scale': 1.5}"),
        ("Crop0.9", "crop:{'ratio': 0.9}"),
        ("Noise3", "gaussian_noise:{'sigma': 3}"),
        ("Noise8", "gaussian_noise:{'sigma': 8}"),
        ("S&P", "salt_pepper:{'amount': 0.002}"),
        ("B/C", "brightness_contrast:{}"),
        ("Blur", "blur:{'ksize': 3}"),
        ("Screenshot", "screenshot:{}"),
        ("Screen sim.", "real_screen_capture:{}"),
        ("Print-scan", "print_scan:{}"),
    ]
    combined_specs = [
        ("Crop+JPEG", "crop_jpeg"),
        ("Resize+JPEG", "resize_jpeg"),
        ("Shot+noise", "screenshot_noise"),
        ("Blur+JPEG", "blur_jpeg"),
        ("Crop+Resize+JPEG", "crop_resize_jpeg"),
        ("Social", "social_recompress"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.7), constrained_layout=True)
    for ax, values_key in ((axes[0, 0], "success_rate"), (axes[0, 1], "mean_ber")):
        labels = [label for label, _ in single_specs]
        values = [single[key][values_key] for _, key in single_specs]
        counts = [single[key]["count"] for _, key in single_specs]
        colors = [
            RED if value == 0 else (GOLD if value < 0.98 else BLUE)
            for value in values
        ]
        y = np.arange(len(labels))
        ax.barh(y, values, color=colors, edgecolor="white", height=0.72)
        ax.set_yticks(y, labels)
        ax.invert_yaxis()
        ax.set_xlim(0, 1 if values_key == "success_rate" else 0.6)
        ax.set_xlabel("Success rate" if values_key == "success_rate" else "Mean BER")
        ax.set_title(
            ("a" if values_key == "success_rate" else "b")
            + "  Single transformations",
            loc="left",
            pad=5,
        )
        intervals = []
        for value, count in zip(values, counts):
            intervals.append(wilson_interval(round(value * count), count))
        for yi, value, (_, high) in zip(y, values, intervals):
            ax.text(
                (high + 0.015 if values_key == "success_rate" else value + 0.008),
                yi,
                f"{value:.3f}",
                va="center",
                fontsize=5.6,
            )
        if values_key == "success_rate":
            lower = []
            upper = []
            for value, (low, high) in zip(values, intervals):
                lower.append(value - low)
                upper.append(high - value)
            ax.errorbar(
                values,
                y,
                xerr=[lower, upper],
                fmt="none",
                ecolor=DARK,
                elinewidth=0.7,
                capsize=1.8,
            )
    labels = [label for label, _ in combined_specs]
    successes = [combined[key]["success_rate"] for _, key in combined_specs]
    ax = axes[1, 0]
    y = np.arange(len(labels))
    ax.barh(y, successes, color=BLUE, height=0.65)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("Success rate")
    ax.set_title("c  Compound transformations", loc="left", pad=5)
    success_intervals = [
        wilson_interval(round(value * 200), 200) for value in successes
    ]
    for yi, value, (_, high) in zip(y, successes, success_intervals):
        ax.text(high + 0.014, yi, f"{value:.3f}", va="center", fontsize=6)
    lower = []
    upper = []
    for value, (low, high) in zip(successes, success_intervals):
        lower.append(value - low)
        upper.append(high - value)
    ax.errorbar(
        successes,
        y,
        xerr=[lower, upper],
        fmt="none",
        ecolor=DARK,
        elinewidth=0.7,
        capsize=1.8,
    )
    trust_keys = [
        ("Crop0.9", "crop:{'ratio': 0.9}"),
        ("Blur", "blur:{'ksize': 3}"),
        ("Crop+Resize+JPEG", "crop_resize_jpeg"),
    ]
    ax = axes[1, 1]
    levels = ["high", "medium", "low"]
    trust_colors = [GREEN, GOLD, RED]
    bottoms = np.zeros(len(trust_keys))
    for level, color in zip(levels, trust_colors):
        values = []
        for _, key in trust_keys:
            source = combined[key] if key in combined else single[key]
            values.append(source["trust_counts"].get(level, 0))
        values = np.asarray(values)
        ax.barh(np.arange(len(trust_keys)), values, left=bottoms, color=color, label=level.capitalize())
        bottoms += values
    ax.set_yticks(np.arange(len(trust_keys)), [label for label, _ in trust_keys])
    ax.invert_yaxis()
    ax.set_xlim(0, 200)
    ax.set_xlabel("Positive images")
    ax.set_title("d  Trust composition", loc="left", pad=5)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.24),
        ncol=3,
    )
    fig.suptitle(
        r"Verification after image transformations ($\alpha$=28; n=200 each)",
        fontsize=9,
        fontweight="bold",
    )
    save_figure(fig, "fig6_robustness")


def make_figure7():
    full_summary = (
        SCRIPT_DIR / "results_ablation_full_alpha28" / "ablation_summary.csv"
    )
    rows = read_csv(
        full_summary
        if full_summary.exists()
        else SCRIPT_DIR / "results_ablation" / "ablation_summary.csv"
    )
    sample_size = 200 if full_summary.exists() else 10
    by_group = {
        group: [row for row in rows if row["group"] == group]
        for group in ("carrier", "coding", "alpha")
    }
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.25), constrained_layout=True)

    for ax, group, title in (
        (axes[0, 0], "carrier", "Carrier"),
        (axes[0, 1], "coding", "Coding"),
    ):
        data = by_group[group]
        labels = [row["config"].replace("_", "-") for row in data]
        x = np.arange(len(labels))
        width = 0.22
        for index, (field, label) in enumerate(
            (("jpeg50_success", "JPEG50"), ("crop_success", "Crop"), ("blur_success", "Blur"))
        ):
            values = 100 * np.asarray([float(row[field]) for row in data])
            ax.bar(
                x + (index - 1) * width,
                values,
                width,
                label=label,
            )
            lower = []
            upper = []
            for value in values:
                low, high = wilson_interval(
                    round(value * sample_size / 100),
                    sample_size,
                )
                lower.append(100 * (value / 100 - low))
                upper.append(100 * (high - value / 100))
            ax.errorbar(
                x + (index - 1) * width,
                values,
                yerr=[lower, upper],
                fmt="none",
                ecolor=DARK,
                elinewidth=0.6,
                capsize=1.2,
            )
        ax.set_xticks(x, labels, rotation=30, ha="right", rotation_mode="anchor")
        ax.set_ylim(0, 105)
        ax.set_ylabel("Success (%)")
        ax.set_title(("a" if group == "carrier" else "b") + f"  {title}", loc="left", pad=5)
    handles, legend_labels = axes[0, 0].get_legend_handles_labels()

    alpha_data = sorted(by_group["alpha"], key=lambda row: float(row["config"].split("_")[1]))
    alpha_values = [int(row["config"].split("_")[1]) for row in alpha_data]
    psnr = [float(row["mean_psnr"]) for row in alpha_data]
    crop_success = [100 * float(row["crop_success"]) for row in alpha_data]
    axes[1, 0].plot(alpha_values, psnr, marker="o", color=BLUE, linewidth=1.5)
    axes[1, 0].set_xlabel(r"Embedding strength $\alpha$")
    axes[1, 0].set_ylabel("Mean PSNR (dB)", color=BLUE)
    axes[1, 0].set_xticks(alpha_values)
    axes[1, 0].set_title("c  Quality-robustness tradeoff", loc="left", pad=5)
    for x_value, y_value in zip(alpha_values, psnr):
        axes[1, 0].annotate(
            f"{y_value:.1f}",
            (x_value, y_value),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            fontsize=5.2,
        )
    axes[1, 0].set_ylim(min(psnr) - 0.8, max(psnr) + 0.7)
    ax_crop = axes[1, 0].twinx()
    ax_crop.plot(
        alpha_values,
        crop_success,
        marker="s",
        color=GOLD,
        linewidth=1.3,
        linestyle="--",
    )
    alpha_lower = []
    alpha_upper = []
    for value in crop_success:
        low, high = wilson_interval(round(value * sample_size / 100), sample_size)
        alpha_lower.append(100 * (value / 100 - low))
        alpha_upper.append(100 * (high - value / 100))
    ax_crop.errorbar(
        alpha_values,
        crop_success,
        yerr=[alpha_lower, alpha_upper],
        fmt="none",
        ecolor=GOLD,
        elinewidth=0.7,
        capsize=1.8,
    )
    ax_crop.set_ylabel("Crop (%)", color=GOLD)
    ax_crop.set_ylim(0, 105)
    ax_crop.spines["top"].set_visible(False)

    dct_combined_path = (
        SCRIPT_DIR / "results_combined_dct_only_alpha28" / "summary.json"
    )
    dwt_combined_path = (
        SCRIPT_DIR / "results_combined_alpha28" / "summary.json"
    )
    if dct_combined_path.exists() and dwt_combined_path.exists():
        dct_combined = read_json(dct_combined_path)
        dwt_combined = read_json(dwt_combined_path)
        attack_keys = [
            ("crop_jpeg", "Crop+JPEG"),
            ("blur_jpeg", "Blur+JPEG"),
            ("crop_resize_jpeg", "Crop+Resize+JPEG"),
        ]
        x = np.arange(len(attack_keys))
        width = 0.34
        dct_values = [100 * dct_combined[key]["success_rate"] for key, _ in attack_keys]
        dwt_values = [100 * dwt_combined[key]["success_rate"] for key, _ in attack_keys]
        axes[1, 1].bar(
            x - width / 2,
            dct_values,
            width,
            color=GOLD,
            label="DCT-only",
        )
        axes[1, 1].bar(
            x + width / 2,
            dwt_values,
            width,
            color=BLUE,
            label="DWT-DCT",
        )
        axes[1, 1].set_xticks(
            x,
            [label for _, label in attack_keys],
            rotation=18,
            ha="right",
            rotation_mode="anchor",
        )
        axes[1, 1].set_ylim(0, 105)
        axes[1, 1].set_ylabel("Success (%)")
        axes[1, 1].set_title("d  Combined-attack carrier check", loc="left", pad=5)
        axes[1, 1].legend(loc="lower right")
        for positions, values in (
            (x - width / 2, dct_values),
            (x + width / 2, dwt_values),
        ):
            for x_value, value in zip(positions, values):
                axes[1, 1].text(
                    x_value,
                    value + 1.2,
                    f"{value:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=5.6,
                )
    ablation_title = (
        "Full-scale ablations (n=200; carrier/coding at alpha=28)"
        if full_summary.exists()
        else "Ablation results (n=10; carrier/coding at alpha=24)"
    )
    fig.suptitle(ablation_title, fontsize=8.5, fontweight="bold")
    fig.legend(
        handles,
        legend_labels,
        loc="lower center",
        ncol=3,
        bbox_to_anchor=(0.5, -0.14),
    )
    save_figure(fig, "fig7_ablation")


def make_figure8():
    calibration = read_json(
        SCRIPT_DIR
        / "results_threshold_calibration_split_alpha28"
        / "summary.json"
    )
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0), constrained_layout=True)
    ax = axes[0]
    for key, label, color in (
        ("calibration", "Calibration", BLUE),
        ("held_out", "Held-out", GREEN),
    ):
        roc = calibration[key]["roc"]
        fpr = [item["fpr"] for item in roc]
        tpr = [item["tpr"] for item in roc]
        lower, upper = calibration[key]["auc_cluster_bootstrap_95ci"]
        ax.plot(
            fpr,
            tpr,
            color=color,
            linewidth=1.5,
            label=(
                f"{label}: AUC={calibration[key]['auc']:.6f} "
                f"[{lower:.6f}, {upper:.6f}]"
            ),
        )
    ax.plot([0, 1], [0, 1], linestyle="--", color=NEUTRAL_LIGHT, linewidth=0.8)
    ax.set_xlim(-0.01, 0.10)
    ax.set_ylim(0.90, 1.005)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("Low-FPR ROC")
    ax.legend(loc="lower right", fontsize=8)
    panel_label(ax, "a")

    negative = read_csv(
        SCRIPT_DIR
        / "results_threshold_calibration_alpha28"
        / "negative_scores.csv"
    )
    assignments = {
        row["generation_id"]: row["split"]
        for row in read_csv(
            SCRIPT_DIR
            / "results_threshold_calibration_split_alpha28"
            / "split_assignments.csv"
        )
    }
    heldout_negative = [
        float(row["score"])
        for row in negative
        if assignments.get(row["generation_id"]) == "held_out"
    ]
    positive_rows = []
    for path in (
        SCRIPT_DIR / "results_full_capture_scan" / "robustness_detail.csv",
        SCRIPT_DIR / "results_combined_alpha28" / "combined_detail.csv",
    ):
        positive_rows.extend(read_csv(path))
    heldout_positive = [
        float(row["score"])
        for row in positive_rows
        if assignments.get(row["generation_id"]) == "held_out"
    ]
    bins = np.linspace(0, 1, 41)
    ax = axes[1]
    ax.hist(heldout_positive, bins=bins, alpha=0.75, color=GREEN, label="Positive")
    ax.hist(heldout_negative, bins=bins, alpha=0.75, color=RED, label="Negative")
    ax.axvline(0.32, color=GOLD, linestyle="--", linewidth=1.2, label="Medium = 0.32")
    ax.axvline(0.55, color=BLUE, linestyle="--", linewidth=1.2, label="High = 0.55")
    ax.set_yscale("log", nonpositive="clip")
    ax.set_xlim(0, 1.02)
    ax.set_xlabel("Trust score")
    ax.set_ylabel("Observations (log scale)")
    ax.set_title("Held-out score distribution")
    ax.legend(loc="upper center", fontsize=8)
    panel_label(ax, "b")
    save_figure(fig, "fig8_calibration")


def make_figure9():
    rows = read_csv(
        SCRIPT_DIR / "results_external_baselines" / "matched_comparison.csv"
    )
    labels = ["Ours", "DWT-DCT", "DWT-DCT-SVD", "RivaGAN (32 bit)"]
    metrics = [
        ("jpeg", {"quality": 50}, "JPEG50", "jpeg50"),
        ("crop", {"ratio": 0.9}, "Crop", "crop"),
        ("blur", {"ksize": 3}, "Blur", "blur"),
        ("screenshot", {}, "Screenshot", "screenshot"),
        (
            "crop_resize_jpeg",
            {"crop_ratio": 0.9, "scale": 0.8, "jpeg_quality": 70},
            "Crop+Resize+JPEG",
            "crop_resize_jpeg",
        ),
    ]
    colors = [BLUE, RED, GOLD, TEAL]

    external_rows = read_csv(
        SCRIPT_DIR / "results_external_baselines" / "external_detail.csv"
    )
    matched_ids = {
        row["generation_id"]
        for row in external_rows
        if row["method"] == "rivaGan"
    }
    ours_single = [
        row
        for row in read_csv(
            SCRIPT_DIR / "results_full_capture_scan" / "robustness_detail.csv"
        )
        if row["generation_id"] in matched_ids
    ]
    ours_combined = [
        row
        for row in read_csv(
            SCRIPT_DIR / "results_combined_alpha28" / "combined_detail.csv"
        )
        if row["generation_id"] in matched_ids
    ]

    def choose_rows(source_rows, attack, params):
        return [
            row
            for row in source_rows
            if row["attack"] == attack
            and json.loads(row["params"] or "{}") == params
        ]

    ours_ber = []
    for attack, params, _, _ in metrics:
        source = ours_combined if attack == "crop_resize_jpeg" else ours_single
        selected = choose_rows(source, attack, params)
        ours_ber.append(
            {
                "attack": attack,
                "params": params,
                "rows": selected,
            }
        )

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.2, 3.35),
        constrained_layout=True,
    )
    x = np.arange(len(metrics))
    width = 0.18
    for method_index, (row, label, color) in enumerate(zip(rows, labels, colors)):
        values = [100 * float(row[result_key]) for _, _, _, result_key in metrics]
        count = int(row["count"])
        lower = []
        upper = []
        for value in values:
            low, high = wilson_interval(round(value * count / 100), count)
            lower.append(value - 100 * low)
            upper.append(100 * high - value)
        axes[0].bar(
            x + (method_index - 1.5) * width,
            values,
            width,
            color=color,
            label=label,
        )
        axes[0].errorbar(
            x + (method_index - 1.5) * width,
            values,
            yerr=[lower, upper],
            fmt="none",
            ecolor=DARK,
            elinewidth=0.6,
            capsize=1.5,
        )
    axes[0].set_xticks(
        x,
        [label for _, _, label, _ in metrics],
        rotation=18,
        ha="right",
        rotation_mode="anchor",
    )
    axes[0].set_ylim(0, 110)
    axes[0].set_ylabel("Success rate (%)")
    axes[0].set_title("a  Verification success", loc="left", pad=5)

    ber_values = {"Ours": [], "DWT-DCT": [], "DWT-DCT-SVD": [], "RivaGAN (32 bit)": []}
    for attack, params, _, _ in metrics:
        ours_selected = next(item for item in ours_ber if item["attack"] == attack)
        ber_values["Ours"].append(
            mean_metric(ours_selected["rows"], "ber")
        )
        for method in ("dwtDct", "dwtDctSvd", "rivaGan"):
            selected = [
                row
                for row in external_rows
                if row["method"] == method
                and row["attack"] == attack
                and json.loads(row["params"] or "{}") == params
            ]
            ber_values[
                "DWT-DCT"
                if method == "dwtDct"
                else "DWT-DCT-SVD"
                if method == "dwtDctSvd"
                else "RivaGAN (32 bit)"
            ].append(mean_metric(selected, "ber"))
    for method_index, (label, color) in enumerate(zip(labels, colors)):
        values = ber_values[label]
        axes[1].bar(
            x + (method_index - 1.5) * width,
            values,
            width,
            color=color,
        )
    axes[1].set_xticks(
        x,
        [label for _, _, label, _ in metrics],
        rotation=18,
        ha="right",
        rotation_mode="anchor",
    )
    axes[1].set_ylim(0, 0.55)
    axes[1].set_ylabel("Mean BER")
    axes[1].set_title("b  Bit error rate", loc="left", pad=5)
    for method_index, row in enumerate(rows):
        values = [100 * float(row[result_key]) for _, _, _, result_key in metrics]
        for x_value, value in zip(x, values):
            if value == 0:
                axes[0].text(
                    x_value + (method_index - 1.5) * width,
                    1.0,
                    "0",
                    ha="center",
                    va="bottom",
                    fontsize=5.5,
                    color=colors[method_index],
                )
    handles = [
        mpl.patches.Patch(color=color, label=label)
        for label, color in zip(labels, colors)
    ]
    fig.legend(
        handles=handles,
        labels=labels,
        ncol=4,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.02),
    )
    save_figure(fig, "fig9_external")


def load_rgb_image(path):
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"))


def add_zoom_inset(ax, image, panel_size=96):
    height, width = image.shape[:2]
    center_y = height // 2
    center_x = width // 2
    half = panel_size // 2
    crop = image[
        center_y - half : center_y + half,
        center_x - half : center_x + half,
    ]
    inset = ax.inset_axes([0.67, 0.02, 0.30, 0.30])
    inset.imshow(crop, interpolation="nearest")
    inset.set_xticks([])
    inset.set_yticks([])
    for spine in inset.spines.values():
        spine.set_visible(True)
        spine.set_edgecolor(GOLD)
        spine.set_linewidth(1.2)


def make_figure10_external_visual():
    rows = read_csv(
        SCRIPT_DIR / "results_visual_evidence" / "multimethod_examples.csv"
    )
    method_order = ["original", "ours", "dwtDct", "dwtDctSvd", "rivaGan"]
    method_titles = {
        "original": "Original",
        "ours": "Ours",
        "dwtDct": "DWT-DCT",
        "dwtDctSvd": "DWT-DCT-SVD",
        "rivaGan": "RivaGAN\n32 bit",
    }
    categories = ["landscape", "portrait"]
    by_key = {
        (row["category"], row["method"]): row
        for row in rows
    }
    fig, axes = plt.subplots(
        2,
        5,
        figsize=(7.2, 3.55),
        constrained_layout=True,
    )
    panel_index = 0
    for row_index, category in enumerate(categories):
        for col_index, method in enumerate(method_order):
            item = by_key[(category, method)]
            image_path = PROJECT_DIR / item["relative_path"]
            image = load_rgb_image(image_path)
            ax = axes[row_index, col_index]
            ax.imshow(image, interpolation="nearest")
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.text(
                0.01,
                0.99,
                "abcdefghij"[panel_index],
                transform=ax.transAxes,
                ha="left",
                va="top",
                color="white",
                fontsize=8,
                fontweight="bold",
                bbox={"facecolor": "black", "alpha": 0.55, "edgecolor": "none", "pad": 1.2},
            )
            panel_index += 1
            if row_index == 0:
                title = method_titles[method]
                if item["psnr"]:
                    title += (
                        f"\n{float(item['psnr']):.2f} dB / "
                        f"{float(item['ssim']):.4f}"
                    )
                ax.set_title(title, fontsize=6.5, pad=3)
            add_zoom_inset(ax, image)
        axes[row_index, 0].set_ylabel(
            "Landscape" if category == "landscape" else "Portrait",
            fontsize=8,
            fontweight="bold",
        )
    fig.suptitle(
        "Watermark visibility across methods (centre patches enlarged)",
        fontsize=9,
        fontweight="bold",
    )
    save_figure(fig, "fig10_multimethod_visual")


def make_figure11_case_gallery():
    rows = read_csv(SCRIPT_DIR / "results_visual_evidence" / "case_gallery.csv")
    labels = {
        "clean": "Clean",
        "jpeg": "JPEG Q70",
        "crop": "Crop 0.9",
        "print_scan": "Print-scan",
    }
    fig = plt.figure(figsize=(7.2, 3.6))
    grid = fig.add_gridspec(2, 4, height_ratios=[3.3, 1.2], hspace=0.12)
    for index, row in enumerate(rows):
        image = load_rgb_image(PROJECT_DIR / row["relative_path"])
        ax = fig.add_subplot(grid[0, index])
        ax.imshow(image, interpolation="nearest")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_linewidth(1.5)
            spine.set_edgecolor(GREEN if int(row["success"]) else RED)
        ax.set_title(labels[row["attack"]], fontsize=8, pad=4)
        ax.text(
            0.025,
            0.97,
            "abcd"[index],
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            fontweight="bold",
            color=DARK,
            bbox={"facecolor": "white", "alpha": 0.88, "edgecolor": "none", "pad": 1.2},
        )

        info = fig.add_subplot(grid[1, index])
        info.axis("off")
        if int(row["success"]):
            status = "ACCEPT"
            detail = (
                f"ID {row['decoded_id_prefix']}\n"
                f"C2 {float(row['content_binding_score']):.3f}\n"
                f"Trust {row['trust'].upper()}"
            )
        else:
            status = "REJECT"
            detail = (
                f"ID {row['decoded_id_prefix']}\n"
                f"Expected {row['expected_id_prefix']}\n"
                f"Trust {row['trust'].upper()}"
            )
        info.text(
            0.5,
            0.88,
            status,
            ha="center",
            va="top",
            fontsize=7.5,
            fontweight="bold",
            color=GREEN if int(row["success"]) else RED,
        )
        info.text(
            0.5,
            0.64,
            detail,
            ha="center",
            va="top",
            fontsize=6.5,
            color=DARK,
            linespacing=1.2,
        )
        if row["alignment"] != "identity":
            info.text(
                0.5,
                0.05,
                f"Alignment: {row['alignment']}",
                ha="center",
                va="bottom",
                fontsize=5.8,
                color=NEUTRAL,
            )
    fig.suptitle(
        "End-to-end provenance case: one registered image through four propagation conditions",
        fontsize=8.8,
        fontweight="bold",
    )
    save_figure(fig, "fig11_case_gallery")


def make_figure12_failure_attribution():
    pass_rows = read_csv(
        SCRIPT_DIR
        / "results_verification_attribution_alpha28"
        / "stage_pass_rates.csv"
    )
    failure_rows = read_csv(
        SCRIPT_DIR
        / "results_verification_attribution_alpha28"
        / "first_failure_counts.csv"
    )
    if not pass_rows or len(pass_rows) != len(failure_rows):
        raise ValueError("Verification-attribution source tables are incomplete.")

    stage_columns = [
        ("crc_pass_rate", "CRC"),
        ("rs_pass_rate", "RS"),
        ("generation_id_pass_rate", "Gen. ID"),
        ("field_consistency_pass_rate", "Fields"),
        ("content_binding_pass_rate", "Content"),
        ("final_accept_rate", "Accept"),
    ]
    failure_columns = [
        ("Accepted", "Accepted", GREEN),
        ("Payload integrity", "Payload", GOLD),
        ("Registry mismatch", "Registry", VIOLET),
        ("Content binding", "Content", RED),
        ("Trust threshold", "Trust", TEAL),
    ]
    matrix = np.asarray(
        [
            [100.0 * float(row[column]) for column, _ in stage_columns]
            for row in pass_rows
        ]
    )
    failure_matrix = np.asarray(
        [
            [100.0 * float(row[column]) for column, _, _ in failure_columns]
            for row in failure_rows
        ]
    )

    from matplotlib.colors import LinearSegmentedColormap

    stage_cmap = LinearSegmentedColormap.from_list(
        "stage_pass",
        [RED, GOLD_LIGHT, BLUE],
        N=256,
    )
    fig, (ax_stage, ax_failure) = plt.subplots(
        1,
        2,
        figsize=(7.2, 6.6),
        sharey=True,
        gridspec_kw={"width_ratios": [1.55, 1.0], "wspace": 0.13},
        constrained_layout=True,
    )
    image = ax_stage.imshow(
        matrix,
        cmap=stage_cmap,
        vmin=0,
        vmax=100,
        aspect="auto",
        interpolation="nearest",
    )
    for row_index in range(matrix.shape[0]):
        for column_index in range(matrix.shape[1]):
            value = matrix[row_index, column_index]
            color = "white" if value < 25 or value > 78 else DARK
            ax_stage.text(
                column_index,
                row_index,
                f"{value:.0f}",
                ha="center",
                va="center",
                fontsize=5.4,
                color=color,
            )
    for boundary in np.arange(0.5, matrix.shape[0], 1):
        ax_stage.axhline(boundary, color="white", linewidth=0.45)
    for boundary in np.arange(0.5, matrix.shape[1], 1):
        ax_stage.axvline(boundary, color="white", linewidth=0.55)

    ax_stage.set_xticks(
        np.arange(len(stage_columns)),
        [label for _, label in stage_columns],
        rotation=24,
        ha="right",
        rotation_mode="anchor",
    )
    ax_stage.set_yticks(
        np.arange(len(pass_rows)),
        [row["label"] for row in pass_rows],
    )
    ax_stage.tick_params(axis="both", length=0, pad=3)
    ax_stage.set_title(
        "a  Cumulative stage pass rate (%; n=200/row)",
        loc="left",
        pad=10,
        fontsize=8.4,
    )
    ax_stage.set_xlabel("Verification stage", labelpad=3)
    for spine in ax_stage.spines.values():
        spine.set_visible(False)

    positions = np.arange(len(failure_rows))
    left = np.zeros(len(failure_rows), dtype=float)
    for column_index, (_, legend_label, color) in enumerate(failure_columns):
        values = failure_matrix[:, column_index]
        ax_failure.barh(
            positions,
            values,
            left=left,
            height=0.78,
            color=color,
            edgecolor="white",
            linewidth=0.45,
            label=legend_label,
        )
        for row_index, (start, value) in enumerate(zip(left, values)):
            if value >= 5:
                ax_failure.text(
                    start + value / 2,
                    row_index,
                    f"{value:.0f}",
                    ha="center",
                    va="center",
                    fontsize=5.2,
                    color="white" if value >= 20 else DARK,
                )
        left += values
    ax_failure.set_xlim(0, 100)
    ax_failure.set_ylim(len(failure_rows) - 0.5, -0.5)
    ax_failure.set_xlabel("First failure attribution (%)")
    ax_failure.set_title(
        "b  Earliest unmet gate (n=200/row)",
        loc="left",
        pad=10,
        fontsize=8.4,
    )
    ax_failure.tick_params(axis="y", left=False, labelleft=False)
    ax_failure.grid(axis="x", color=NEUTRAL_LIGHT, linewidth=0.55)
    ax_failure.set_axisbelow(True)
    handles, labels = ax_failure.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.025),
        ncol=5,
        fontsize=6.0,
        handlelength=1.1,
        columnspacing=0.8,
        borderaxespad=0,
    )

    single_indices = [
        index
        for index, row in enumerate(pass_rows)
        if row["attack_group"] == "single"
    ]
    compound_indices = [
        index
        for index, row in enumerate(pass_rows)
        if row["attack_group"] == "combined"
    ]
    for ax in (ax_stage, ax_failure):
        if single_indices and compound_indices:
            boundary = max(single_indices) + 0.5
            ax.axhline(boundary, color=DARK, linewidth=1.0)
    save_figure(fig, "fig12_failure_attribution")


def make_graphical_abstract():
    fig, ax = plt.subplots(figsize=(7.2, 3.1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(
        0.5,
        0.94,
        "Structured AIGC provenance with database-backed trust",
        ha="center",
        va="top",
        fontsize=11,
        fontweight="bold",
    )
    cards = [
        ("1", "Generation event", "platform + generation ID", BLUE_LIGHT, BLUE),
        ("2", "Robust payload", "128-bit record + ECC", GOLD_LIGHT, GOLD),
        ("3", "DWT-DCT embed", "blind image watermark", TEAL_LIGHT, TEAL),
        ("4", "Joint verification", "registry + content + trust", GREEN_LIGHT, GREEN),
    ]
    xs = [0.03, 0.275, 0.52, 0.765]
    for index, (number, title, detail, face, edge) in enumerate(cards):
        x = xs[index]
        add_box(ax, x, 0.25, 0.20, 0.50, title, detail, face, edge, 9, 7)
        ax.text(
            x + 0.02,
            0.79,
            number,
            ha="left",
            va="top",
            fontsize=10,
            color=edge,
            fontweight="bold",
        )
        if index < len(cards) - 1:
            add_arrow(ax, (x + 0.20, 0.50), (xs[index + 1], 0.50), NEUTRAL)
    ax.text(
        0.5,
        0.08,
        "A watermark is accepted only when payload, registry record, and image content agree.",
        ha="center",
        va="center",
        fontsize=8,
        color=NEUTRAL,
    )
    save_figure(fig, "graphical_abstract")


def main():
    setup_style()
    make_figure1()
    make_figure2()
    make_figure3()
    make_figure4()
    make_figure5()
    make_figure6()
    make_figure7()
    make_figure8()
    make_figure9()
    make_figure10_external_visual()
    make_figure11_case_gallery()
    make_figure12_failure_attribution()
    make_graphical_abstract()
    print(f"figures={OUT_DIR}")


if __name__ == "__main__":
    main()
