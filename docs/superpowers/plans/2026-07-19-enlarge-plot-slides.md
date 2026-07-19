# Enlarged Plot Slides Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all seven charts on slides 13 and 14 materially larger while preserving the 17-slide, 16:9 deck.

**Architecture:** Add narrowly scoped CSS overrides for the two visual-output slides inside the existing low-height desktop media query, because the PDF is rendered at a 1280x720 viewport. Regenerate the stable PDF artifact with Playwright, then validate the two edited pages visually and the full document structurally with Poppler and pypdf.

**Tech Stack:** HTML/CSS, Playwright with headless Chrome, Poppler (`pdfinfo`, `pdftoppm`), Python with Pillow and pypdf.

---

## File Map

- Modify: `slides.html` - slide-specific sizing and grid rules for slides 13 and 14.
- Modify: `output/pdf/cinema_analytics_slides.pdf` - regenerated final deck.
- Create temporarily: `tmp/pdfs/*.png` - rendered review pages and contact sheet; remove after verification.

### Task 1: Establish the Current Plot-Size Baseline

**Files:**
- Read: `slides.html:395-460`
- Read: `slides.html:959-1125`

- [ ] **Step 1: Measure the current plot image boxes at the PDF viewport**

Run:

```bash
NODE_PATH='/Users/davide/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules' \
/Users/davide/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node <<'NODE'
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.goto('file://' + path.resolve('slides.html'), { waitUntil: 'load' });
  const result = await page.evaluate(() => ({
    q1q4: [...document.querySelectorAll('[data-od-id="slide-olap-visuals-1"] .plot-card img')].map((img) => img.getBoundingClientRect().height),
    q5q7: [...document.querySelectorAll('[data-od-id="slide-olap-visuals-2"] .plot-card img')].map((img) => img.getBoundingClientRect().height)
  }));
  console.log(JSON.stringify(result));
  await browser.close();
})();
NODE
```

Expected before the change: all seven image boxes are approximately 108 px tall,
which fails the new minimums of 190 px for Q1-Q6 and 220 px for Q7.

### Task 2: Add the Slide-Specific Layout Overrides

**Files:**
- Modify: `slides.html:1105-1125`

- [ ] **Step 1: Add the enlarged plot rules at the end of the existing `@media (min-width: 1001px) and (max-height: 800px)` block**

Add the following CSS after the current compact `.plot-card p` rule and before the media query closes:

```css
      [data-od-id="slide-olap-visuals-1"],
      [data-od-id="slide-olap-visuals-2"] {
        padding-bottom: 34px;
      }
      [data-od-id="slide-olap-visuals-1"] .topline,
      [data-od-id="slide-olap-visuals-2"] .topline {
        margin-bottom: 6px;
      }
      [data-od-id="slide-olap-visuals-1"] .plot-grid,
      [data-od-id="slide-olap-visuals-2"] .plot-grid {
        gap: 7px;
        margin-top: 0;
      }
      [data-od-id="slide-olap-visuals-1"] .plot-card img {
        height: 198px;
      }
      [data-od-id="slide-olap-visuals-2"] .plot-grid.q5-7 {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        align-items: stretch;
      }
      [data-od-id="slide-olap-visuals-2"] .plot-card {
        width: auto;
      }
      [data-od-id="slide-olap-visuals-2"] .plot-card img {
        height: 195px;
      }
      [data-od-id="slide-olap-visuals-2"] [data-od-id="plot-q7-top-films"] {
        grid-column: 1 / -1;
        width: 76%;
        justify-self: center;
      }
      [data-od-id="slide-olap-visuals-2"] [data-od-id="plot-q7-top-films"] img {
        height: 225px;
      }
```

- [ ] **Step 2: Re-run the viewport measurement**

Run the Task 1 command again.

Expected:

```text
{"q1q4":[198,198,198,198],"q5q7":[195,195,225]}
```

- [ ] **Step 3: Check the source edit**

Run:

```bash
git diff --check -- slides.html
```

Expected: exit status 0 with no output.

### Task 3: Regenerate the PDF with Complete Reveal Content

**Files:**
- Modify: `output/pdf/cinema_analytics_slides.pdf`
- Create temporarily: `tmp/pdfs/slide-13.png`
- Create temporarily: `tmp/pdfs/slide-14.png`

- [ ] **Step 1: Create the output and temporary directories**

Run:

```bash
mkdir -p output/pdf tmp/pdfs
```

- [ ] **Step 2: Render the deck with Playwright**

Run:

