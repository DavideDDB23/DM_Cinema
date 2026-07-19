# Enlarged Plot Slides Design

## Goal

Improve the readability of the charts on slides 13 and 14 while preserving the
existing 17-slide structure, visual language, chart order, and source content.

## Layout

### Slide 13: Visual outputs for Q1-Q4

- Keep the four plots in a 2x2 grid.
- Increase each plot's rendered image height from the compact low-viewport value
  of roughly 108 px to about 190-205 px at the 1280x720 presentation size.
- Retain the Q1-Q4 captions directly below their plots.
- Reduce only the plot-grid spacing and slide-specific bottom padding as needed;
  the title, explanatory lead, and existing margins remain visually consistent.

### Slide 14: Window-function outputs for Q5-Q7

- Keep Q5 and Q6 side by side in the top row.
- Center Q7 on the second row and make its card wider than either top-row card so
  its dense table remains legible.
- Render the top-row plot images at about 185-200 px high and Q7 at about
  215-235 px high at the 1280x720 presentation size.
- Retain captions, full axes, legends, and labels without cropping.

## Implementation Boundary

Add slide-specific CSS rules to `slides.html`. Do not edit or regenerate the
source plot PNG files, change analytical data, rewrite slide copy, or add/remove
slides. The PDF export keeps the existing 16:9 page size and final reveal state.

## Verification

1. Render the updated PDF at 1280x720-equivalent resolution.
2. Inspect slides 13 and 14 at full size for clipped axes, labels, legends,
   captions, overlaps, and page overflow.
3. Inspect a complete-deck contact sheet to confirm the other 15 slides are
   unchanged in composition.
4. Verify the PDF still contains 17 nonblank pages at 960x540 pt and that all
   expected slide titles remain extractable.

## Acceptance Criteria

- All seven plots are materially larger than in the current PDF.
- No plot, caption, axis label, legend, or card is clipped.
- Slides 13 and 14 retain clear hierarchy and balanced spacing.
- The final PDF remains a complete, 17-page, 16:9 deck.
