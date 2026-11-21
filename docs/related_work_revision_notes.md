# Related Work Revision Notes

Date: 2026-11-04

## Section structure

1. **Transform-domain watermarking:** spread-spectrum, DWT, DCT, differential
   blind extraction, and authentication-oriented adaptive embedding.
2. **Generative and post-hoc AIGC watermarking:** learned post-hoc encoders,
   model-integrated fingerprints, plug-and-play schemes, internet-scale
   deployment, and bit-exact payload recovery.
3. **Provenance and database verification:** C2PA-style manifests, provenance
   evidence, error-corrected retrieval, user-level attribution, perceptual-hash
   registries, and content binding.
4. **Attack and evaluation literature:** removal, evasion, regeneration,
   detector-robustness limits, screen shooting, and print shooting.

## Gap synthesized

Prior work provides strong components, but the reviewed lines optimize different
parts of the problem:

- classical and learned watermarks primarily optimize imperceptibility,
  robustness, or bit recovery;
- model-integrated watermarking is often tied to a particular generator;
- provenance manifests are expressive but can be technically disconnected from
  image evidence;
- perceptual-hash and database methods identify similar content without
  necessarily proving that a recovered generation payload belongs to the query.

The present work combines a structured multi-field payload, DWT-DCT blind
extraction, registry matching, content binding, and calibrated trust in one
platform-controlled verifier.

## Citation audit

- All citations in this section resolve through the LaTeX/BibTeX build.
- The ORB method is cited to its original ICCV paper.
- The C2PA specification is used for manifest structure rather than as a claim
  of pixel-level authenticity.
- RivaGAN is intentionally not discussed as an equal-payload method because its
  role in this paper is the 32-bit external reference.

## Remaining manuscript work

- Introduction
- Abstract and highlights
- Author-specific CRediT, funding, competing-interest, data-availability,
  generative-AI declaration, and acknowledgements fields
- Final two-column float and page-layout pass
