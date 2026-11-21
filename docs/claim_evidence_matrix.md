# Paper 1 Claim--Evidence Matrix

Last audited: 2026-10-29

This document maps each proposed manuscript claim to a reproducible result
artifact. It is the source of truth for the first drafting pass. A number should
not enter the manuscript if its evidence source and sample size cannot be named.

## 1. Frozen primary configuration

| Item | Frozen value | Source |
|---|---|---|
| Positive images | 200 generated with `sd1.5/anything-v5.safetensors` | `paper1_dataset/metadata_all.csv` |
| Other-model AI negatives | 50 generated with `Elysium_Anime_V3.safetensors` | `paper1_dataset/metadata_all.csv` |
| Natural negatives | 50 Wikimedia Commons images | `paper1_dataset/metadata_all.csv` |
| Image size | 512 x 512 for all 300 images | `paper1_dataset/dataset_validation_report.md` |
| Payload | 16 bytes = 128 bits | `paper1_model/payload.py` |
| Error control | RS(32,16), followed by 4-repeat bit coding | `paper1_model/payload.py` |
| Coded watermark length | 32 bytes x 8 x 4 = 1024 bits | `paper1_model/payload.py` |
| Carrier | DWT-DCT on the Y channel | `paper1_model/watermark.py` |
| DWT | One-level Haar transform | `paper1_model/watermark.py` |
| DCT | 8 x 8 blocks; coefficient pairs (3,2) and (2,3) | `paper1_model/watermark.py` |
| Embedding rule | Differential coefficient update with `alpha=28` | `paper1_model/watermark.py` |
| Block selection | Keyed permutation, seed 20260910 | `paper1_model/watermark.py` |
| Content binding | ORB hard gate at 0.30; flat-image fallback at 0.90 | `paper1_model/verify.py` |
| Trust levels | high >= 0.55; medium >= 0.32; low otherwise | `paper1_model/verify.py` |

The DWT-DCT carrier and ECC configuration are method facts. The alpha value,
content-binding threshold, trust thresholds, and flat-image fallback are
configuration choices that must be justified in the Method section.

## 2. Claim status

- `READY`: evidence is complete enough for the stated bounded claim.
- `CONDITIONAL`: evidence exists, but a caveat or additional analysis is
  required.
- `BLOCKED`: do not write the stronger claim until the experiment is rerun or
  the current evidence is replaced.

## 3. Main claim matrix