```bash
NODE_PATH='/Users/davide/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules' \
/Users/davide/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node <<'NODE'
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args: ['--allow-file-access-from-files', '--disable-gpu']
  });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1
  });
  await page.goto('file://' + path.resolve('slides.html'), { waitUntil: 'load' });
  await page.emulateMedia({ media: 'screen', reducedMotion: 'reduce' });
  await page.evaluate(async () => {
    await Promise.all([...document.images].map((img) => img.complete
      ? Promise.resolve()
      : new Promise((resolve) => {
          img.addEventListener('load', resolve, { once: true });
          img.addEventListener('error', resolve, { once: true });
        })));
    if (document.fonts?.ready) await document.fonts.ready;
  });
  await page.addStyleTag({ content: `
    @page { size: 13.333333in 7.5in; margin: 0; }
    html, body {
      width: 1280px !important;
      height: auto !important;
      margin: 0 !important;
      overflow: visible !important;
      background: #fff !important;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }
    #deck-track {
      display: block !important;
      width: 1280px !important;
      height: auto !important;
      transform: none !important;
    }
    .slide {
      display: flex !important;
      width: 1280px !important;
      min-width: 1280px !important;
      max-width: 1280px !important;
      height: 720px !important;
      min-height: 720px !important;
      max-height: 720px !important;
      flex: none !important;
      overflow: hidden !important;
      break-after: page !important;
      page-break-after: always !important;
    }
    .slide:last-child {
      break-after: auto !important;
      page-break-after: auto !important;
    }
    .step-track, .panel-track, .box-track {
      display: flex !important;
      width: 100% !important;
      transform: none !important;
      transition: none !important;
    }
    .panel-compact { display: none !important; }
    .panel-revealed {
      display: block !important;
      flex: 1 1 100% !important;
      width: 100% !important;
      max-width: 100% !important;
    }
    #nav-dots, .lightbox, .speaker-notes { display: none !important; }
    .zoom-frame, .zoom-frame:hover, .plot-card:hover, .img-box:hover {
      transform: none !important;
      box-shadow: none !important;
    }
  ` });
  await page.pdf({
    path: path.resolve('output/pdf/cinema_analytics_slides.pdf'),
    width: '13.333333in',
    height: '7.5in',
    margin: { top: '0', right: '0', bottom: '0', left: '0' },
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: false,
    tagged: true
  });
  await browser.close();
})();
NODE
```

Expected output file:

```text
output/pdf/cinema_analytics_slides.pdf
```

- [ ] **Step 3: Confirm PDF structure before visual review**

Run:

```bash
pdfinfo output/pdf/cinema_analytics_slides.pdf | rg 'Title|Tagged|Pages|Page size|File size'
```

Expected: title `Cinema Analytics Data Warehouse`, tagged `yes`, 17 pages, and
page size `960 x 540 pts`.

### Task 4: Perform Visual and Structural Verification

**Files:**
- Read: `output/pdf/cinema_analytics_slides.pdf`
- Create temporarily: `tmp/pdfs/review-slide-*.png`

- [ ] **Step 1: Render slides 13 and 14 at full review resolution**

Run:

```bash
pdftoppm -f 13 -l 14 -png -r 96 \
  output/pdf/cinema_analytics_slides.pdf tmp/pdfs/review-slide
```

Expected: two 1280x720 PNG files.

- [ ] **Step 2: Inspect both pages visually**

Confirm that Q1-Q4 fill the 2x2 grid, Q5-Q6 fill the top row, Q7 is centered and
wider below, and no plot, legend, axis, caption, or card is clipped or overlaps.

- [ ] **Step 3: Verify every page is structurally complete**

Run:

```bash
/Users/davide/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 <<'PY'
from pypdf import PdfReader

reader = PdfReader('output/pdf/cinema_analytics_slides.pdf')
assert len(reader.pages) == 17
assert all(float(page.mediabox.width) == 960 for page in reader.pages)
assert all(float(page.mediabox.height) == 540 for page in reader.pages)
assert all((page.extract_text() or '').strip() for page in reader.pages)
print('pdf_structure=PASS pages=17 page_size=960x540pt text=17/17')
PY
```

Expected: all assertions pass.

- [ ] **Step 4: Remove temporary review artifacts**

Run:

```bash
find tmp/pdfs -maxdepth 1 -type f -name 'review-slide-*.png' -delete
```

Expected: final PDF remains in `output/pdf/`; temporary review PNGs are removed.

- [ ] **Step 5: Report the completed artifact**

Provide the clickable path to `output/pdf/cinema_analytics_slides.pdf` and state
the verified page count, page size, and enlarged chart layout.
