# Full-Scale Ablation Under the Final Configuration

## Protocol

- Positives: 200
- Other-model AI negatives: 50
- Natural negatives: 50
- Carrier, coding, and verification-mode configurations: alpha=28
- Alpha sweep: 8, 12, 16, 20, 24, and 28
- Attack evaluation: the 15 standard single-attack conditions

All rows were produced from the same evaluation command and attack list.

## Carrier ablation

| Configuration | PSNR | SSIM | Clean | JPEG50 | Crop | Noise8 | Blur | Screenshot | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| dwt_dct | 39.65 | 0.9990 | 100.0 | 99.5 | 92.0 | 99.5 | 98.0 | 99.5 | 0.00 |
| dwt_only | 41.36 | 0.9994 | 100.0 | 98.0 | 39.0 | 100.0 | 87.0 | 99.5 | 0.00 |
| dct_only | 43.46 | 0.9996 | 100.0 | 99.5 | 92.0 | 100.0 | 99.5 | 100.0 | 0.00 |
| lsb | 52.36 | 1.0000 | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.00 |

## Coding ablation

| Configuration | PSNR | SSIM | Clean | JPEG50 | Crop | Noise8 | Blur | Screenshot | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rs_repeat | 39.65 | 0.9990 | 100.0 | 99.5 | 92.0 | 99.5 | 98.0 | 99.5 | 0.00 |
| rs_only | 44.22 | 0.9997 | 99.5 | 95.0 | 0.0 | 99.0 | 68.0 | 94.5 | 0.00 |
| repeat_only | 39.62 | 0.9990 | 99.5 | 99.0 | 81.5 | 99.5 | 97.0 | 98.5 | 0.00 |
| raw | 45.92 | 0.9998 | 92.0 | 52.5 | 0.0 | 82.0 | 11.0 | 47.5 | 0.00 |

## Verification-mode ablation

| Configuration | PSNR | SSIM | Clean | JPEG50 | Crop | Noise8 | Blur | Screenshot | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| db_only | 39.65 | 0.9990 | 100.0 | 99.5 | 92.0 | 99.5 | 98.0 | 99.5 | 0.00 |
| joint | 39.65 | 0.9990 | 100.0 | 99.5 | 92.0 | 99.5 | 98.0 | 99.5 | 0.00 |
| watermark_only | 39.65 | 0.9990 | 100.0 | 99.5 | 92.0 | 99.5 | 98.0 | 99.5 | 0.00 |

## Embedding-strength ablation

| Configuration | PSNR | SSIM | Clean | JPEG50 | Crop | Noise8 | Blur | Screenshot | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| alpha_8 | 40.72 | 0.9992 | 99.5 | 1.0 | 61.0 | 2.0 | 23.0 | 60.0 | 0.00 |
| alpha_12 | 40.59 | 0.9992 | 99.5 | 44.5 | 82.5 | 98.5 | 64.5 | 92.0 | 0.00 |
| alpha_16 | 40.40 | 0.9991 | 99.5 | 98.5 | 84.5 | 99.5 | 83.0 | 97.0 | 0.00 |
| alpha_20 | 40.21 | 0.9991 | 100.0 | 99.5 | 85.5 | 99.5 | 91.5 | 98.5 | 0.00 |
| alpha_24 | 39.96 | 0.9990 | 100.0 | 99.5 | 89.0 | 99.5 | 96.5 | 99.5 | 0.00 |
| alpha_28 | 39.65 | 0.9990 | 100.0 | 99.5 | 92.0 | 99.5 | 98.0 | 99.5 | 0.00 |

## Combined-Attack Carrier Check

| Attack | DCT-only | DWT-DCT |
|---|---:|---:|
| Crop+JPEG70 | 90.0% | 87.5% |
| Resize0.75+JPEG70 | 100.0% | 99.5% |
| Screenshot+noise | 100.0% | 99.5% |
| Blur+JPEG70 | 29.5% | 96.0% |
| Crop0.9+Resize0.8+JPEG70 | 87.5% | 81.5% |
| Social recompression | 99.5% | 99.5% |

## Key observations

- DCT-only attains higher PSNR and comparable single-attack crop
  accuracy, so DWT-DCT must not be described as globally superior.
- DWT-DCT remains materially stronger for blur+JPEG (96.0% versus
  29.5% for DCT-only), which supports retaining it for compound
  transformations.
- RS+repeat improves crop success over repeat-only (92.0% versus
  81.5%) with only a 0.03 dB PSNR difference.
- Alpha=28 improves crop and blur success over alpha=24 while reducing
  mean PSNR by approximately 0.31 dB.

The table values are empirical rates from their respective configurations.
Carrier and coding differences must be interpreted with both success and
fidelity in view; a higher PSNR alone does not establish a better carrier.
