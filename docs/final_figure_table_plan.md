# Paper 1 Final Figure and Table Plan

Last updated: 2026-10-29

## 1. Design rules

- Every result figure must use a canonical evidence directory listed in
  `claim_evidence_matrix.md`.
- Schematic figures use vector PDF or SVG. Raster result figures use at least
  600 dpi for the working copy and are exported as PDF for LaTeX.
- All fonts should be Arial/Helvetica-compatible, with a final body-text size
  of at least 8 pt after scaling to the manuscript width.
- Use one colorblind-safe palette across the paper.
- Use `booktabs` rules in tables and no vertical rules or cell shading.
- Every table and figure must be cited in the body before it appears.
- Do not place the Graphical Abstract in the numbered figure sequence.

## 2. Recommended manuscript figures

| Final ID | Working file | Core message | Source | Status |
|---|---|---|---|---|
| Fig. 1 | `fig1_framework.pdf` | Flowchart from generation-time registration to hard-gated verification with diagnostic trust | New schematic | Complete |
| Fig. 2 | `fig2_payload_ecc.pdf` | 128-bit payload, CRC, RS, repetition, and 1024-bit coded stream | `payload.py` | Complete |
| Fig. 3 | `fig3_dwt_dct.pdf` | DWT-DCT embedding and blind extraction details | `watermark.py` | Complete |
| Fig. 4 | `fig4_verification.pdf` | Candidate matching, content binding, and trust scoring | `verify.py` | Complete |
| Fig. 5 | `fig5_watermark_example.pdf` | Visual quality and x10 amplified residual | Final `alpha=28` example | Complete |
| Fig. 6 | `fig6_robustness.pdf` | Single and compound attack success/BER | `results_full_capture_scan/`; `results_combined_alpha28/` | Complete |
| Fig. 7 | `fig7_ablation.pdf` | Full-scale carrier, coding, alpha, and combined-attack tradeoffs | `results_ablation_full_alpha28/`; `results_combined_dct_only_alpha28/` | Complete |
| Fig. 8 | `fig8_calibration.pdf` | Calibration and held-out ROC, score distributions, and operating thresholds | `results_threshold_calibration_split_alpha28/` | Complete |
| Fig. 9 | `fig9_external.pdf` | Matched 50-image external comparison | `matched_comparison.csv` | Complete |
| Fig. 10 | `fig10_multimethod_visual.pdf` | Multi-method visibility comparison with enlarged patches | `results_visual_evidence/multimethod_examples.csv` | Complete |
| Fig. 11 | `fig11_case_gallery.pdf` | End-to-end clean/JPEG/crop/print-scan case gallery | `results_visual_evidence/case_gallery.csv` | Complete |
| Fig. 12 | `fig12_failure_attribution.pdf` | Verification-stage pass rates and earliest unmet gate | `results_verification_attribution_alpha28/` | Complete |
| Graphical Abstract | `graphical_abstract.pdf` and high-resolution TIFF | One-panel summary of payload--embedding--matching--trust | Final method | Complete |

### Figure-specific requirements

**Fig. 1. Overall framework.**
Use the reference paper's flowchart language: black-outline rectangular
processes, diamond decisions, orthogonal arrows, explicit Yes/No branches, and
terminal rejection/trust outcomes. Show the per-block embedding loop, optical
propagation, integrity check, registry check, and content-binding check.

**Fig. 2. Payload and coding.**
Show bit allocation as a proportional horizontal bar:

| Field | Bits |
|---|---:|
| Version | 4 |
| Platform hash | 8 |
| Generation hash | 48 |
| Model-version hash | 8 |
| Timestamp | 24 |
| Content hash | 16 |
| Reserved | 4 |
| CRC-16 | 16 |
| Total | 128 |

Then show RS(32,16) and 4-repeat expansion to 1024 coded bits. Clearly mark the
16-bit content-hash field as a compact projection, not a full SHA-256 digest.

**Fig. 3. DWT-DCT embedding.**
Show Y-channel extraction, one-level Haar DWT, 8 x 8 blocks in the
approximation band, coefficient pair (3,2)/(2,3), differential update, inverse
transform, and blind extraction. State `alpha=28` and the keyed block
permutation.

**Fig. 4. Verification.**
Show decoded fields entering the registry, candidate ranking, ORB content
binding/flat fallback, joint score, and trust bands. Use 0.45/0.25/0.30 for
candidate ranking and 0.25/0.20/0.30/0.15/0.10 for the joint score only if the
final implementation remains unchanged.

