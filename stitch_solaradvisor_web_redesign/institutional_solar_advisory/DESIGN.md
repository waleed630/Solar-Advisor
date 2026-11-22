---
name: Institutional Solar Advisory
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#45464d'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#006c4a'
  on-secondary: '#ffffff'
  secondary-container: '#82f5c1'
  on-secondary-container: '#00714e'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#2f1500'
  on-tertiary-container: '#c76c00'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#85f8c4'
  secondary-fixed-dim: '#68dba9'
  on-secondary-fixed: '#002114'
  on-secondary-fixed-variant: '#005137'
  tertiary-fixed: '#ffdcc3'
  tertiary-fixed-dim: '#ffb77d'
  on-tertiary-fixed: '#2f1500'
  on-tertiary-fixed-variant: '#6e3900'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.015em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  numeric-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.02em
  numeric-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 30px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  margin: 2rem
  gutter-mobile: 1rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system establishes an institutional-grade, highly authoritative digital experience tailored for residential solar investment feasibility. The audience consists of discerning Pakistani homeowners navigating complex capital expenditure decisions, rising LESCO tariffs, net-metering regulations, and ROI projections. 

The aesthetic merges modern cleantech precision with the sobriety of private wealth management. It avoids gimmicky decorative tropes in favor of structural clarity, high-contrast data presentation, crisp borders, and calm, confident spatial distribution. Every interface element must reinforce engineering legitimacy, fiscal accuracy, and transparency.

## Colors

The palette leverages high-contrast structural tones paired with targeted energy accents:

- **Primary (`#0F172A`)**: Deep Navy anchors top-level navigation, structural headers, metric titles, and core interface chrome, projecting sovereign institutional authority.
- **Secondary (`#059669`)**: Energy Jade represents positive fiscal returns, generation output, net-metering export credits, and green certification benchmarks.
- **Tertiary (`#D97706`)**: Solar Amber drives primary interactive calls-to-action, solar production peak highlights, irradiance metrics, and advisory alerts.
- **Neutral (`#64748B`)**: Slate neutral provides optical balance across borders, tabular dividers, sub-labels, and disabled treatments against a clean canvas background (`#F8FAFC`).

Ensure monetary metrics and solar load calculations strictly adhere to WCAG AAA contrast against container surfaces.

## Typography

The type system blends the executive, contemporary geometry of Plus Jakarta Sans for titles, system capacities, and financial summaries with the functional legibility of Inter for body text, technical specs, and analytical tables.

Apply tabular numerals (`font-variant-numeric: tabular-nums`) across all energy production readouts, tariff comparison tables, and payback period graphs to prevent baseline shifting during dynamic recalculations.

## Layout & Spacing

A 12-column fluid grid system governs desktop interfaces, collapsing to 8 columns on tablet and 4 columns on mobile. 

The spatial cadence prioritizes dense analytical readability alongside generous structural whitespace:
- Desktop sections utilize a 2.5rem vertical rhythm, allowing multi-metric dashboards and generation curves to sit adjacent without visual congestion.
- Mobile layouts employ compact margins and tighter gaps, preserving chart legibility while keeping critical actionable metrics (e.g., Estimated Net Savings, Recommended System kW) above the fold.

## Shapes

The design system adopts a balanced roundedness (Level 2), providing a modern, accessible interface that retains architectural precision. 

Standard input fields, action buttons, and small metric badges use `0.5rem` (`rounded-md`). Cards, feasibility summary modules, and financial tables use `1rem` (`rounded-lg`). Inner nestings inside cards must step down to `0.5rem` to preserve proportional geometric continuity.

## Components

### Buttons
- **Primary**: Solid Solar Amber (`#D97706`), bold white text, subtle downward inset shadow, transitions to `#B45309` on hover. Used for primary conversion points: "Generate Feasibility Report" or "Calculate LESCO Net Savings."
- **Secondary**: Deep Navy (`#0F172A`), white text, used for structural actions like "Download PDF Summary."
- **Outline / Tertiary**: 1px Slate border (`#CBD5E1`), transparent background, Deep Navy text. Hover fills to `#F1F5F9`.

### Input Fields & Selectors
- Background: `#FFFFFF` with `#CBD5E1` border.
- Focus: Crisp 2px primary focus ring (`#0F172A` with 15% opacity ring offset) and `#0F172A` border.
- Unit Adornments: Fixed right-aligned monospaced text for unit values (e.g., `PKR/kWh`, `Units`, `kW`).

### Cards & Data Panels
- Pure white container (`#FFFFFF`), 1px outline (`#E2E8F0`), `rounded-lg` (1rem), subtle ambient shadow.
- Financial metric cards display a micro badge at the top-right corner to indicate calculation confidence or LESCO peak-tariff assumptions.

### Status Chips & Badges
- **Approved / Grid Connected**: Subtle jade surface (`#ECFDF5`), bold jade text (`#047857`), 1px border (`#A7F3D0`).
- **Pending / In Review**: Amber tint surface (`#FFFBEB`), amber text (`#B45309`), 1px border (`#FDE68A`).
- **High Consumption Alert**: Crimson tint surface (`#FEF2F2`), red text (`#B91C1C`), 1px border (`#FECACA`).

### Feasibility Metrics Table
- Strict alternating rows or crisp 1px slate divider lines. Numeric columns align right; text aligns left. 
- Integrated sub-rows accommodate localized Pakistani energy variables (e.g., LESCO off-peak vs. peak unit rates, fuel price adjustments, sales tax).