# Discussion and Conclusion Revision Notes

Date: 2026-11-04

## Paragraph map

### 6.1 Interpretation

1. Joint verification is an event-consistency test rather than a watermark
   detector; forged and transplanted-payload tests isolate the registry and
   content checks.
2. Failure attribution shows that the registered-positive stress cases are
   limited by payload recovery before later database stages are exercised.
3. Cropping and strong acquisition simulators are interpreted as geometric
   desynchronization and resampling failures, without claiming a single causal
   component.
4. Carrier, coding, and calibration results are interpreted as tradeoffs rather
   than universal superiority.

### 6.2 Limitations

1. Platform-controlled scope, single-platform data regime, and absence of
   arbitrary cross-platform attribution.
2. Simulator-based attack coverage, small flat-image stress set, 50-image
   external comparison, and the RivaGAN payload-parity limitation.
3. Exhaustive registry search, truncated identifiers, trusted registry, absent
   cryptographic signature/key management, and threshold drift.

### 6.3 Deployment Implications

1. Generation-time registration and post-generation embedding.
2. Structured audit output, versioned thresholds, and manual review for failed
   recovery or low trust.
3. Signed records, protected keys, content-dependent authentication, and
   physical geometric registration as additional safeguards.

### 7. Conclusion

1. Restate the structured-record and joint-verification contribution.
2. Summarize decisive bounded evidence from the controlled benchmark.
3. State why physical/geometric synchronization is the next concrete extension.

## Claim-evidence map

| Claim | Evidence | Status |
|---|---|---|
| Registry and content checks reject different attack classes. | Forged payload joint 0/20; copied payload binding-on 0/50 | Supported |
| Registered-positive failures are dominated by payload recovery. | 507/507 first failures at payload integrity | Supported |
| Crop remains the hardest standard geometry operation. | Crop0.9 92.0%; crop+resize+JPEG70 81.5% | Supported |
| DWT-DCT is not globally superior to DCT-only. | DCT-only has higher PSNR; DWT-DCT is stronger on blur+JPEG70 | Supported |
| The trust score is auxiliary to hard acceptance gates. | Calibration AUC and forged high-score rejections | Supported |
| Physical screen/print robustness is not established. | 0/200 for each simulator | Supported, bounded to simulators |

## Remaining manuscript work

- Introduction and related work
- Abstract and highlights
- Author-specific CRediT, competing-interest, funding, data-availability,
  generative-AI declaration, and acknowledgements fields
- Final two-column float/layout pass