**Fig. 5. Visual example.**
Use original, watermarked, absolute difference, and x10 difference panels. Pick
the displayed image using a fixed rule rather than an unusually favorable
sample. Include PSNR and SSIM in the caption.

**Fig. 6. Robustness.**
Recommended 2 x 2 panel:

- (a) single-attack success rate;
- (b) single-attack mean BER;
- (c) compound-attack success rate;
- (d) trust-level composition for crop, blur, and the hardest compound case.

Include screen-capture and print-scan stress-test failures as a separately
labelled group or move them to the security/negative-results table. Do not
merge them with the weaker `screenshot` simulation without explanation.

**Fig. 7. Ablation.**
Use four panels: carrier, coding, alpha/quality tradeoff, and a combined-attack
check between DCT-only and DWT-DCT. All uses 200 positives and alpha=28.
DCT-only has higher PSNR and equal single-attack crop success, while DWT-DCT
has much higher blur+JPEG success (96.0% versus 29.5%).

**Fig. 8. Calibration.**
Panel (a): calibration and held-out ROC curves. Panel (b): held-out positive
and negative score distributions with the selected operating thresholds.
State that the split is by image and that all attacks of an image stay in one
split.

**Fig. 9. External comparison.**
Use only the common 50-image subset from `matched_comparison.csv`. Show success
rates for DWT-DCT, DWT-DCT-SVD, Ours, and RivaGAN. Put the payload length in
the legend or a second row; do not plot RivaGAN as if it had the same payload.

**Fig. 10. Multi-method visual comparison.**
Show landscape and portrait examples across Original, Ours, DWT-DCT,
DWT-DCT-SVD, and RivaGAN. Preserve method labels and PSNR/SSIM values. The
enlarged patches are diagnostic crops, not evidence of watermark localization.

**Fig. 11. End-to-end verification gallery.**
Use the same registered image under clean, JPEG70, crop0.9, and print-scan.
Report decoded and expected identifier prefixes, content-binding score, and
trust level. The print-scan panel is an intentional failure case.

**Fig. 12. Verification failure attribution.**
Use all 200 registered images under the 21 final single and compound
conditions. Panel (a) shows cumulative pass rates after CRC, RS decoding,
generation-ID matching, exact field consistency, content binding, and final
acceptance. Panel (b) assigns every rejection to its earliest unmet gate.
Retain screen-capture and print-scan simulators as failures rather than
merging them with the weaker screenshot simulation.

## 3. Recommended manuscript tables

| Final ID | Table | Required columns | Source | Status |
|---|---|---|---|---|
| Table 1 | Payload field allocation | Field, bits, purpose | `payload.py` | Complete |
| Table 2 | Embedding and verification parameters | Category, symbol, value | code and frozen configuration | Complete |
| Table 3 | Dataset composition | Group, generator/source, count, role | `metadata_all.csv` | Complete |
| Table 4 | Robustness results | Operation, N, success, mean BER | main and combined summaries | Complete |
| Table 5 | Ablation results | Group, PSNR, SSIM, key attack success | `ablation_summary.csv` | Complete |
| Table 6 | External comparison | Method, payload bits, N, PSNR/SSIM, selected attacks | `matched_comparison.csv` | Complete |
| Table 7 | Forgery, copy, and flat-image security | Test, condition, outcome, interpretation | forged-payload, final-alpha copy, final-alpha flat | Complete |
| Table 8 | Calibration, negatives, and physical stress | Test, condition, outcome, interpretation | held-out thresholds, clean negatives, capture/scan | Complete |

### Table content decisions

**Table 1. Payload field allocation.**
Use decimal bit lengths and state the total is 16 bytes. Explain that several
fields are truncated hashes.

**Table 2. Hyperparameters.**
Include alpha, Haar level, DCT block size, coefficient pair, repeat factor,
seed, ORB threshold, flat fallback threshold, and high/medium trust thresholds.
This table prevents the Method and Experiments sections from disagreeing.

**Table 3. Dataset composition.**
Report the 200 platform positives, 50 other-model negatives, and 50 natural
negatives. Add one footnote for the Wikimedia license mix and one for the fixed
512 x 512 processing.

**Table 4. Robustness.**
Rows should include all single and compound operations used in the final
method. Separate `screenshot simulation` from `real_screen_capture simulator`.
Report percentages with one decimal and BER with three significant digits.
Trust composition is shown in Fig. 6 rather than repeated in this table.

**Table 5. Ablation.**
Use a configuration column and group rows by carrier, coding, and alpha.
Report n=200 and alpha=28 for carrier/coding comparisons.

