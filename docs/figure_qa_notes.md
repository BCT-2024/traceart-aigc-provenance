# Paper 1 Figure QA Notes

Date: 2026-11-04

Backend: Python / matplotlib.

All figures were rendered from `paper1_model/make_paper_figures.py` and exported
as editable SVG, editable-text PDF, 600-dpi PNG, and 600-dpi TIFF.

## Source preflight

`validate_figure.py --strict` result:

- 20 checks passed;
- 0 warnings;
- 0 failures;
- verdict: READY FOR VISUAL QA.

## PDF text audit

`audit_pdf_text.py --min-pt 5` passed for all thirteen PDFs.

| Figure | Minimum detected font size |
|---|---:|
| Fig. 1 | 6.0 pt |
| Fig. 2 | 6.0 pt |
| Fig. 3 | 6.1 pt |
| Fig. 4 | 5.9 pt |
| Fig. 5 | 7.0 pt |
| Fig. 6 | 5.6 pt |
| Fig. 7 | 5.2 pt |
| Fig. 8 | 5.6 pt |
| Fig. 9 | 5.5 pt |
| Fig. 10 | 6.5 pt |
| Fig. 11 | 5.8 pt |
| Fig. 12 | 5.2 pt |
| Graphical Abstract | 7.0 pt |

## Embedded raster audit

PDF/SVG exports use 1200 dpi for embedded raster content, while PNG and TIFF
remain at 600 dpi. The following figures intentionally contain raster elements:

- Fig. 1: input-image thumbnail;
- Fig. 3: coefficient map retained as a raster panel;
- Fig. 5: original, watermarked, residual, and enlarged image panels;
- Fig. 10: multi-method image panels and enlarged patches;
- Fig. 11: end-to-end image cases;
- Fig. 12: heatmap retained as a raster panel.

`pdfimages -list` reports 1200 ppi for each embedded raster object in the
individual figure PDFs. After placement in the manuscript, effective raster
resolution remains 1048--1333 ppi. Figs. 2, 4, 6, 7, 8, and 9 contain no
embedded raster image and remain fully vector.

## Figure contracts

| Figure | Core conclusion | Archetype | Evidence |
|---|---|---|---|
| Fig. 1 | Verification requires payload integrity, an exact registered-generation match, content binding, and non-low trust; field consistency contributes to the diagnostic score. | vertical decision flowchart | Method design |
| Fig. 2 | The 128-bit record is expanded deterministically to a 1024-bit watermark. | quantitative schematic | `payload.py` |
| Fig. 3 | The Y-channel DWT-DCT differential rule supports blind extraction. | schematic-led composite | `watermark.py` |
| Fig. 4 | Candidate matching and content binding produce a graded trust score. | schematic-led composite | `verify.py` |
| Fig. 5 | Embedding is visually subtle while retaining non-zero residual structure. | image plate | Median-PSNR image from the canonical final `alpha=28` run |
| Fig. 6 | Verification is strong under common edits but fails under physical propagation simulators. | quantitative grid | Main and compound summaries |
| Fig. 7 | Carrier, coding, and strength choices expose a quality-robustness tradeoff. | quantitative grid | `ablation_summary.csv` |
| Fig. 8 | Trust scores separate classes on held-out images, and an operating point can be calibrated without image leakage. | quantitative grid | Image-disjoint split result |
| Fig. 9 | The proposed long-payload method is competitive with transform baselines and is distinct from the short-payload RivaGAN reference. | quantitative grid | `matched_comparison.csv` |
| Fig. 10 | Multi-method watermarks preserve visual appearance on landscape and portrait examples. | image plate | `multimethod_examples.csv` |
| Fig. 11 | The same registered image is accepted under clean/JPEG/crop but rejected after print-scan. | image plate + quant | `case_gallery.csv` |
| Fig. 12 | Rejections in the registered-positive benchmark arise at payload recovery rather than at later database stages. | quantitative grid | `results_verification_attribution_alpha28/` |
| Graphical Abstract | Structured provenance plus database/content checks provides a graded verification workflow. | schematic strip | Final method |

