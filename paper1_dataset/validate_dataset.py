#!/usr/bin/env python3
"""Validate the Paper 1 image dataset and write a Markdown report."""

import csv
import hashlib
import io
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image


BASE = Path(__file__).resolve().parent
METADATA = BASE / "metadata_all.csv"
REPORT = BASE / "dataset_validation_report.md"
RESIZE_PARAMS = BASE / "resize_params_natural_512.csv"


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    rows = load_csv(METADATA)
    errors = []
    warnings = []
    group_counts = Counter()
    platform_values = defaultdict(Counter)
    is_platform_values = defaultdict(Counter)
    category_counts = defaultdict(Counter)
    dimensions = Counter()
    sha_to_rows = defaultdict(list)
    generation_ids = Counter()
    filenames = Counter()
    paths = Counter()

    for index, row in enumerate(rows, 2):
        group = row.get("sample_group", "")
        group_counts[group] += 1
        platform_values[group][row.get("platform_id", "")] += 1
        is_platform_values[group][row.get("is_platform_sample", "")] += 1
        category_counts[group][row.get("category", "")] += 1
        generation_ids[row.get("generation_id", "")] += 1
        filenames[row.get("filename", "")] += 1
        paths[row.get("relative_path", "")] += 1

        rel = row.get("relative_path", "")
        path = BASE / rel
        if not rel or not path.exists():
            errors.append(f"第 {index} 行图片不存在: {rel}")
            continue
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"第 {index} 行图片为空或不是文件: {rel}")
            continue

        actual_sha = sha256_file(path)
        row_sha = row.get("sha256", "").strip()
        if row_sha and actual_sha != row_sha:
            errors.append(f"第 {index} 行 SHA-256 不一致: {rel}")
        sha_to_rows[actual_sha].append((group, rel))

        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                width, height = image.size
                mode = image.mode
                fmt = image.format
        except Exception as exc:
            errors.append(f"第 {index} 行图片无法读取: {rel} ({exc})")
            continue

        dimensions[(width, height)] += 1
        expected_width = int(float(row.get("width") or 0))
        expected_height = int(float(row.get("height") or 0))
        if (width, height) != (expected_width, expected_height):
            errors.append(
                f"第 {index} 行尺寸不一致: {rel}, 实际 {width}x{height}, "
                f"记录 {expected_width}x{expected_height}"
            )
        if mode != "RGB":
            warnings.append(f"第 {index} 行图像模式不是 RGB: {rel}, mode={mode}")
        if fmt not in ("JPEG", "PNG"):
            warnings.append(f"第 {index} 行图片格式异常: {rel}, format={fmt}")

        if group == "natural":
            if "images_natural_512" not in rel:
                errors.append(f"自然图未指向 512 目录: {rel}")
            if (width, height) != (512, 512):
                errors.append(f"自然图不是 512x512: {rel}")
            if not row.get("source_url"):
                errors.append(f"自然图缺少来源链接: {rel}")
            if not row.get("license"):
                errors.append(f"自然图缺少许可证: {rel}")

    for value, count in generation_ids.items():
        if value and count > 1:
            errors.append(f"generation_id 重复: {value}, 次数 {count}")
    for value, count in filenames.items():
        if value and count > 1:
            errors.append(f"filename 重复: {value}, 次数 {count}")
    for value, count in paths.items():
        if value and count > 1:
            errors.append(f"relative_path 重复: {value}, 次数 {count}")

    duplicate_sha = {
        sha: refs for sha, refs in sha_to_rows.items() if len(refs) > 1
    }
    for sha, refs in duplicate_sha.items():
        errors.append(f"图片内容重复 SHA-256={sha[:12]}...: {refs}")

    expected_groups = {"positive": 200, "negative_ai": 50, "natural": 50}
    for group, expected in expected_groups.items():
        if group_counts[group] != expected:
            errors.append(
                f"{group} 数量异常: 实际 {group_counts[group]}, 期望 {expected}"
            )
    if len(rows) != 300:
        errors.append(f"metadata_all.csv 总行数异常: {len(rows)}")

    folder_expectations = {
        "images_positive_general": 200,
        "images_negative_other": 50,
        "images_natural_512": 50,
    }
    folder_counts = {}
    for folder, expected in folder_expectations.items():
        actual = len([p for p in (BASE / folder).iterdir() if p.is_file()])
        folder_counts[folder] = actual
        if actual != expected:
            errors.append(f"{folder} 文件数异常: 实际 {actual}, 期望 {expected}")

    resize_rows = load_csv(RESIZE_PARAMS)
    resize_modes = Counter(row.get("resize_mode", "") for row in resize_rows)
    resize_sizes = Counter(
        (row.get("out_width"), row.get("out_height")) for row in resize_rows
    )
    resize_hash_errors = 0
    for row in resize_rows:
        output_path = BASE / row["output_relative_path"]
        if not output_path.exists():
            resize_hash_errors += 1
            continue
        if sha256_file(output_path) != row["output_sha256"]:
            resize_hash_errors += 1
    if len(resize_rows) != 50:
        errors.append(f"resize_params_natural_512_center_crop.csv 行数异常: {len(resize_rows)}")
    if resize_modes != Counter({"short_side_resize_center_crop": 50}):
        errors.append(f"自然图缩放模式异常: {resize_modes}")
    if resize_sizes != Counter({("512", "512"): 50}):
        errors.append(f"自然图输出尺寸异常: {resize_sizes}")
    if resize_hash_errors:
        errors.append(f"自然图 resize 参数表中有 {resize_hash_errors} 条哈希不匹配")

    lines = [
        "# 论文一数据集校验报告",
        "",
        f"- 元数据总行数：{len(rows)}",
        f"- 图片目录数量：{folder_counts}",
        f"- 分组数量：{dict(group_counts)}",
        f"- 图片尺寸分布：{dict(dimensions)}",
        f"- 重复 SHA-256：{len(duplicate_sha)}",
        "",
        "## 分组标签",
        "",
        f"- positive platform_id：{dict(platform_values['positive'])}",
        f"- positive is_platform_sample：{dict(is_platform_values['positive'])}",
        f"- negative_ai platform_id：{dict(platform_values['negative_ai'])}",
        f"- negative_ai is_platform_sample：{dict(is_platform_values['negative_ai'])}",
        f"- natural platform_id：{dict(platform_values['natural'])}",
        f"- natural is_platform_sample：{dict(is_platform_values['natural'])}",
        "",
        "## 类别分布",
        "",
    ]
    for group in ["positive", "negative_ai", "natural"]:
        lines.append(f"- {group}：{dict(category_counts[group])}")

    lines += [
        "",
        "## 自然图 512 处理",
        "",
        f"- 参数表行数：{len(resize_rows)}",
        f"- 缩放模式：{dict(resize_modes)}",
        f"- 输出尺寸：{dict(resize_sizes)}",
        f"- 哈希不匹配数：{resize_hash_errors}",
        "",
        "## 结论",
        "",
        "未发现错误。" if not errors else "发现以下错误：",
        "",
    ]
    for item in errors:
        lines.append(f"- {item}")
    if warnings:
        lines += ["", "## 警告", ""]
        for item in warnings:
            lines.append(f"- {item}")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rows={len(rows)} errors={len(errors)} warnings={len(warnings)}")
    print(f"report={REPORT}")
    if errors:
        for item in errors:
            print("ERROR:", item)


if __name__ == "__main__":
    main()