**Table 6. External baselines.**
Use N=50 for every row. Include payload length in bits. Mark RivaGAN as a
short-payload reference rather than an equal-payload baseline.

**Table 7. Forgery and content-binding security.**
Include:

- forged payload: watermark-only 20/20 accepted; joint 0/20;
- copied watermark: binding off 50/50; binding on 0/50;
- flat images: 0.30 gives TPR 95.45%/FPR 100%; 0.90 gives TPR 75%/FPR 0%;

**Table 8. Calibration, negatives, and physical stress.**
Include:

- clean negatives: 0/100 false positives;
- screen/print stress tests: 0/200 each.

Do not merge these into a single accuracy number because they answer different
questions. Held-out trust thresholds are also listed here.

## 4. Figure and table captions to reuse

Draft captions:

- **Fig. 1.** Overview of the platform-controlled structured provenance
  framework, from generation-time registration to graded verification.
- **Fig. 2.** Structured 128-bit payload layout and its expansion through
  CRC-16, RS(32,16), and fourfold repetition coding.
- **Fig. 3.** DWT-DCT differential embedding and blind extraction on the
  luminance channel.
- **Fig. 4.** Database candidate matching, content binding, and graded trust
  scoring.
- **Fig. 5.** Representative watermarked image and amplified residual.
- **Fig. 6.** Verification success and bit error rate under single and compound
  image transformations.
- **Fig. 7.** Carrier, coding, and embedding-strength ablations.
- **Fig. 8.** ROC and trust-score distributions with selected operating points.
- **Fig. 9.** Payload-matched comparison with external watermarking methods on
  the common 50-image subset.
- **Fig. 10.** Visual comparison of watermarked landscape and portrait images;
  insets enlarge central patches.
- **Fig. 11.** End-to-end verification of one registered image under successful
  and failed propagation conditions.
- **Fig. 12.** Verification-stage pass rates and first-failure attribution
  across single and compound attacks.

## 5. Existing files and reuse decisions

| Existing file | Decision |
|---|---|
| `results_threshold_calibration_split_alpha28/roc_calibration.png` | Reuse data; regenerate in final style |
| `results_threshold_calibration_split_alpha28/roc_held_out.png` | Reuse data; regenerate in final style |
| `results_threshold_calibration_split_alpha28/held_out_score_distribution.png` | Reuse data; regenerate in final style |
| `results_external_baselines/external_ber_comparison.png` | Redraw from matched comparison |
| `results_flat_sensitivity_alpha28/threshold_sensitivity.png` | Keep for final-alpha analysis; not a main figure unless flat policy enters the method |
| `results_full_capture_scan/figures/robustness_success.png` | Data are current; redesign for publication |
| `results_full_capture_scan/figures/robustness_ber.png` | Data are current; redesign for publication |
| `results_full/figures/*` | Do not use; generated before the final alpha report |
| `results_full/visual_examples/*` | Rebuild from a documented `alpha=28` sample |
| `results_ablation/figures/*` | Archived exploratory output; use the full-scale Fig. 7 instead |

## 6. Submission artwork

The Graphical Abstract is separate from the numbered figure sequence. It should
show four steps in one horizontal strip:

1. generation event and metadata;
2. structured payload and ECC;
3. DWT-DCT embedding;
4. database verification and high/medium/low output.

Use an aspect ratio close to 2:1 or wider, at least 1328 px on the longest side,
and check legibility at 13 cm width. Export both an editable source and a
high-resolution submission image. Do not reuse a result plot as the Graphical
Abstract.

## 7. Production order

1. Freeze the final method decisions and evidence snapshot.
2. Generate Tables 1--8 from scripted CSV inputs.
3. Create Figs. 1--4 as vector schematics.
4. Regenerate Figs. 5--9 from canonical results with one shared style.
5. Write titles and captions before prose so each result has a defined role.
6. Insert figure/table references into the manuscript.
7. Build the Graphical Abstract only after the final method figure is approved.

## 8. Acceptance checklist

- [ ] Every figure has a cited purpose in the text.
- [ ] Every table has the same N and configuration as its evidence source.
- [ ] `alpha=28` appears consistently.
- [ ] DCT-only is not described as inferior without evidence.
- [ ] RivaGAN's 32-bit payload is visible in table and caption.
- [ ] `screenshot` and `real_screen_capture` are named differently.
- [ ] No result figure is copied from an old run.
- [ ] TIFF/PDF/vector requirements are checked against JVCI guidelines.
- [ ] Graphical Abstract remains separate from numbered figures.
