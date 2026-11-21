# Reproducibility Guide

## Runtime

The reported pipeline uses Python 3.13.1, NumPy, OpenCV, PyWavelets,
`reedsolo`, Pillow, matplotlib, `invisible-watermark`, ONNX Runtime, and
scikit-learn. Install the dependencies with:

```bash
python -m pip install -r paper1_model/requirements.txt
```

RivaGAN comparison requires the model assets supported by the installed
`invisible-watermark` package. Third-party model weights are not redistributed.

## Regenerate tables and figures

From the repository root:

```bash
cd paper1_model
python make_paper_tables.py
python make_paper_figures.py
```

The scripts read the canonical results included in this repository and write
tables and figures into `paper1_submission/`.

## Re-run core experiments

```bash
cd paper1_model
python run_experiment.py --full --alpha 28 \
  --output-dir results_full_capture_scan
python run_combined_attacks.py --alpha 28 \
  --output-dir results_combined_alpha28
python run_verification_attribution.py --attack-set all --alpha 28 \
  --output-dir results_verification_attribution_alpha28
```

The fixed embedding/attack seed is `20260910`. Calibration uses split seed
`20261028`.

## Compile the manuscript

```bash
cd paper1_submission/manuscript_latex
pdflatex manuscript.tex
bibtex manuscript
pdflatex manuscript.tex
pdflatex manuscript.tex
```

## Key conventions

- Payload: 128 bits / 16 bytes.
- Error control: CRC-16, RS(32,16), and fourfold repetition.
- Coded watermark: 1024 bits.
- Carrier: Y-channel, one-level Haar DWT and 8 x 8 DCT.
- Coefficient pair: `(3,2)` and `(2,3)`.
- Embedding strength: `alpha=28`.
- Trust thresholds: medium 0.32 and high 0.55.
- Content binding: ORB threshold 0.30; flat-image fallback threshold 0.90.