## Panel-level visual audit

| Figure | Labels and collisions | Data/uncertainty | Result |
|---|---|---|---|
| Fig. 1 | Uses black-outline rectangles, decision diamonds, orthogonal arrows, a block-processing loop, and a unified rejection route. Rejection preserves diagnostic evidence and is not conflated with a low trust score. | No quantitative claim. | Pass |
| Fig. 2 | Version/reserved labels rotated with anchored alignment; no collisions. | Exact bit allocation and coding lengths. | Pass |
| Fig. 3 | Full 8 x 8 coefficient map identifies C(3,2) and C(2,3); arrows remain clear. | Exact implementation values. | Pass |
| Fig. 4 | Hard ORB/flat gate and weighted trust score are separate stages. | Exact implementation weights and thresholds. | Pass |
| Fig. 5 | Centre patches are enlarged; panel letters remain outside dark images. | Full 200-image PSNR/SSIM distributions are included. | Pass |
| Fig. 6 | Panel titles carry panel letters; trust legend is outside the bars. | Wilson 95% intervals on all success proportions; n=200 shown in title. | Pass |
| Fig. 7 | Four panels include full-scale carrier/coding, alpha tradeoff, and the combined-attack carrier check. | n=200; Wilson 95% intervals; DCT-only and DWT-DCT tradeoff shown explicitly. | Pass |
| Fig. 8 | ROC and distributions are separated; legend does not cover curves. | Cluster-bootstrap AUC intervals are printed in the legend. | Pass |
| Fig. 9 | Success and BER panels share method colours; four-item legend is below both axes. | Wilson 95% intervals on success, n=50. | Pass |
| Fig. 10 | Ten panels use stable method order and enlarged centre crops. | PSNR/SSIM values come from the displayed images. | Pass |
| Fig. 11 | Four cases share one source image; metadata sits below each image. | Shows recovered ID, C2 score, and trust; print-scan failure retained. | Pass |
| Fig. 12 | Twenty-one aligned attack rows separate single and compound groups; every heat-map cell is directly labelled. | n=200 per row; cumulative stages are monotonic; accepted and first-failure categories are mutually exclusive. | Pass |
| Graphical Abstract | Wide horizontal flow; no collision at 13 cm reference width. | No quantitative claim. | Pass |

## Source-data integrity

- Raw result directories were not modified by figure generation.
- Fig. 6 uses the final `alpha=28` single/compound results.
- Fig. 8 uses the image-disjoint split; calibration and held-out images do not
  overlap.
- Fig. 9 uses the common 50-image subset for every method.
- Fig. 10 is generated from the median-PSNR landscape and portrait examples.
- Fig. 11 uses a fixed image that succeeds under clean, JPEG, and crop, while
  retaining the print-scan failure.
- Fig. 12 reuses the final `alpha=28` carriers and reruns the joint verifier;
  missing content-binding fields were not inferred from older result files.
- PDF/SVG exports now preserve 1200-dpi raster content; Fig. 3 and Fig. 12 are
  intentionally retained as high-resolution raster heatmaps.
- Fig. 7 now uses 200 positives with alpha=28 for carrier and coding
  comparisons. The DCT-only baseline is stronger on several single attacks;
  DWT-DCT's advantage appears under blur+JPEG.

## Known presentation caveats

- The result panels report empirical percentages from deterministic attack
  simulators. Wilson intervals quantify finite-sample uncertainty but do not
  represent variation across unseen platforms or acquisition devices.
- Fig. 6 separates the screenshot simulation from the stronger realistic
  screen-capture simulator.
- Fig. 12 reports only the failures observed in the five specified cumulative
  stages; post-payload registry, content-binding, and trust failures were zero
  in this registered-positive benchmark and are not synthesized for visual
  balance.
- Fig. 9 identifies RivaGAN as a 32-bit reference in the legend; it is not an
  equal-payload competitor.
