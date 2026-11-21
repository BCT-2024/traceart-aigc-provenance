#!/usr/bin/env python3
"""Run the Paper 1 ablation matrix."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RUNNER = SCRIPT_DIR / "run_experiment.py"
DEFAULT_OUTPUT_ROOT = SCRIPT_DIR / "results_ablation"


def configs(base_alpha=28.0):
    rows = []
    for carrier in ["dwt_dct", "dwt_only", "dct_only", "lsb"]:
        rows.append(
            {
                "group": "carrier",
                "name": carrier,
                "args": [
                    "--carrier",
                    carrier,
                    "--payload-mode",
                    "rs_repeat",
                    "--repeat",
                    "4",
                    "--alpha",
                    str(base_alpha),
                ],
            }
        )
    for mode, repeat in [
        ("rs_repeat", 4),
        ("rs_only", 1),
        ("repeat_only", 8),
        ("raw", 1),
    ]:
        rows.append(
            {
                "group": "coding",
                "name": mode,
                "args": [
                    "--carrier",
                    "dwt_dct",
                    "--payload-mode",
                    mode,
                    "--repeat",
                    str(repeat),
                    "--alpha",
                    str(base_alpha),
                ],
            }
        )
    for mode in ["joint", "watermark_only", "db_only"]:
        rows.append(
            {
                "group": "verification",
                "name": mode,
                "args": [
                    "--carrier",
                    "dwt_dct",
                    "--payload-mode",
                    "rs_repeat",
                    "--repeat",
                    "4",
                    "--alpha",
                    str(base_alpha),
                    "--verification-mode",
                    mode,
                ],
            }
        )
    for alpha in [8, 12, 16, 20, 24, 28]:
        rows.append(
            {
                "group": "alpha",
                "name": f"alpha_{alpha}",
                "args": [
                    "--carrier",
                    "dwt_dct",
                    "--payload-mode",
                    "rs_repeat",
                    "--repeat",
                    "4",
                    "--alpha",
                    str(alpha),
                ],
            }
        )
    return rows


def run_one(config, limit_pos, limit_neg, limit_natural, force, output_root):
    out_dir = output_root / config["group"] / config["name"]
    summary_path = out_dir / "summary.json"
    if summary_path.exists() and not force:
        print(f"skip existing: {out_dir}")
        return summary_path
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(RUNNER),
        "--limit-pos",
        str(limit_pos),
        "--limit-neg",
        str(limit_neg),
        "--limit-natural",
        str(limit_natural),
        "--output-dir",
        str(out_dir),
        *config["args"],
    ]
    print("run:", " ".join(command))
    subprocess.run(command, check=True)
    return summary_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-pos", type=int, default=10)
    parser.add_argument("--limit-neg", type=int, default=10)
    parser.add_argument("--limit-natural", type=int, default=10)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--base-alpha", type=float, default=28.0)
    parser.add_argument("--summary-name", default="ablation_summary.csv")
    parser.add_argument(
        "--groups",
        default="carrier,coding,verification,alpha",
        help="Comma-separated groups to run",
    )
    args = parser.parse_args()

    selected_groups = {g.strip() for g in args.groups.split(",") if g.strip()}
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / args.summary_name
    existing = {}
    if output.exists():
        with output.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                existing[(row["group"], row["config"])] = row

    summaries = {}
    for config in configs(base_alpha=args.base_alpha):
        if config["group"] not in selected_groups:
            continue
        summary_path = run_one(
            config,
            args.limit_pos,
            args.limit_neg,
            args.limit_natural,
            args.force,
            output_root,
        )
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        robustness = summary["robustness"]

        def attack_success(key):
            return robustness.get(key, {}).get("success_rate")

        summaries[(config["group"], config["name"])] = {
                "group": config["group"],
                "config": config["name"],
                "mean_psnr": summary["quality"]["mean_psnr"],
                "mean_ssim": summary["quality"]["mean_ssim"],
                "clean_success": attack_success("clean:{}"),
                "jpeg50_success": attack_success("jpeg:{'quality': 50}"),
                "crop_success": attack_success("crop:{'ratio': 0.9}"),
                "noise8_success": attack_success("gaussian_noise:{'sigma': 8}"),
                "blur_success": attack_success("blur:{'ksize': 3}"),
                "screenshot_success": attack_success("screenshot:{}"),
                "false_positive_rate": summary["false_positive"]["false_positive_rate"],
            }

    existing.update(summaries)
    fields = [
        "group",
        "config",
        "mean_psnr",
        "mean_ssim",
        "clean_success",
        "jpeg50_success",
        "crop_success",
        "noise8_success",
        "blur_success",
        "screenshot_success",
        "false_positive_rate",
    ]
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        group_order = {"carrier": 0, "coding": 1, "verification": 2, "alpha": 3}
        writer.writerows(
            sorted(
                existing.values(),
                key=lambda row: (group_order.get(row["group"], 9), row["config"]),
            )
        )
    print(f"ablation summary: {output}")


if __name__ == "__main__":
    main()
