# Problem Formulation and Method Revision Notes

Date: 2026-11-04

## Section map

### Problem Formulation and Scope

1. **Application scenario:** defines the platform-controlled setting, the
   generation event, the verification inputs, the returned decision, and the
   non-universal scope.
2. **Structured provenance payload:** gives the full 128-bit layout and explains
   that hashed fields are registry projections rather than globally unique IDs.
3. **Threat model:** separates registered positives, unregistered negatives,
   forged payloads, transplanted payloads, and damaged carriers; states the
   trusted-registry assumption and excluded cryptographic-authenticity cases.

### Proposed Method

1. **Overview:** maps generation-time creation and verification-time evidence
   combination to Fig. 1.
2. **Payload encoding:** defines CRC-16, shortened RS(32,16), fourfold
   repetition, decoding, and integrity acceptance.
3. **DWT-DCT embedding:** defines the luminance transform, 8 x 8 block layout,
   coefficient difference, embedding update, blind extraction, permutation,
   and final configuration.
4. **Database verification:** defines registry fields, the five-component field
   score, average-hash similarity, and candidate ranking.
5. **Content binding:** defines ORB matching and the flat-image fallback.
6. **Trust scoring:** defines the weighted score, three trust levels, hard
   acceptance conditions, and the distinction between trust and acceptance.
7. **Alignment search:** defines the 14 spatial hypotheses, candidate selection,
   early exit, and diagnostic output.

## Formula-to-code audit

| Quantity in manuscript | Implemented value | Source |
|---|---|---|
| Payload length | 128 bits | `payload.py` |
| CRC input | 112 bits, CRC-CCITT, initial `0xFFFF` | `payload.py` |
| RS code | shortened RS(32,16), up to 8 byte errors | `payload.py` |
| Repetition | four copies per coded bit | `payload.py` |
| Coded length | 1024 bits | `payload.py` |
| DWT | Haar, level 1 | `watermark.py` |
| DCT blocks | 8 x 8 in the LL band | `watermark.py` |
| Coefficient pair | `(3,2)` and `(2,3)` | `watermark.py` |
| Embedding update | move pair by half of the target gap | `watermark.py` |
| Embedding strength | `alpha=28` | frozen configuration |
| Block permutation seed | 20260910 | frozen configuration |
| Candidate weights | `0.45 F + 0.25 H + 0.30 G` | `verify.py` |
| ORB threshold | 0.30 | `verify.py` |
| Flat fallback | 0.90 | `verify.py` |
| Trust score | `0.25 CRC + 0.20 RS + 0.30 F + 0.15 H + 0.10 G` | `verify.py` |
| Trust levels | high at 0.55, medium at 0.32 | `verify.py` |
| Alignment candidates | 14 for 512 x 512 inputs | `verify.py` |

## Figure consistency correction

The previous Fig. 1 treated field matching as a hard rejection gate and labelled
every rejection as low trust. The implementation instead uses four hard
conditions:

1. CRC and RS success;
2. exact generation-ID match;
3. content-binding success;
4. non-low trust.

Field consistency contributes to the trust score but is not an independent hard
gate. Format-valid unregistered payloads can therefore retain medium or high
diagnostic scores while being rejected. Fig. 1 and its caption were revised to
match this behaviour.

## Remaining inputs before final submission

- Reflow figure and table floats when converting the single-column working
  manuscript to the final two-column JVCI layout.
- Keep dataset generation, software versions, hardware, and attack
  implementation details in the Experiments section rather than duplicating
  them here.

The ORB algorithm is now cited with Rublee et al., *ORB: An Efficient
Alternative to SIFT or SURF*, DOI `10.1109/ICCV.2011.6126544`.
