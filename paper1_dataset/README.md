# Paper 1 Dataset Preparation

This folder generates the image dataset for Paper 1:

`AIGC image content verification and trust scoring`

## What it does

The script calls the local Stable Diffusion WebUI API, generates images, assigns a
unique `generation_id` to every image, and writes a `metadata.csv` record for each
image.

The metadata file is the source of truth for later experiments. Do not delete or
edit it after experiments begin.

## Before running

1. Start Stable Diffusion WebUI with API enabled:

```bash
webui-user.bat --api
```

2. Make sure the API is available:

```text
http://127.0.0.1:7860/docs
```

3. Check or switch to the model you want:

```text
http://127.0.0.1:7860/sdapi/v1/options
```

The current model is recorded automatically in `metadata.csv`.

## Run a small pilot

```bash
python generate_dataset.py --count 10
```

Output:

```text
images_positive/
metadata_positive.csv
```

## Run the full positive set

```bash
python generate_dataset.py --count 200
```

The script resumes from the existing `metadata_positive.csv`, so it is safe to
stop and restart it.

## Recommended next steps

1. Generate 180-200 positive images with this script.
2. Switch to another model and generate 40-60 non-platform negatives.
3. Add 40-60 natural images from COCO, Unsplash, or your own photos.
4. Keep all three groups in separate folders and record them in metadata.

## Current dataset

The current dataset contains:

| Group | Folder | Metadata | Count |
|---|---|---|---|
| Platform positive | `images_positive_general` | `metadata_positive_general.csv` | 200 |
| Other-model negative | `images_negative_other` | `images_negative_other_corrected.csv` | 50 |
| Natural image negative | `images_natural` | `metadata_natural.csv` | 50 |

The combined experiment index is `metadata_all.csv` with 300 rows. It adds a
`sample_group` column with values `positive`, `negative_ai`, and `natural`.

Natural images were downloaded from Wikimedia Commons. Their metadata includes
source URL, artist, license, license URL, and attribution requirement.

## Natural image 512 preprocessing

The original 512 version used non-uniform stretching and was kept as a backup:

```text
images_natural_512_stretch_backup_<timestamp>/
resize_params_natural_512_stretch_backup_<timestamp>.csv
```

The corrected version uses short-side resize followed by center crop:

```text
images_natural_512/
resize_params_natural_512_center_crop.csv
metadata_natural_512.csv
```

The corrected parameter file records source dimensions, EXIF orientation,
resize scale, resized dimensions, crop coordinates, output dimensions, JPEG
quality, and output SHA-256.
