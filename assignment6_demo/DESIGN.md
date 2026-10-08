---
name: Cortis
description: Vietnamese fashion discovery in a cool-stone photographic showroom.
colors:
  wine: "#60283b"
  wine-dark: "#482030"
  stone: "#f6f5f3"
  paper: "#fff"
  ink: "#211c22"
  clay: "#eddfda"
  muted: "#665f65"
  line: "#d9d3d3"
  tray: "#eeece9"
  tab-selected: "#f8f1ee"
  secondary-hover: "#f4e8e4"
  invalid: "#a72f41"
  error-text: "#922438"
  error-ink: "#7e263a"
  error-line: "#d5b0b8"
  error-paper: "#fcf3f3"
typography:
  display:
    fontFamily: "Be Vietnam Pro, sans-serif"
    fontSize: "clamp(32px, 4.5vw, 58px)"
    fontWeight: 500
    lineHeight: 1.25
    letterSpacing: "-.04em"
  headline:
    fontFamily: "Be Vietnam Pro, sans-serif"
    fontSize: "clamp(25px, 2.8vw, 35px)"
    fontWeight: 500
    lineHeight: 1.25
    letterSpacing: "-.03em"
  title:
    fontFamily: "Be Vietnam Pro, sans-serif"
    fontSize: "18px"
    fontWeight: 500
    lineHeight: 1.25
  body:
    fontFamily: "Be Vietnam Pro, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "Be Vietnam Pro, sans-serif"
    fontSize: "14px"
    fontWeight: 500
    lineHeight: 1.5
rounded:
  flat: "0"
  control: "3px"
  round: "50%"
spacing:
  gap-sm: "8px"
  gap-md: "12px"
  mobile-panel: "16px"
  control-inline: "20px"
  panel: "22px"
  tablet-gutter: "32px"
  desktop-gutter: "48px"
components:
  button-primary:
    backgroundColor: "{colors.wine}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    padding: "12px 20px"
  button-primary-hover:
    backgroundColor: "{colors.wine-dark}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.wine}"
    rounded: "{rounded.control}"
    padding: "12px 20px"
  button-secondary-hover:
    backgroundColor: "{colors.secondary-hover}"
  text-link:
    textColor: "{colors.wine}"
    padding: "6px 0"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  navigation:
    textColor: "{colors.muted}"
  navigation-active:
    textColor: "{colors.wine}"
  mode-tab:
    textColor: "{colors.muted}"
    padding: "12px 8px"
  mode-tab-selected:
    backgroundColor: "{colors.tab-selected}"
    textColor: "{colors.wine}"
  stock-tag:
    backgroundColor: "{colors.stone}"
    textColor: "{colors.muted}"
    padding: "4px 8px"
  product-tray:
    backgroundColor: "{colors.tray}"
    rounded: "{rounded.flat}"
---

# Design System: Cortis
## Overview

**Creative North Star: "The Searchable Showroom"**

Cortis presents fashion objects as samples on a cool-stone showroom wall. Oxblood marks actions and selection; restrained Vietnamese typography, fine rules and real photographs keep the objects and the search task legible. Flat photographic trays are the recurring material signature across search, product details, orders and image credits.

This is a scan of the implemented code-first world, committed in the first body comment of frontend/index.html (FORM seed e0088335), rather than an approved image comp. The desktop search page pairs a task desk with a framed Converse sample; that composition belongs to this surface and is not a compulsory layout for every route.

**Key Characteristics:**

- Cool stone, ink, oxblood and pale clay.
- Be Vietnam Pro with Vietnamese diacritics and restrained weight changes.
- Flat trays, fine rules and clearly selected controls.
- Real internet photographs with local provenance records.

Evidence: frontend/src/styles.css, main.tsx, App.tsx, ui.tsx and pages/SearchPage.tsx; data/image_sources.json records 60 product photographs and their source/license/hash metadata. Supplied final captures live in artifacts/frontend/screenshots/final. The finish reviewer cleared its single material fix with disposition: ship; QUALITY BAR and approved-comp fidelity remain unavailable. This document is descriptive authority for the implemented system, not a new quality or license audit.

## Colors

### Primary

Oxblood (`wine`) marks primary actions, active navigation, selected tabs, focus and understated brand details. Deeper oxblood (`wine-dark`) is the primary-button hover state. Pale clay (`clay`) supports specimen framing, selected text and draft-context notices; it is a supporting tint rather than a competing accent. The frontmatter values are normative and retain the code's color notation.

### Neutral

Cool stone (`stone`) is the page field; white (`paper`) holds inputs and the search desk. Ink (`ink`) carries main text; muted stone-ink (`muted`) carries descriptions and metadata. Fine grey (`line`) separates sections and frames fields; the slightly darker tray (`tray`) sets photographs apart from the field. Selected-tab and secondary-hover tints support control state. Error tokens retain the existing red-ink, pale-error-paper and fine-error-line roles rather than introducing a second brand accent.

**The Action Accent Rule.** Use oxblood to indicate an action, selection or focused object; retain neutral fields around it.

## Typography

**Display Font:** Be Vietnam Pro, sans-serif fallback.
**Body Font:** Be Vietnam Pro, sans-serif fallback.

Local Fontsource imports in frontend/src/main.tsx load Vietnamese and Latin subsets at 400, 500, 600 and 700. The normal body is 400, headings and primary controls are 500, and the wordmark is 600. There is no separate serif or monospace family.

### Hierarchy

- **Display:** the frontmatter display role applies to the main task heading. Product-detail headings use their observed smaller clamp (30px-42px).
- **Headline:** the frontmatter headline role applies to section headings.
- **Title:** the base third-level heading is the frontmatter title role; product names use a denser catalogue setting (16px, weight 500, line-height 1.5).
- **Body:** the frontmatter body role establishes the readable Vietnamese base.
- **Label:** the frontmatter label role describes the shared button setting. Field labels are 14px/500; secondary metadata steps down through 13px, 12px and 11px by context.

