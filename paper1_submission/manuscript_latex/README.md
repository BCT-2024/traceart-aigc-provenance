# JVCI CAS LaTeX Working Copy

This directory is a clean working copy based on the Elsevier CAS single-column
template (`cas-sc`, version 2.4).

## Main file

Edit only:

```text
manuscript.tex
```

Do not edit:

- `cas-sc.cls`
- `cas-common.sty`
- `elsarticle-num-names.bst`
- `cas-model2-names.bst`

## Figures

Put the final figure files in `figures/`, for example:

```text
figures/Figure_1.pdf
figures/Figure_2.pdf
```

The manuscript currently contains a safe placeholder if `Figure_1.pdf` is
missing.

## Compile

Run in this order:

```text
pdflatex manuscript
bibtex manuscript
pdflatex manuscript
pdflatex manuscript
```

Or use the build recipe in your LaTeX editor.

## References

`references.bib` contains a small verified starter bibliography. Replace the
placeholder citations and add the final reference set before submission.

## Before submission

- Replace every red `TODO`.
- Replace author names, affiliations, and emails.
- Insert the final figure files.
- Convert `highlights.txt` into the required separate editable file.
- Prepare the Graphical Abstract separately.
- Add CRediT, competing interests, funding, data availability, and AI-use
  declarations.
- Verify that every citation is present in `references.bib`.