| ID | Claim suitable for the manuscript | Evidence | Key result | Scope and limitation | Status |
|---|---|---|---|---|---|
| C1 | A fixed-length structured payload can identify a registered generation event. | Code and clean test | 200/200 successful; mean BER 0.001675 | The 48-bit generation field is a truncated hash, not a globally collision-free identifier. | READY |
| C2 | Watermark embedding preserves high image fidelity. | `results_full_capture_scan/quality_metrics.csv` | Mean PSNR 39.65 dB; mean SSIM 0.998980; PSNR range 30.28--44.08 dB | The method is evaluated only on 512 x 512 images. | READY |
| C3 | Verification remains effective under common single post-processing operations. | `results_full_capture_scan/summary.json` | Clean 100%; JPEG50 99.5%; crop 92%; blur 98%; screenshot simulation 99.5% | Attacks are deterministic simulators, not platform production traffic. | READY |
| C4 | Compound transformations reduce performance but remain mostly recoverable. | `results_combined_alpha28/summary.json` | Crop+JPEG 87.5%; crop+resize+JPEG 81.5% | Crop and combined geometric processing are the hardest cases. | READY |
| C5 | Database-backed joint verification rejects format-valid but unregistered identifiers. | `results_verification_ablation/summary.json` | Watermark-only 20/20 accepted; DB-only 0/20; joint 0/20 | Only 20 synthetic forged payloads were tested. | READY |
| C6 | Content binding prevents a valid payload copied from a different image from being accepted. | `results_copy_attack_alpha28/summary.json` | At `alpha=28`: binding off 50/50 joint acceptances; binding on 0/50 | Fifty paired donor-target trials, not the full 50 x 50 Cartesian set. | READY |
| C7 | The trust score provides strong separation on images not used for threshold calibration. | `results_threshold_calibration_split_alpha28/summary.json` | Held-out AUC 0.999833; calibration AUC 0.998693 | The image-disjoint split contains 100 positive and 50 negative images on each side. | READY |
| C8 | A conservative flat-image fallback suppresses copy acceptance on texture-poor images. | `results_flat_sensitivity_alpha28/summary.json` | At `alpha=28`, threshold 0.90 gives TPR 75.0% and FPR 0%; default 0.30 gives TPR 95.45% and FPR 100% | Only 11 synthetic/low-texture images and 44 positive cases. | CONDITIONAL |
| C9 | The method is competitive with same-length transform-domain baselines under several edits. | `results_external_baselines/external_report.md` and `matched_comparison.csv` | On the common 50-image subset: Ours crop 94%, combo 88%; DWT-DCT-SVD crop 0%, combo 0% | Comparison uses 50 images; RivaGAN has only 32 payload bits and is not payload-matched. | READY |
| C10 | Realistic screen-capture and print-scan propagation remain unsolved. | `results_full_capture_scan/summary.json` | Screen 0/200; print-scan 0/200 | These are strong simulations, not physical camera/print experiments; geometric synchronization is needed. | READY |
| C11 | No false positives were observed in the clean negative set. | `results_full_capture_scan/negative_fpr_detail.csv` | 0/100 | Zero observed events do not prove zero population FPR; 0/100 has limited resolution. | CONDITIONAL |
| C12 | The selected carrier and coding configuration provides a balanced robustness-quality tradeoff under the final setting. | `results_ablation_full_alpha28/ablation_summary.csv`; `results_combined_dct_only_alpha28/summary.json` | Full n=200: DWT-DCT crop 92%, blur+JPEG 96%; DCT-only crop 92%, blur+JPEG 29.5%; RS+repeat crop 92% vs repeat-only 81.5% | DCT-only has higher PSNR and comparable single-attack crop performance; DWT-DCT should not be described as globally superior. | READY |
| C13 | The dataset covers one controlled generation platform, one other model, and natural images. | `paper1_dataset/dataset_validation_report.md` | 200 + 50 + 50 images; zero duplicate SHA-256 values | It is a controlled benchmark, not evidence of universal cross-platform generalization. | READY |
| C14 | The long-payload method preserves visual appearance in representative landscape and portrait examples. | `results_visual_evidence/multimethod_examples.csv` | Landscape: 41.10 dB / 0.9994; portrait: 39.80 dB / 0.9994 | Two median-PSNR examples are visual evidence, not the full-sample quality statistic. | READY |
| C15 | End-to-end verification accepts clean, JPEG, and cropped versions of a registered image while rejecting the tested print-scan case. | `results_visual_evidence/case_gallery.csv` | Clean/JPEG/crop accepted with high trust; print-scan rejected with low trust | Representative single-image case; population rates remain in the main experiment. | READY |
| C16 | In the registered-positive stress set, first failure occurs during payload recovery rather than in later registry or content checks. | `results_verification_attribution_alpha28/stage_detail.csv` | 3,693 accepted and 507 rejected of 4,200; all 507 first failed payload integrity | The claim covers 200 registered images and the 21 specified deterministic conditions; it is not a negative-image false-positive analysis. | READY |

## 4. Exact main results

### 4.1 Image quality and clean identification

| Quantity | Value | N |
|---|---:|---:|
| Mean PSNR | 39.6522 dB | 200 |
| Median PSNR | 39.8685 dB | 200 |
| 5th--95th percentile PSNR | 36.5382--42.2299 dB | 200 |
| Minimum PSNR | 30.2774 dB | 200 |
| Mean SSIM | 0.998980 | 200 |
| Median SSIM | 0.999158 | 200 |
| Minimum SSIM | 0.995417 | 200 |
| Clean verification success | 200/200 | 200 |
| Clean mean BER | 0.001675 | 200 |

