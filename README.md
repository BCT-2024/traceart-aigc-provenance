# TraceArt AIGC Provenance Verification

Reproducibility package for:

> **Structured DWT-DCT Payloads for Database-Backed AIGC Image Provenance
> Verification and Trust Scoring**

Authors: Lianli Dong and Zican Luo

Affiliation: School of Economics and Management, Hunan University of Technology,
Zhuzhou 412007, Hunan, China.

This repository contains the 300-image benchmark, structured-payload and
DWT-DCT watermarking code, database/content verification code, canonical result
tables, final figures, and the LaTeX manuscript source.

## Repository structure

| Directory | Contents |
|---|---|
| `paper1_dataset/` | 200 registered positives, 50 other-model negatives, 50 natural images, metadata, prompts, and validation material |
| `paper1_model/` | Source code and curated result files |
| `paper1_submission/` | Manuscript source, bibliography, tables, and final figures in PDF, PNG, SVG, and TIFF |

## Dataset summary

- Positive images: 200 SD 1.5 / Anything V5 images.
- Other-model negatives: 50 Elysium Anime V3 images.
- Natural negatives: 50 Wikimedia Commons images.
- All images are 512 x 512.
- The dataset metadata contains generation parameters, source URLs, SHA-256
  digests, categories, resize parameters, and third-party licences.
- Natural images retain their original licences. Attribution requirements are
  recorded in `paper1_dataset/metadata_all.csv`.

## Main result sources

- `paper1_model/results_full_capture_scan/` contains the canonical single-attack
  results and clean-negative evaluation.
- `paper1_model/results_combined_alpha28/` contains the compound-attack results.
- `paper1_model/results_ablation_full_alpha28/` contains the curated
  carrier/coding/strength summaries.
- `paper1_model/results_verification_attribution_alpha28/` contains the
  4,200-observation verification-stage attribution.
- `paper1_model/results_threshold_calibration_split_alpha28/` contains the
  image-disjoint ROC and held-out operating points.
- The remaining result directories contain forgery, copied-watermark,
  flat-image, external-baseline, and visual evidence.

## GitHub Desktop workflow

This directory is intended to be opened directly as a local Git repository.

1. Open GitHub Desktop.
2. Choose **File > Add local repository**.
3. Select this `paper1_release` directory.
4. Review the initial commit and commit it if GitHub Desktop has not already
   done so.
5. Choose **Publish repository**.
6. Use a repository name such as `traceart-aigc-provenance`.
7. After uploading, create a GitHub release with tag `v1.0.0`.
8. If the GitHub repository is linked to Zenodo, publish the GitHub release and
   verify that Zenodo archives it.
9. Add the resulting DOI and repository URL to the manuscript Data Availability
   statement before final journal submission.

## Excluded material

The package excludes local caches, temporary files, redundant watermarked images,
per-configuration intermediate images from all 17 ablation variants, and
superseded partial results. The retained canonical data and source code are
sufficient to regenerate the reported tables and figures.

## Licensing

- Source code is licensed under the MIT License; see `LICENSE`.
- AIGC images, metadata, processed results, figure source data, and
  author-created figures are licensed under CC BY 4.0; see `LICENSE-DATA.md`.
- Third-party natural images keep their original licences.
