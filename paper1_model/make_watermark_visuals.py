#!/usr/bin/env python3
"""Create visual comparisons for watermarked images."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR.parent / "paper1_dataset"
RESULTS = SCRIPT_DIR / "results_full"
OUT_DIR = RESULTS / "visual_examples"


def load_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main(sample_count: int = 4):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    quality_rows = load_csv(RESULTS / "quality_metrics.csv")
    metadata_rows = {
        row["generation_id"]: row
        for row in load_csv(DATASET_DIR / "metadata_all.csv")
    }
    selected = quality_rows[:sample_count]

    columns = 5
    fig, axes = plt.subplots(
        sample_count, columns, figsize=(18, 3.4 * sample_count)
    )
    if sample_count == 1:
        axes = np.array([axes])

    for row_index, quality in enumerate(selected):
        generation_id = quality["generation_id"]
        metadata = metadata_rows[generation_id]
        original = np.asarray(
            Image.open(DATASET_DIR / metadata["relative_path"]).convert("RGB")
        )
        watermarked = np.asarray(
            Image.open(quality["watermarked_path"]).convert("RGB")
        )
        raw_difference = np.abs(
            original.astype(np.int16) - watermarked.astype(np.int16)
        )
        difference = np.clip(
            raw_difference * 20,
            0,
            255,
        ).astype(np.uint8)

        crop_size = 64
        gray_difference = raw_difference.mean(axis=2)
        best_score = -1.0
        best_top = 0
        best_left = 0
        for top in range(0, original.shape[0] - crop_size + 1, 16):
            for left in range(0, original.shape[1] - crop_size + 1, 16):
                score = gray_difference[
                    top : top + crop_size, left : left + crop_size
                ].mean()
                if score > best_score:
                    best_score = score
                    best_top = top
                    best_left = left

        zoom_watermarked = np.asarray(
            Image.fromarray(
                watermarked[
                    best_top : best_top + crop_size,
                    best_left : best_left + crop_size,
                ]
            ).resize((256, 256), Image.Resampling.NEAREST)
        )
        zoom_difference = np.asarray(
            Image.fromarray(
                difference[
                    best_top : best_top + crop_size,
                    best_left : best_left + crop_size,
                ]
            ).resize((256, 256), Image.Resampling.NEAREST)
        )

        panels = [
            (original, "Original"),
            (watermarked, "Watermarked"),
            (difference, "Difference x20"),
            (zoom_watermarked, "Watermarked zoom x10"),
            (zoom_difference, "Difference zoom x10"),
        ]
        for col, (image, title) in enumerate(panels):
            axes[row_index, col].imshow(image)
            if row_index == 0:
                axes[row_index, col].set_title(title)
            axes[row_index, col].axis("off")

        axes[row_index, 2].add_patch(
            Rectangle(
                (best_left, best_top),
                crop_size,
                crop_size,
                fill=False,
                edgecolor="red",
                linewidth=1.8,
            )
        )
        axes[row_index, 0].set_ylabel(
            f"PSNR {float(quality['psnr']):.2f} dB\nSSIM {float(quality['ssim']):.4f}",
            rotation=0,
            labelpad=38,
            va="center",
        )

        if row_index == 0:
            Image.fromarray(watermarked).save(OUT_DIR / "watermarked_example.png")
            Image.fromarray(difference).save(OUT_DIR / "difference_x20.png")
            Image.fromarray(original).save(OUT_DIR / "original_example.png")
            Image.fromarray(zoom_watermarked).save(
                OUT_DIR / "watermarked_zoom_x10.png"
            )
            Image.fromarray(zoom_difference).save(
                OUT_DIR / "difference_zoom_x10.png"
            )

    fig.tight_layout()
    output = OUT_DIR / "watermark_comparison.png"
    fig.savefig(output, dpi=220)
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    main()