Source: `paper1_model/results_full_capture_scan/`.

### 4.2 Single-operation robustness

| Operation | Success | Mean BER | Trust high/medium/low |
|---|---:|---:|---:|
| Clean | 100.0% | 0.001675 | 200 / 0 / 0 |
| JPEG Q90 | 100.0% | 0.002217 | 200 / 0 / 0 |
| JPEG Q70 | 99.5% | 0.004229 | 199 / 0 / 1 |
| JPEG Q50 | 99.5% | 0.008174 | 199 / 0 / 1 |
| Resize 0.75 | 99.5% | 0.006377 | 199 / 0 / 1 |
| Resize 1.5 | 100.0% | 0.001909 | 200 / 0 / 0 |
| Center crop 0.9 | 92.0% | 0.085010 | 184 / 6 / 10 |
| Gaussian noise sigma=3 | 100.0% | 0.002031 | 200 / 0 / 0 |
| Gaussian noise sigma=8 | 99.5% | 0.003306 | 199 / 0 / 1 |
| Salt-and-pepper 0.002 | 99.5% | 0.035093 | 199 / 0 / 1 |
| Brightness/contrast | 96.0% | 0.023823 | 192 / 2 / 6 |
| Gaussian blur 3 x 3 | 98.0% | 0.033726 | 196 / 1 / 3 |
| Screenshot simulation | 99.5% | 0.010542 | 199 / 0 / 1 |

Each row contains 200 test positives. Source:
`paper1_model/results_full_capture_scan/summary.json`.

### 4.3 Compound-operation robustness

| Operation | Success | Mean BER | N |
|---|---:|---:|---:|
| Crop 0.9 + JPEG70 | 87.5% | 0.091821 | 200 |
| Resize 0.75 + JPEG70 | 99.5% | 0.010908 | 200 |
| Screenshot + noise | 99.5% | 0.011733 | 200 |
| Blur + JPEG70 | 96.0% | 0.040776 | 200 |
| Crop 0.9 + resize 0.8 + JPEG70 | 81.5% | 0.095576 | 200 |
| Social recompression | 99.5% | 0.008223 | 200 |

Source: `paper1_model/results_combined_alpha28/summary.json`.

### 4.4 Physical-propagation stress tests

| Simulator | Success | Mean BER | Trust high/medium/low | N |
|---|---:|---:|---:|---:|
| Realistic screen capture | 0.0% | 0.5353 | 0 / 0 / 200 | 200 |
| Print-scan | 0.0% | 0.4948 | 0 / 0 / 200 | 200 |

Source: `paper1_model/results_full_capture_scan/summary.json`.

These rows must be reported as failures of the current carrier under geometric
desynchronization. They do not support claims of screen-shooting or print-scan
robustness.

## 5. Verification and security evidence

### 5.1 Format-valid forged payloads

Twenty negative images received validly formatted payloads whose generation IDs
were absent from the database.

| Verification mode | Accepted | Mean score |
|---|---:|---:|
| Watermark only | 20/20 | 1.0000 |
| Database only | 0/20 | 0.3792 |
| Joint | 0/20 | 0.6396 |

Source: `paper1_model/results_verification_ablation/summary.json`.

### 5.2 Copied-watermark attack

| Binding | Mode | Accepted | N |
|---|---|---:|---:|
| Off | Joint | 50/50 | 50 |
| On | Joint | 0/50 | 50 |

The final-configuration run is stored in
`paper1_model/results_copy_attack_alpha28/`. It uses `alpha=28`, a seed of
20260910, and the same trust thresholds as the main experiment. The experiment
contains 50 unique paired donor-target trials, with one donor cycled onto each
negative target; it is not the full 50 x 50 Cartesian attack matrix. The
current `experiment_status.md` also mentions a 380-positive/400-copy threshold
calibration, but those calibration records cannot be reconstructed from the
listed result files. Do not cite those two counts until their source is
recovered.

