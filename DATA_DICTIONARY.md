# Data Dictionary

## Dataset manifest

Primary file: `paper1_dataset/metadata_all.csv`

| Field | Meaning |
|---|---|
| `generation_id` | Internal generation identifier |
| `filename` | Image filename |
| `relative_path` | Image path relative to `paper1_dataset/` |
| `platform_id` | Platform or source namespace |
| `model_name` | Generator/checkpoint name |
| `model_version` | Recorded model-version string |
| `prompt` | Generation prompt, where applicable |
| `prompt_sha256` | SHA-256 digest of the prompt |
| `negative_prompt` | Negative prompt, where applicable |
| `seed` | Generation seed |
| `sampler` | Sampling algorithm |
| `steps` | Sampling steps |
| `cfg_scale` | Classifier-free guidance scale |
| `width`, `height` | Image dimensions |
| `created_at` | Generation timestamp |
| `sha256` | Source-image SHA-256 digest |
| `category` | Prompt/content category |
| `is_platform_sample` | Platform-positive marker |
| `sample_group` | `positive`, `negative_ai`, or `natural` |
| `source` | Image source |
| `source_url` | Source page for third-party images |
| `source_file_title` | Original source title |
| `artist` | Original creator attribution |
| `license` | Original licence |
| `license_url` | Licence reference |
| `attribution_required` | Attribution requirement flag |
| `image_description` | Human-readable image description |
| `resize_mode` | Preprocessing/resizing mode |
| `resize_params_file` | Associated resize-parameter file |

## Main result tables

| File | Meaning |
|---|---|
| `results_full_capture_scan/quality_metrics.csv` | Per-image PSNR and SSIM |
| `results_full_capture_scan/robustness_detail.csv` | Canonical per-image/single-attack decisions |
| `results_full_capture_scan/negative_fpr_detail.csv` | Clean-negative decisions |
| `results_combined_alpha28/combined_detail.csv` | Per-image compound-attack decisions |
| `results_ablation_full_alpha28/ablation_summary.csv` | Carrier, coding, and alpha configurations |
| `results_threshold_calibration_split_alpha28/threshold_transfer.csv` | Target-FPR calibration transfer |
| `results_threshold_calibration_split_alpha28/split_assignments.csv` | Image-disjoint split membership |
| `results_verification_attribution_alpha28/stage_detail.csv` | Per-sample verification-stage evidence |
| `results_copy_attack_alpha28/copy_attack_detail.csv` | Paired donor-target copy attempts |
| `results_flat_sensitivity_alpha28/*.csv` | Flat-image fallback stress test |
| `results_external_baselines/external_detail.csv` | External-method per-image results |
| `results_visual_evidence/multimethod_examples.csv` | Multi-method image examples |
| `results_visual_evidence/case_gallery.csv` | End-to-end case-gallery evidence |

## Verification fields

- `crc_ok`: CRC-16 verification result.
- `rs_success`: Reed-Solomon decoding result.
- `generation_match`: exact projected-generation match.
- `field_score`: fraction of matching registry fields.
- `hash_score`: average-hash similarity.
- `content_binding_score`: ORB or flat-signature fallback score.
- `content_binding_ok`: hard content-binding decision.
- `score`: joint trust score.
- `trust`: high, medium, or low trust.
- `success`: final joint acceptance decision.
- `alignment`: selected alignment hypothesis.
- `first_failure_stage`: earliest unmet verification stage.

## Figure source data

The figures are generated from the canonical CSV/JSON files in
`paper1_model/results_*`. Table CSVs in `paper1_submission/paper_tables/` map
directly to manuscript Tables 1-8.
