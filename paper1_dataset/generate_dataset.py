#!/usr/bin/env python3
"""Batch-generate AIGC images and provenance metadata from Stable Diffusion WebUI."""

import argparse
import base64
import csv
import hashlib
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_API = "http://127.0.0.1:7860"
DEFAULT_NEGATIVE = "low quality, blurry, watermark, text, logo, deformed"

FIELDNAMES = [
    "generation_id",
    "filename",
    "relative_path",
    "platform_id",
    "model_name",
    "model_version",
    "prompt",
    "prompt_sha256",
    "negative_prompt",
    "seed",
    "sampler",
    "steps",
    "cfg_scale",
    "width",
    "height",
    "created_at",
    "sha256",
    "category",
    "is_platform_sample",
]


def api_get(base_url, endpoint, timeout=30):
    response = requests.get(f"{base_url}{endpoint}", timeout=timeout)
    response.raise_for_status()
    return response.json()


def api_post(base_url, endpoint, payload, timeout=600):
    response = requests.post(f"{base_url}{endpoint}", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def load_prompts(path):
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prompt = (row.get("prompt") or "").strip()
            if prompt:
                rows.append(
                    {
                        "prompt": prompt,
                        "category": (row.get("category") or "general").strip(),
                    }
                )
    if not rows:
        raise RuntimeError(f"No prompts found in {path}")
    return rows


def read_existing_count(metadata_path):
    if not metadata_path.exists():
        return 0
    with metadata_path.open("r", encoding="utf-8-sig", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def append_metadata(metadata_path, row):
    new_file = not metadata_path.exists()
    with metadata_path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def current_model(base_url):
    options = api_get(base_url, "/sdapi/v1/options")
    return options.get("sd_model_checkpoint") or "unknown"


def build_tasks(prompts, target_count, base_seed):
    tasks = []
    repeats = target_count // len(prompts)
    remainder = target_count % len(prompts)
    for index, item in enumerate(prompts):
        count = repeats + (1 if index < remainder else 0)
        for repeat in range(count):
            tasks.append(
                {
                    "prompt": item["prompt"],
                    "category": item["category"],
                    "seed": base_seed + index * 1000 + repeat,
                }
            )
    return tasks


def decode_and_save(image_b64, output_path):
    raw = base64.b64decode(image_b64)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw)
    return raw


def generate_once(base_url, payload, retries=3):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return api_post(base_url, "/sdapi/v1/txt2img", payload)
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(3 * attempt)
    raise RuntimeError(f"txt2img failed after {retries} attempts: {last_error}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument(
        "--prompts",
        default=str(SCRIPT_DIR / "prompts.csv"),
        help="CSV file with prompt and category columns",
    )
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--steps", type=int, default=25)
    parser.add_argument("--cfg", type=float, default=7.0)
    parser.add_argument("--sampler", default="DPM++ 2M")
    parser.add_argument("--base-seed", type=int, default=100000)
    parser.add_argument("--platform-id", default="TraceArt-Lab")
    parser.add_argument(
        "--output-dir",
        default=str(SCRIPT_DIR / "images_positive"),
    )
    parser.add_argument(
        "--metadata",
        default=str(SCRIPT_DIR / "metadata_positive.csv"),
    )
    parser.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE)
    parser.add_argument(
        "--is-platform-sample",
        type=int,
        choices=[0, 1],
        default=1,
    )
    args = parser.parse_args()

    prompts = load_prompts(Path(args.prompts))
    output_dir = Path(args.output_dir)
    metadata_path = Path(args.metadata)
    output_dir.mkdir(parents=True, exist_ok=True)

    existing = read_existing_count(metadata_path)
    if existing >= args.count:
        print(f"Already have {existing} records; target is {args.count}. Nothing to do.")
        return

    model_name = current_model(args.api)
    tasks = build_tasks(prompts, args.count, args.base_seed)

    print(f"API: {args.api}")
    print(f"Model: {model_name}")
    print(f"Target: {args.count}, existing: {existing}")
    print(f"Images: {output_dir}")
    print(f"Metadata: {metadata_path}")

    for index in range(existing, len(tasks)):
        task = tasks[index]
        generation_id = uuid.uuid4().hex
        filename = f"{generation_id}.png"
        image_path = output_dir / filename
        payload = {
            "prompt": task["prompt"],
            "negative_prompt": args.negative_prompt,
            "steps": args.steps,
            "cfg_scale": args.cfg,
            "width": args.width,
            "height": args.height,
            "sampler_name": args.sampler,
            "seed": task["seed"],
            "batch_size": 1,
            "n_iter": 1,
            "save_images": False,
            "send_images": True,
        }

        try:
            result = generate_once(args.api, payload)
            images = result.get("images") or []
            if not images:
                raise RuntimeError("API returned no images")
            raw = decode_and_save(images[0], image_path)
        except Exception as exc:
            print(f"[{index + 1}/{args.count}] FAILED: {exc}", file=sys.stderr)
            continue

        created_at = datetime.now().astimezone().isoformat()
        prompt_sha256 = hashlib.sha256(task["prompt"].encode("utf-8")).hexdigest()
        image_sha256 = hashlib.sha256(raw).hexdigest()
        record = {
            "generation_id": generation_id,
            "filename": filename,
            "relative_path": str(image_path.relative_to(SCRIPT_DIR)),
            "platform_id": args.platform_id,
            "model_name": model_name,
            "model_version": model_name,
            "prompt": task["prompt"],
            "prompt_sha256": prompt_sha256,
            "negative_prompt": args.negative_prompt,
            "seed": task["seed"],
            "sampler": args.sampler,
            "steps": args.steps,
            "cfg_scale": args.cfg,
            "width": args.width,
            "height": args.height,
            "created_at": created_at,
            "sha256": image_sha256,
            "category": task["category"],
            "is_platform_sample": args.is_platform_sample,
        }
        append_metadata(metadata_path, record)
        print(
            f"[{index + 1}/{args.count}] {filename} "
            f"seed={task['seed']} category={task['category']}"
        )

    print("Done.")
    print(f"Total records: {read_existing_count(metadata_path)}")


if __name__ == "__main__":
    main()
