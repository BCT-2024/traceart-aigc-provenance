# Superseded Partial Result

This directory is retained for provenance but is no longer the canonical
source for the manuscript's robustness results.

A complete re-evaluation including the two physical-propagation simulators is
stored in `../results_full_capture_scan/`. Across the 3,000 single-attack
records, the only aggregate difference is salt-and-pepper acceptance:

- this partial run: 198/200 = 99.0%;
- canonical complete run: 199/200 = 99.5%.

The mean BER for that attack is identical in both runs. The one borderline
sample was accepted when the final released PNG was re-evaluated with the final
ORB threshold logic.

Use `../results_full_capture_scan/` for Tables 4 and 8, Figs. 5, 6, 8, and 9,
and the clean-negative result.