Prices, scores, counters and request timings use tabular numerals. Heading tracking is tight; body copy retains normal tracking. Do not turn all labels into uppercase.

## Layout

The shared header and page containers cap at 1360px with centered margins and desktop side gutters from the spacing tokens. Desktop catalogue layout is a 220px filter rail plus a flexible results area, separated by 40px. The catalogue uses three columns, with 30px row gaps and 22px column gaps. Detail pages use a separate two-column composition (1.1fr/1fr, 64px gap); credits use two columns, while orders remain text/table focused.

At the 1100px maximum-width breakpoint, gutters become 32px, the rail becomes 190px, and products reduce to two columns. At 800px, the search desk becomes full width, catalogue filters become an expandable control above results, and detail becomes one column. At 540px, gutters become 20px, navigation wraps beneath the wordmark, the search action fills the desk width, and catalogue cards remain two columns with a 14px gap. The footer has a separate 1340px gutter adjustment. Body minimum width is 320px.

Use the recurring 8/12/16/20/22/32/48 spacing steps where their roles fit; this is an extracted vocabulary, not an arithmetic spacing scale. The desktop search hero's large gap and specimen frame belong to the search surface. Other routes should retain the world without copying that composition.

## Elevation & Depth

No box shadows are declared in the incumbent stylesheet. Depth comes from stone-to-paper and stone-to-tray tonal changes, fine borders, photograph framing and whitespace. The circular open affordance sits on white over the photograph without a drop shadow. Search, processing, credit and order surfaces use rules and tonal separation rather than floating panels.

**The Flat Tray Rule.** Keep catalogue and detail photographs on flat neutral trays; use borders and tonal contrast to separate neighboring surfaces.

Motion is limited: product images scale to 1.035 on hover over 0.3s ease; the desktop specimen reveals through a 0.65s clipping animation; busy icons spin in 1s linear loops. Reduced-motion CSS reduces animation and transition duration and disables smooth scrolling. The static capture packet does not verify animation behavior.

## Shapes

Containers and photographic trays are square-cornered. Buttons and text fields soften only their corners using the control radius. Thin rules and field borders are 1px; the selected-tab indicator is 2px. Round photographic open affordances use the round radius. The showroom specimen has small corner marks, but these are a signature of that frame rather than a universal container decoration.

Keyboard focus uses a 3px oxblood outline with 4px offset. Interactive controls generally provide 44px targets, buttons and fields at least 46px. Unavailable notices are plain text without a colored side stripe.

## Components

### Buttons

Primary and outlined secondary buttons are precise, compact controls using the frontmatter assignments, a 1px oxblood border, minimum 46px height, 14px/500 type and 10px icon gap. Primary hover deepens both fill and border; secondary hover uses the pale warm tint. Disabled buttons have 0.55 opacity and a not-allowed cursor. Text links remain underlined with a 4px underline offset and a minimum 44px target. Icon buttons retain a minimum 44px square target. Focus follows the global outline.

### Inputs / Fields

White fields use ink text, fine grey borders and the control radius. Textareas are at least 92px tall and resize vertically. Visible labels precede fields; counters and recovery text stay adjacent. Invalid fields use the existing invalid border token and field-error text. Checkbox and range accents use oxblood. Image upload uses a dashed frame with a focus-within outline, real file labels and an object-contain preview; it is not a simulated upload control.

### Navigation

A compact lowercase wordmark anchors the shared header. Three text/icon links identify search, orders and credits. Muted default links become oxblood on hover; the active route receives oxblood text and a 1px bottom rule. On narrow screens the links remain visible in a second row. Icons use restrained outlines; sidecar samples embed SVG paths directly.

### Search Mode Tabs

Four equal segments switch description, voice, image and combined modes. Muted defaults become oxblood on the selected pale tint, with an inset bottom indicator. Tabs retain aria-selected and keyboard arrow/Home/End behavior in the app; changing mode cancels work and preserves each mode's draft. The sidecar depicts states and does not implement the React behavior.

### Cards / Containers

Product cards are open photographic trays with text below; they have no enclosing card border or shadow. Square images use object-fit: contain; metadata precedes a medium-weight name, color, price and stock. A round open affordance sits in the lower-right corner. Rank and out-of-stock tags are compact, square, stone-filled overlays. Detail and credits reuse contain photography; only the search specimen uses an intentional cover crop. Source metadata and an image-error recovery pattern accompany the real photographs.

### Status / Recovery

Detail stock labels use a pale-clay rectangle; out-of-stock labels use a muted neutral variant. Error panels have a pale-red field, fine full border, alert icon and retry link. Unavailable voice notices remain plain muted text with recovery choices. Loading uses flat skeleton blocks or a spinner; empty results use a simple ruled panel and recovery action.

## Do's and Don'ts

### Do:

- **Do** use the existing CSS custom properties for shared surfaces and accents.
- **Do** preserve Vietnamese labels, visible keyboard focus and readable recovery copy.
- **Do** retain real-photo credits and the image fallback/retry pattern.
- **Do** use contain for catalogue and detail photography; preserve the intentional cover crop in the search specimen.
- **Do** distinguish demo prices, inventory and orders from commercial claims.

### Don't:

- **Don't** replace product photography with generated, synthetic or CSS-drawn objects.
- **Don't** add lifted cards or decorative shadows to the flat tray system.
- **Don't** impose the search page specimen-and-desk composition on other routes.
- **Don't** remove unavailable-state recovery or the manual-transcript simulation label.
- **Don't** add the removed thick colored side stripe to unavailable notices.