### 5.3 Extremely flat images

| Content-binding policy | TPR | FPR | N |
|---|---:|---:|---:|
| Default threshold 0.30 | 95.45% | 100% | 44 positive, 11 copy |
| Flat fallback threshold 0.90 | 75.00% | 0% | 44 positive, 11 copy |

Source: `paper1_model/results_flat_sensitivity_alpha28/summary.json`. The
experiment uses 11 synthetic low-texture images and `alpha=28`. Because the
sample is small, treat this result as a targeted stress test rather than a
general estimate for flat images.

### 5.4 Verification-stage failure attribution

The final `alpha=28` watermarked carriers were replayed through all 21 single
and compound conditions with joint verification and content binding enabled.
Each of the 200 registered images contributes one observation to every attack
row, yielding 4,200 trajectories.

| Outcome or first failing stage | Count | Share |
|---|---:|---:|
| Accepted | 3,693 | 87.93% |
| Payload integrity | 507 | 12.07% |
| Registry mismatch | 0 | 0.00% |
| Content binding | 0 | 0.00% |
| Trust threshold | 0 | 0.00% |

Every rejected trajectory failed before a valid CRC and RS codeword was
recovered. Among the 3,693 trajectories that passed payload integrity, all
also matched the correct generation, contained the complete expected field
set, passed content binding, and reached at least medium trust. The largest
losses were crop0.9 (8.0%), crop+JPEG70 (12.5%),
crop+resize0.8+JPEG70 (18.5%), and both physical stress simulators (100%).

Source: `paper1_model/results_verification_attribution_alpha28/`.

## 6. External baseline comparison

The original report compared the full 200-image Ours result with 50-image
baseline results. The report generator has been corrected to use the common
50-image subset for all methods.

| Method | Payload bits | N | PSNR | SSIM | JPEG50 | Crop | Blur | Screenshot | Crop+resize+JPEG |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Ours, matched subset | 1024 coded bits | 50 | 40.33 | 0.999302 | 100% | 94% | 100% | 100% | 88% |
| External DWT-DCT | 1024 coded bits | 50 | 37.76 | 0.999999 | 0% | 0% | 0% | 0% | 0% |
| External DWT-DCT-SVD | 1024 coded bits | 50 | 37.68 | 1.000000 | 72% | 0% | 100% | 100% | 0% |
| RivaGAN | 32 native bits | 50 | 40.48 | 0.999918 | 100% | 100% | 100% | 100% | 100% |

Source: `paper1_model/results_external_baselines/matched_comparison.csv`.

The defensible conclusion is:

- Both our method and external DWT-DCT-SVD carry a 1024-bit coded payload.
- Our joint verification remains effective after cropping and the compound
  attack, while external DWT-DCT-SVD fails those conditions.
- RivaGAN is a short-payload robustness reference only. Its 32-bit payload
  cannot contain our 128-bit structured payload plus FEC.

## 7. Image-disjoint threshold calibration

The manuscript should use the image-disjoint calibration result rather than the
old pooled ROC:

- calibration: 100 positive and 50 negative images;
- held-out evaluation: the other 100 positive and 50 negative images;
- all attack variants of a given image remain in one split;
- positive strata are balanced across the eight image categories;
- natural and other-model negatives each contribute 25 images to each side.

Each side contains 1900 positive and 950 negative score observations. The
cluster bootstrap resamples images and keeps all attacks of a sampled image
together.

| Metric | Calibration | Held-out |
|---|---:|---:|
| AUC | 0.998693 | 0.999833 |
| Cluster-bootstrap 95% CI | 0.996138--0.999970 | 0.999570--1.000000 |

Threshold transfer:

