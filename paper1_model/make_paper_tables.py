#!/usr/bin/env python3
"""Generate paper-ready CSV and LaTeX tables from frozen result artifacts."""

from __future__ import annotations

import csv
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATASET_DIR = PROJECT_DIR / "paper1_dataset"
OUT_DIR = PROJECT_DIR / "paper1_submission" / "paper_tables"
MANUSCRIPT_TABLE_DIR = (
    PROJECT_DIR / "paper1_submission" / "manuscript_latex" / "tables"
)


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def latex_escape(value):
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def write_csv_table(name, fieldnames, rows):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_latex_table(name, caption, label, headers, align, rows, note=None):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    columns = " ".join(align)
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        rf"\caption{{{latex_escape(caption)}}}",
        rf"\label{{{label}}}",
        rf"\begin{{tabular}}{{{columns}}}",
        r"\toprule",
        " & ".join(latex_escape(header) for header in headers) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(latex_escape(row[key]) for key in headers) + r" \\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    if note:
        lines.extend([r"\par\smallskip", rf"\footnotesize {latex_escape(note)}"])
    lines.append(r"\end{table}")
    (OUT_DIR / f"{name}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def grouped_attack_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        params = json.loads(row["params"] or "{}")
        key = (row["attack"], tuple(sorted(params.items())))
        grouped[key].append(row)
    return grouped


def attack_display_name(attack, params):
    names = {
        "clean": "Clean",
        "jpeg": f"JPEG Q{params.get('quality')}",
        "resize": f"Resize x{params.get('scale')}",
        "crop": f"Crop {params.get('ratio')}",
        "gaussian_noise": f"Gaussian noise sigma={params.get('sigma')}",
        "salt_pepper": f"Salt-and-pepper {params.get('amount')}",
        "brightness_contrast": "Brightness/contrast",
        "blur": f"Gaussian blur {params.get('ksize')}x{params.get('ksize')}",
        "screenshot": "Screenshot simulation",
        "crop_jpeg": (
            f"Crop {params.get('crop_ratio')} + JPEG "
            f"Q{params.get('jpeg_quality')}"
        ),
        "resize_jpeg": (
            f"Resize x{params.get('scale')} + JPEG "
            f"Q{params.get('jpeg_quality')}"
        ),
        "screenshot_noise": (
            f"Screenshot + noise sigma={params.get('sigma')}"
        ),
        "blur_jpeg": (
            f"Blur + JPEG Q{params.get('jpeg_quality')}"
        ),
        "crop_resize_jpeg": (
            f"Crop {params.get('crop_ratio')} + resize "
            f"x{params.get('scale')} + JPEG Q{params.get('jpeg_quality')}"
        ),
        "social_recompress": "Social recompression",
    }
    return names.get(attack, attack.replace("_", " ").title())


def attack_sort_key(item):
    order = {
        "clean": 0,
        "jpeg": 1,
        "resize": 2,
        "crop": 3,
        "gaussian_noise": 4,
        "salt_pepper": 5,
        "brightness_contrast": 6,
        "blur": 7,
        "screenshot": 8,
        "crop_jpeg": 9,
        "resize_jpeg": 10,
        "screenshot_noise": 11,
        "blur_jpeg": 12,
        "crop_resize_jpeg": 13,
        "social_recompress": 14,
    }
    (attack, params), _ = item
    return (order.get(attack, 99), str(params))


def make_tables():
    metadata = read_csv(DATASET_DIR / "metadata_all.csv")
    group_counts = Counter(row["sample_group"] for row in metadata)
    natural_licenses = Counter(
        row["license"] for row in metadata if row["sample_group"] == "natural"
    )

    table1 = [
        {
            "Group": "Platform positive",
            "Source": "SD 1.5 / Anything V5",
            "Count": str(group_counts["positive"]),
            "Role": "Registered provenance records",
        },
        {
            "Group": "Other-model AI negative",
            "Source": "Elysium Anime V3",
            "Count": str(group_counts["negative_ai"]),
            "Role": "Non-platform AI images",
        },
        {
            "Group": "Natural negative",
            "Source": "Wikimedia Commons",
            "Count": str(group_counts["natural"]),
            "Role": "Non-AI images",
        },
    ]
    fields1 = ["Group", "Source", "Count", "Role"]
    write_csv_table("table3_dataset", fields1, table1)
    write_latex_table(
        "table3_dataset",
        "Composition of the 300-image evaluation benchmark.",
        "tab:dataset",
        fields1,
        ["l", "l", "r", "l"],
        table1,
        (
            "All images were evaluated at 512 x 512. Natural-image licenses: "
            + ", ".join(f"{key} ({value})" for key, value in sorted(natural_licenses.items()))
            + "."
        ),
    )

    table2 = [
        {"Field": "Version", "Bits": "4", "Purpose": "Payload format version"},
        {"Field": "Platform hash", "Bits": "8", "Purpose": "Platform namespace"},
        {"Field": "Generation hash", "Bits": "48", "Purpose": "Per-generation identifier projection"},
        {"Field": "Model-version hash", "Bits": "8", "Purpose": "Generator/model version"},
        {"Field": "Timestamp", "Bits": "24", "Purpose": "Hours since Unix epoch"},
        {"Field": "Content hash", "Bits": "16", "Purpose": "Compact content projection"},
        {"Field": "Reserved", "Bits": "4", "Purpose": "Future extension"},
        {"Field": "CRC-16", "Bits": "16", "Purpose": "Header integrity"},
        {"Field": "Total", "Bits": "128", "Purpose": "16-byte structured payload"},
    ]
    fields2 = ["Field", "Bits", "Purpose"]
    write_csv_table("table1_payload", fields2, table2)
    write_latex_table(
        "table1_payload",
        "Structured 128-bit provenance payload.",
        "tab:payload",
        fields2,
        ["l", "r", "l"],
        table2,
        (
            "After CRC-16, RS(32,16) expands the 16-byte payload to 32 bytes; "
            "fourfold repetition produces 1024 coded bits."
        ),
    )

    table3 = [
        {"Parameter": "Input size", "Value": "512 x 512 px"},
        {"Parameter": "Color/luminance domain", "Value": "Y channel"},
        {"Parameter": "DWT", "Value": "Haar, level 1"},
        {"Parameter": "DCT block", "Value": "8 x 8"},
        {"Parameter": "Coefficient pair", "Value": "(3,2) and (2,3)"},
        {"Parameter": "Embedding strength", "Value": "alpha = 28"},
        {"Parameter": "Block selection seed", "Value": "20260910"},
        {"Parameter": "Error control", "Value": "RS(32,16) + 4-repeat"},
        {"Parameter": "Coded payload length", "Value": "1024 bits"},
        {"Parameter": "ORB binding threshold", "Value": "0.30"},
        {"Parameter": "Flat-image fallback", "Value": "0.90"},
        {"Parameter": "Medium trust threshold", "Value": "0.32"},
        {"Parameter": "High trust threshold", "Value": "0.55"},
    ]
    fields3 = ["Parameter", "Value"]
    write_csv_table("table2_parameters", fields3, table3)
    write_latex_table(
        "table2_parameters",
        "Embedding, error-control, and verification parameters.",
        "tab:parameters",
        fields3,
        ["l", "l"],
        table3,
    )

    single_rows = [
        row
        for row in read_csv(
            SCRIPT_DIR / "results_full_capture_scan" / "robustness_detail.csv"
        )
        if row["attack"] not in {"real_screen_capture", "print_scan"}
    ]
    combined_rows = read_csv(
        SCRIPT_DIR / "results_combined_alpha28" / "combined_detail.csv"
    )
    table4 = []
    for family, grouped in (
        ("Single", grouped_attack_rows(single_rows)),
        ("Compound", grouped_attack_rows(combined_rows)),
    ):
        for (attack, params_items), rows in sorted(grouped.items(), key=attack_sort_key):
            params = dict(params_items)
            table4.append(
                {
                    "Family": family,
                    "Operation": attack_display_name(attack, params),
                    "N": str(len(rows)),
                    "Success (%)": f"{100 * sum(int(r['success']) for r in rows) / len(rows):.1f}",
                    "BER": f"{sum(float(r['ber']) for r in rows) / len(rows):.3f}",
                }
            )
    fields4 = ["Family", "Operation", "N", "Success (%)", "BER"]
    write_csv_table("table4_robustness", fields4, table4)
    write_latex_table(
        "table4_robustness",
        "Verification success, mean BER, and trust composition under single and compound transformations.",
        "tab:robustness",
        fields4,
        ["l", "l", "r", "r", "r"],
        table4,
        (
            "Each operation uses 200 registered positives. Success requires a "
            "valid CRC/RS decode, a database generation match, content binding, "
            "and a non-low trust score. Trust-level composition is shown in "
            "Fig. 6."
        ),
    )

    full_ablation = (
        SCRIPT_DIR / "results_ablation_full_alpha28" / "ablation_summary.csv"
    )
    ablation = read_csv(
        full_ablation
        if full_ablation.exists()
        else SCRIPT_DIR / "results_ablation" / "ablation_summary.csv"
    )
    ablation_group_order = {"carrier": 0, "coding": 1, "alpha": 2}
    ablation_config_order = {
        "dwt_dct": 0,
        "dwt_only": 1,
        "dct_only": 2,
        "lsb": 3,
        "rs_repeat": 0,
        "rs_only": 1,
        "repeat_only": 2,
        "raw": 3,
    }
    ablation = sorted(
        ablation,
        key=lambda row: (
            ablation_group_order.get(row["group"], 9),
            int(row["config"].split("_")[1])
            if row["group"] == "alpha"
            else ablation_config_order.get(row["config"], 9),
        ),
    )
    table5 = []
    for row in ablation:
        if row["group"] == "verification":
            continue
        table5.append(
            {
                "Group": row["group"],
                "Configuration": row["config"],
                "PSNR (dB)": f"{float(row['mean_psnr']):.2f}",
                "SSIM": f"{float(row['mean_ssim']):.4f}",
                "JPEG50 (%)": f"{100 * float(row['jpeg50_success']):.1f}",
                "Crop (%)": f"{100 * float(row['crop_success']):.1f}",
                "Blur (%)": f"{100 * float(row['blur_success']):.1f}",
                "Screenshot (%)": f"{100 * float(row['screenshot_success']):.1f}",
            }
        )
    fields5 = [
        "Group",
        "Configuration",
        "PSNR (dB)",
        "SSIM",
        "JPEG50 (%)",
        "Crop (%)",
        "Blur (%)",
        "Screenshot (%)",
    ]
    write_csv_table("table5_ablation", fields5, table5)
    write_latex_table(
        "table5_ablation",
        "Carrier, coding, and embedding-strength ablations.",
        "tab:ablation",
        fields5,
        ["l", "l", "r", "r", "r", "r", "r", "r"],
        table5,
        (
            "The ablation uses 200 positive images and alpha=28 for carrier "
            "and coding comparisons."
            if full_ablation.exists()
            else (
                "The ablation uses 10 positive images and alpha=24; treat the "
                "differences as exploratory."
            )
        ),
    )

    external = read_csv(
        SCRIPT_DIR / "results_external_baselines" / "matched_comparison.csv"
    )
    external_by_method = {row["method"]: row for row in external}
    method_labels = {
        "Ours (structured + DB, matched subset)": "Ours",
        "external dwtDct": "DWT-DCT",
        "external dwtDctSvd": "DWT-DCT-SVD",
        "RivaGAN (pretrained)": "RivaGAN",
    }
    table6 = []
    metric_specs = [
        ("Payload bits", "payload_bits", lambda value: str(value)),
        ("N", "count", lambda value: str(value)),
        ("PSNR (dB)", "psnr", lambda value: f"{float(value):.2f}"),
        ("SSIM", "ssim", lambda value: f"{float(value):.4f}"),
        ("JPEG50 (%)", "jpeg50", lambda value: f"{100 * float(value):.1f}"),
        ("Crop (%)", "crop", lambda value: f"{100 * float(value):.1f}"),
        ("Blur (%)", "blur", lambda value: f"{100 * float(value):.1f}"),
        ("Screenshot (%)", "screenshot", lambda value: f"{100 * float(value):.1f}"),
        (
            "Crop+Resize+JPEG (%)",
            "crop_resize_jpeg",
            lambda value: f"{100 * float(value):.1f}",
        ),
    ]
    for metric, key, formatter in metric_specs:
        row = {"Metric": metric}
        for source_name, display_name in method_labels.items():
            row[display_name] = formatter(external_by_method[source_name][key])
        table6.append(row)
    fields6 = ["Metric", "Ours", "DWT-DCT", "DWT-DCT-SVD", "RivaGAN"]
    write_csv_table("table6_external", fields6, table6)
    write_latex_table(
        "table6_external",
        "Comparison with external watermarking methods on the common 50-image subset.",
        "tab:external",
        fields6,
        ["l", "r", "r", "r", "r"],
        table6,
        (
            "RivaGAN uses a native 32-bit payload and is a short-payload "
            "reference, not an equal-payload baseline."
        ),
    )

    forgery = read_json(
        SCRIPT_DIR / "results_verification_ablation" / "summary.json"
    )
    copy = read_json(
        SCRIPT_DIR / "results_copy_attack_alpha28" / "summary.json"
    )
    flat = read_json(
        SCRIPT_DIR / "results_flat_sensitivity_alpha28" / "summary.json"
    )
    capture = read_json(
        SCRIPT_DIR / "results_full_capture_scan" / "summary.json"
    )
    calibration = read_json(
        SCRIPT_DIR
        / "results_threshold_calibration_split_alpha28"
        / "summary.json"
    )
    clean_negative = read_json(
        SCRIPT_DIR / "results_full_capture_scan" / "summary.json"
    )["false_positive"]

    held_out_high = next(
        item
        for item in calibration["operational_thresholds"]
        if item["name"] == "operational_high"
    )
    held_out_medium = next(
        item
        for item in calibration["operational_thresholds"]
        if item["name"] == "operational_medium"
    )
    security_rows = [
        {
            "Test": "Forged valid payload",
            "Condition": "Watermark only",
            "Accepted / tested": (
                f"{round(forgery['watermark_only']['acceptance_rate'] * forgery['watermark_only']['count'])}"
                f" / {forgery['watermark_only']['count']}"
            ),
            "Interpretation": "No registry/content rejection",
        },
        {
            "Test": "Forged valid payload",
            "Condition": "Joint verification",
            "Accepted / tested": (
                f"{round(forgery['joint']['acceptance_rate'] * forgery['joint']['count'])}"
                f" / {forgery['joint']['count']}"
            ),
            "Interpretation": "Unregistered generation ID rejected",
        },
        {
            "Test": "Copied watermark",
            "Condition": "Binding off",
            "Accepted / tested": f"{round(50 * copy['copy_attack']['binding_0:joint']['acceptance_rate'])} / 50",
            "Interpretation": "Payload-only verification is vulnerable",
        },
        {
            "Test": "Copied watermark",
            "Condition": "Binding on",
            "Accepted / tested": f"{round(50 * copy['copy_attack']['binding_1:joint']['acceptance_rate'])} / 50",
            "Interpretation": "Content mismatch rejected",
        },
        {
            "Test": "Flat-image fallback",
            "Condition": "Threshold 0.30",
            "Accepted / tested": (
                f"TPR {100 * flat['default_threshold_result']['tpr']:.1f}%; "
                f"FPR {100 * flat['default_threshold_result']['fpr']:.1f}%"
            ),
            "Interpretation": "Unsafe for flat images",
        },
        {
            "Test": "Flat-image fallback",
            "Condition": "Threshold 0.90",
            "Accepted / tested": (
                f"TPR {100 * flat['adaptive_policy']['flat_result']['tpr']:.1f}%; "
                f"FPR {100 * flat['adaptive_policy']['flat_result']['fpr']:.1f}%"
            ),
            "Interpretation": "Conservative fallback",
        },
    ]
    calibration_rows = [
        {
            "Test": "Held-out trust",
            "Condition": "Score >= 0.55",
            "Accepted / tested": (
                f"TPR {100 * held_out_high['tpr']:.1f}%; "
                f"FPR {100 * held_out_high['fpr']:.2f}%"
            ),
            "Interpretation": "High-confidence operating point",
        },
        {
            "Test": "Held-out trust",
            "Condition": "Score >= 0.32",
            "Accepted / tested": (
                f"TPR {100 * held_out_medium['tpr']:.1f}%; "
                f"FPR {100 * held_out_medium['fpr']:.2f}%"
            ),
            "Interpretation": "Medium-or-higher operating point",
        },
        {
            "Test": "Clean negatives",
            "Condition": "Joint verification",
            "Accepted / tested": (
                f"{clean_negative['false_positive_count']} / "
                f"{clean_negative['count']}"
            ),
            "Interpretation": "No observed clean false positives",
        },
        {
            "Test": "Physical stress",
            "Condition": "Screen-capture simulator",
            "Accepted / tested": (
                f"{round(capture['robustness']['real_screen_capture:{}']['success_rate'] * capture['robustness']['real_screen_capture:{}']['count'])}"
                f" / {capture['robustness']['real_screen_capture:{}']['count']}"
            ),
            "Interpretation": "Current carrier fails",
        },
        {
            "Test": "Physical stress",
            "Condition": "Print-scan simulator",
            "Accepted / tested": (
                f"{round(capture['robustness']['print_scan:{}']['success_rate'] * capture['robustness']['print_scan:{}']['count'])}"
                f" / {capture['robustness']['print_scan:{}']['count']}"
            ),
            "Interpretation": "Current carrier fails",
        },
    ]
    fields7 = ["Test", "Condition", "Accepted / tested", "Interpretation"]
    write_csv_table("table7_security", fields7, security_rows)
    write_latex_table(
        "table7_security",
        "Forgery, copy attack, and flat-image security tests.",
        "tab:security",
        fields7,
        [
            r">{\raggedright\arraybackslash}p{27mm}",
            r">{\raggedright\arraybackslash}p{32mm}",
            r">{\raggedright\arraybackslash}p{38mm}",
            r">{\raggedright\arraybackslash}p{48mm}",
        ],
        security_rows,
        (
            "Copy testing contains 50 paired donor-target trials. Flat-image "
            "testing contains 11 synthetic images."
        ),
    )
    write_csv_table("table8_calibration_negative", fields7, calibration_rows)
    write_latex_table(
        "table8_calibration_negative",
        "Calibrated trust thresholds, clean negatives, and physical stress tests.",
        "tab:calibration-negative",
        fields7,
        [
            r">{\raggedright\arraybackslash}p{27mm}",
            r">{\raggedright\arraybackslash}p{32mm}",
            r">{\raggedright\arraybackslash}p{38mm}",
            r">{\raggedright\arraybackslash}p{48mm}",
        ],
        calibration_rows,
        (
            "Held-out rates aggregate repeated attack observations from 50 "
            "held-out negative images. Physical stress tests use 200 registered "
            "positives."
        ),
    )

    index_lines = [
        "# Paper 1 Table Bundle",
        "",
        "Generated from the frozen evidence versions by `make_paper_tables.py`.",
        "",
        "| Table | CSV | LaTeX |",
        "|---|---|---|",
    ]
    table_files = [
        "table1_payload",
        "table2_parameters",
        "table3_dataset",
        "table4_robustness",
        "table5_ablation",
        "table6_external",
        "table7_security",
        "table8_calibration_negative",
    ]
    for index, stem in enumerate(table_files, 1):
        index_lines.append(f"| {index} | `{stem}.csv` | `{stem}.tex` |")
    index_lines += [
        "",
        "The LaTeX fragments require `booktabs`. They are single-column tables",
        "and intentionally contain no vertical rules or cell shading.",
        "",
        "The same `.tex` and `.csv` files are mirrored under "
        "`manuscript_latex/tables/` for self-contained LaTeX builds.",
        "",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(index_lines), encoding="utf-8")
    MANUSCRIPT_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    for stem in table_files:
        for extension in ("csv", "tex"):
            source = OUT_DIR / f"{stem}.{extension}"
            shutil.copy2(source, MANUSCRIPT_TABLE_DIR / source.name)


if __name__ == "__main__":
    make_tables()
