# Verification-stage failure attribution

- Registered images: 200
- Database records: 200
- Attacks: 21
- Observations: 4200
- Alpha: 28; verification: joint; content binding: required (ORB threshold 0.30; flat fallback 0.90)

| Attack | n | CRC | RS | Generation ID | Fields | Content | Accept |
|---|---:|---:|---:|---:|---:|---:|---:|
| Clean | 200 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| JPEG Q90 | 200 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| JPEG Q70 | 200 | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% |
| JPEG Q50 | 200 | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% |
| Resize 0.75x | 200 | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% |
| Resize 1.5x | 200 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Crop 0.9 | 200 | 92.0% | 92.0% | 92.0% | 92.0% | 92.0% | 92.0% |
| Gaussian noise s=3 | 200 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Gaussian noise s=8 | 200 | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% |
| Salt-and-pepper 0.002 | 200 | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% |
| Brightness/contrast | 200 | 96.0% | 96.0% | 96.0% | 96.0% | 96.0% | 96.0% |
| Blur 3x3 | 200 | 98.0% | 98.0% | 98.0% | 98.0% | 98.0% | 98.0% |
| Screenshot sim. | 200 | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% |
| Screen-capture sim. | 200 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Print-scan sim. | 200 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Crop+JPEG | 200 | 87.5% | 87.5% | 87.5% | 87.5% | 87.5% | 87.5% |
| Resize+JPEG | 200 | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% |
| Screenshot+noise | 200 | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% |
| Blur+JPEG | 200 | 96.0% | 96.0% | 96.0% | 96.0% | 96.0% | 96.0% |
| Crop+Resize+JPEG | 200 | 81.5% | 81.5% | 81.5% | 81.5% | 81.5% | 81.5% |
| Social recompression | 200 | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% | 99.5% |

Pass rates are cumulative through each stage. `first_failure_counts.csv` assigns each rejection to the earliest unmet gate.