| Target FPR | Threshold | Calibration FPR | Calibration TPR | Held-out FPR | Held-out TPR |
|---:|---:|---:|---:|---:|---:|
| 0.020 | 0.174844 | 2.11% | 99.79% | 2.84% | 99.95% |
| 0.010 | 0.310156 | 1.16% | 97.95% | 0.53% | 98.00% |
| 0.005 | 0.310156 | 1.16% | 97.95% | 0.53% | 98.00% |
| 0.001 | 0.331250 | 0.11% | 97.16% | 0.11% | 97.47% |

The operational thresholds remain high >= 0.55 and medium >= 0.32. On held-out
data they produce:

| Threshold | FPR | TPR |
|---|---:|---:|
| High >= 0.55 | 0.00% | 97.32% |
| Medium >= 0.32 | 0.32% | 98.00% |

The current thresholds can therefore be described as conservative operational
cutoffs. The target-FPR curve and the deployed thresholds are different
objects and should be labelled accordingly. The manuscript should report the
held-out observed rates rather than an exact deployment probability of zero.

## 8. Allowed and prohibited claims

Allowed:

- "The payload is structured and bound to a registered generation event in a
  platform-controlled setting."
- "Joint verification rejects the tested format-valid but unregistered
  payloads."
- "The method preserves high image fidelity on the reviewed 512 x 512
  benchmark."
- "The current carrier fails under strong screen-capture and print-scan
  simulations, motivating geometric synchronization."

Prohibited without new experiments:

- "The method verifies any AIGC image from any platform."
- "The system is robust to real screen capture or print-scan."
- "DWT-DCT clearly outperforms DCT-only."
- "RivaGAN is weaker at equal payload; RivaGAN is less capable for long
  structured records."
- "The empirical false-positive probability is exactly zero."
- "All 2500 donor-target copy combinations were tested."
- "The flat-image fallback is validated for the general population of flat
  images."

## 9. P0 actions completed

1. The paired copy/transplant test was rerun at `alpha=28`.
2. The flat-image sensitivity test was rerun at `alpha=28`.
3. Calibration and evaluation were split by image, and cluster-bootstrap AUC
   confidence intervals were computed.
4. The 0.55/0.32 thresholds are retained as conservative operational cutoffs
   and reported against the target-FPR calibration curve.
5. The external comparison uses the common 50-image subset.
6. Final evidence artifacts and checksums are indexed in
   `evidence_audit_20261028.md`.

## 10. Evidence artifact index

| Purpose | Canonical artifact |
|---|---|
| Primary configuration status | `paper1_model/experiment_status.md` |
| Dataset manifest | `paper1_dataset/metadata_all.csv` |
| Dataset validation | `paper1_dataset/dataset_validation_report.md` |
| Main quality and single attacks | `paper1_model/results_full_capture_scan/summary.json` |
| Additional physical stress tests | `paper1_model/results_full_capture_scan/summary.json` |
| Compound attacks | `paper1_model/results_combined_alpha28/summary.json` |
| Carrier/coding/alpha ablations | `paper1_model/results_ablation_full_alpha28/ablation_summary.csv` |
| Forged-payload verification | `paper1_model/results_verification_ablation/summary.json` |
| Copy attack at final alpha | `paper1_model/results_copy_attack_alpha28/summary.json` |
| Flat-image sensitivity at final alpha | `paper1_model/results_flat_sensitivity_alpha28/summary.json` |
| Image-disjoint ROC and operating points | `paper1_model/results_threshold_calibration_split_alpha28/` |
| Matched external comparison | `paper1_model/results_external_baselines/matched_comparison.csv` |
| Multi-method visual comparison | `paper1_model/results_visual_evidence/multimethod_examples.csv` |
| End-to-end case gallery | `paper1_model/results_visual_evidence/case_gallery.csv` |
| Verification-stage failure attribution | `paper1_model/results_verification_attribution_alpha28/` |

The checksums in `evidence_audit_20261028.md` identify the data state at the
end of this audit.
