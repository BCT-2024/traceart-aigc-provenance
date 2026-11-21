# Experiments 5.1--5.7 Revision Notes

Date: 2026-11-04

## Section map

1. **5.1 Dataset and implementation:** benchmark composition, metadata,
   software/hardware, seeds, attack families, and decision/metric definitions.
2. **5.2 Image quality:** full-sample PSNR/SSIM distribution and the median-PSNR
   visual example.
3. **5.3 Robustness:** single, compound, and strong propagation simulators.
4. **5.4 Ablation:** carrier, coding, embedding strength, and verification mode.
5. **5.5 Calibration:** image-disjoint split, AUC, held-out thresholds, and the
   finite-sample limitation on empirical zero FPR.
6. **5.6 External comparison:** common 50-image subset, equal-coded-length
   transform baselines, and the non-equal-payload RivaGAN reference.
7. **5.7 Security and failure boundaries:** forged payloads, transplanted
   payloads, flat images, negative sets, physical stress simulators, and the
   end-to-end case.

## Claim--evidence map

| Claim | Evidence | Status |
|---|---|---|
| Embedding preserves high fidelity. | PSNR 39.65 dB; SSIM 0.998980; n=200 | Supported |
| Common edits remain recoverable. | JPEG50/70 and resize 99.5%; crop 92.0%; blur 98.0% | Supported |
| Geometric/compression combinations are harder. | Crop+JPEG70 87.5%; crop+resize+JPEG70 81.5% | Supported |
| DWT-DCT is a tradeoff rather than universally superior. | DCT-only has higher PSNR and comparable single-attack rates; DWT-DCT wins blur+JPEG70, 96.0% vs 29.5% | Supported |
| Both RS and repetition are necessary in the tested carrier. | RS-only crop 0.0%; repeat-only crop 81.5%; RS+repeat crop 92.0% | Supported |
| Calibration transfers across images. | Held-out AUC 0.999833; threshold 0.32 gives TPR 98.0%, FPR 0.32% | Supported |
| Joint verification resists registered-ID forgery. | Watermark-only 20/20; database-only and joint 0/20 | Supported |
| Content binding resists payload transplantation. | Binding off 50/50; binding on 0/50 | Supported |
| Strong physical propagation remains unsolved. | Screen capture 0/200; print-scan 0/200 | Supported, bounded to simulators |

## Evidence-source notes

- Primary robustness values come from the 200-image final `alpha=28` run.
- The low-texture fallback is a targeted stress test with 11 synthetic images,
  not a population estimate.
- RivaGAN carries 32 native bits and cannot be treated as an equal-payload
  baseline.
- AUC confidence intervals use a cluster bootstrap over images (2,000
  resamples), keeping all attack variants of an image together.
- Screen-capture, print-scan, and screenshot are distinct conditions.

## Resolved data consistency issue

The earlier partial run recorded 198/200 accepted salt-and-pepper cases. The
complete re-evaluation of all 3,000 single-attack records accepted 199/200, and
the released-PNG attribution run reproduced 199/200. Across the two datasets,
the salt-and-pepper condition was the only aggregate that changed; its mean BER
was identical. The 199/200 result is now the canonical value used by Table 4,
Fig. 6, Fig. 12, and the manuscript text. The superseded partial run is retained
for provenance but is no longer used as a paper data source.
