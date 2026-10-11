---
name: MotoKaizen Simulator
description: Interactive customer experience simulator for collective financing model
colors:
  brand-navy: "#0f172a"
  brand-navy-light: "#1e293b"
  brand-blue: "#1d4ed8"
  brand-blue-hover: "#1e40af"
  brand-orange: "#ea580c"
  brand-orange-hover: "#c2410c"
  brand-orange-subtle: "#fff7ed"
  brand-green: "#059669"
  brand-green-subtle: "#ecfdf5"
  bg-app: "#f8fafc"
  bg-card: "#ffffff"
  bg-subtle: "#f1f5f9"
  bg-muted: "#e2e8f0"
  border-light: "#e2e8f0"
  border-medium: "#cbd5e1"
  border-dark: "#94a3b8"
  text-primary: "#0f172a"
  text-secondary: "#475569"
  text-muted: "#64748b"
  text-light: "#94a3b8"
typography:
  display:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "clamp(1.75rem, 3.5vw, 2.35rem)"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "1.35rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.05em"
rounded:
  sm: "0.5rem"
  md: "0.75rem"
  lg: "1rem"
  xl: "1.25rem"
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2rem"
  xxl: "2.5rem"
components:
  button-primary:
    backgroundColor: "{colors.brand-orange}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "0.85rem 1.75rem"
  button-primary-hover:
    backgroundColor: "{colors.brand-orange-hover}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "0.85rem 1.75rem"
  button-outline:
    backgroundColor: "#ffffff"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.md}"
    padding: "0.85rem 1.75rem"
---

# Design System: MotoKaizen Simulator

## Overview

**Creative North Star: "Trustworthy Financial Clarity"**

MotoKaizen’s simulator prioritizes institutional credibility with a formal banking aesthetic adapted for educational storytelling. The interface is structured, restrained, and informative—designed to build confidence for non-technical audiences evaluating a collective financing model. Clean surfaces, clear hierarchy, and deliberate spacing reinforce transparency and professionalism without feeling cold.

**Key Characteristics:**
- Corporate/banking formality with approachable warmth
- High clarity and scanability for instructional flows
- Trust-first color language (blues/navy + green for success, orange for action)
- Structured stepper-driven navigation emphasizing process transparency

## Colors

The palette blends institutional navy/blues with actionable orange and reassuring greens, set against soft neutral backgrounds for readability.

### Primary
- **MotoKaizen Navy** (#0f172a): Core brand anchor used for headings, primary text, and key UI elements.
- **Action Orange** (#ea580c): Primary action color for CTAs and interactive emphasis; conveys momentum and confidence.

### Secondary
- **Trust Blue** (#1d4ed8): Supporting accent for informational states and links.

### Neutral
- **Application Background** (#f8fafc): Soft neutral canvas reducing eye strain across multi-step flows.
- **Card Surface** (#ffffff): Primary content surface for clarity and contrast.
- **Subtle Background** (#f1f5f9): Section dividers and supporting panels.
- **Border Light** (#e2e8f0): Default borders for structure and separation.
- **Secondary Text** (#475569): Body text for comfortable reading.
- **Muted Text** (#64748b): Supporting metadata and labels.

### Semantic
- **Success Green** (#059669): Confirmation states, completed steps, and positive outcomes.
- **Success Subtle** (#ecfdf5): Background for success messaging and badges.

**The Clarity Rule.** Color is used functionally to guide attention and communicate state, never decoratively at the expense of comprehension.

## Typography

**Display Font:** -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif
**Body Font:** -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif
**Label Font:** -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif

**Character:** System font stack prioritizes legibility, familiarity, and cross-platform consistency—appropriate for an institutional, trust-focused interface.

### Hierarchy
- **Display** (800, clamp(1.75rem, 3.5vw, 2.35rem), 1.1, -0.02em): Hero section titles and primary screen headings.
- **Headline** (800, 1.5rem, 1.15, -0.02em): Sub-section headers within screens.
- **Title** (800, 1.35rem, 1.2, -0.02em): Card titles, model names, and key entities.
- **Body** (400, 1rem, 1.5): Primary content and instructional text.
- **Label** (700, 0.75rem, 1.2, 0.05em, uppercase): Badges, tags, form labels, and metadata for scannability.

**The Readability Rule.** Tight tracking on display/headings (-0.02em) paired with generous line-height (1.5) for body text maximizes scanability for educational content.

## Layout

The interface uses a max-width container (1200px) with consistent horizontal padding and vertical rhythm. Multi-step flows use a formal stepper header, sticky preview panels on desktop (screen 2), and responsive grid layouts.

Spacing follows an 8pt-aligned scale (0.25rem/4pt through 2.5rem/40pt). Cards use comfortable internal padding (1.5rem–1.75rem). Grid gaps of 1.25–1.5rem create structured, breathable layouts.

**The Structured Flow Rule.** Each screen follows a consistent banner + content pattern to reinforce the guided 4-step journey.

## Elevation & Depth

The system uses soft, deliberate shadows to create subtle depth without competing with content. Surfaces are flat-by-default with minimal elevation for cards and floating elements.

### Shadow Vocabulary
- **Shadow SM** (`0 1px 2px 0 rgba(0, 0, 0, 0.05)`): Subtle header elevation and compact elements.
- **Shadow MD** (`0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.04)`): Interactive cards and elevated UI elements.
- **Shadow LG** (`0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.03)`): Modals and prominent overlays.
- **Shadow Card** (`0 2px 8px rgba(15, 23, 42, 0.06)`): Default card elevation for gentle separation.

**The Restraint Rule.** Shadows are used sparingly and with low opacity to maintain the clean, institutional aesthetic.

## Shapes

Rounded corners follow a consistent scale (sm/md/lg/xl). Cards use larger radius (xl, 1.25rem) for a friendly, modern feel while buttons and inputs use md (0.75rem) for precision. Pills/badges use full radius (9999px).

**The Consistent Curves Rule.** Shape language is uniform across components—soft, predictable curves that feel polished and approachable.

## Components

### Buttons
- **Shape:** Medium rounded (0.75rem). Full-width option available for cards.
- **Primary:** Orange background (#ea580c), white text. Padding 0.85rem 1.75rem (lg size 1.05rem 2.4rem). Subtle shadow on rest, lifts on hover.
- **Hover / Focus:** Background shifts to #c2410c with slight translateY lift and increased shadow; smooth 0.2s transitions.
- **Outline:** White background, secondary text (#475569), 1.5px border (#cbd5e1). On hover, subtle background (#f1f5f9), navy text, darker border.
- **Green (Success):** Green background (#059669), white text. Used for success/confirmation actions.

### Cards
- **Corner Style:** Extra-large radius (1.25rem).
- **Background:** White (#ffffff) with 1px light border (#e2e8f0).
- **Shadow Strategy:** Shadow Card (0 2px 8px rgba(15,23,42,0.06)); lifts on hover with orange border highlight.
- **Internal Padding:** 1.5rem–1.75rem depending on context (bike cards 1.5rem, config cards 1.75rem).
- **Behavior:** Hover state adds orange border, increased shadow, subtle translateY (-4px) for bike selection cards.

### Stepper (Bank Stepper)
- **Style:** Pill-shaped container (9999px radius) with subtle background (#f1f5f9) and light border. Active step has white background with orange badge; completed steps shown in green.

### Form Inputs
- **Style:** 1.5px border (#cbd5e1), white background, medium radius (0.75rem), padding 0.85rem 1rem. System font.
- **Focus:** Orange border (#ea580c) with soft focus ring (rgba(234,88,12,0.15)).
- **States:** Clean, high-contrast for accessibility.

### Badges & Pills
- **Style:** Full-radius (9999px), compact padding, uppercase labels with letter-spacing. Color-coded by semantic meaning (info blue, success green, brand orange).

### Loading Modal
- **Style:** Centered card with large shadow, backdrop blur (6px) for focus. Orange spinner ring indicates progress.

## Do's and Don'ts

### Do:
- **Do** maintain the formal banking aesthetic—structured, clean, and professional.
- **Do** prioritize clarity over decoration in every screen; function leads visual treatment.
- **Do** use orange (#ea580c) exclusively for primary actions to create clear affordance hierarchy.
- **Do** leverage whitespace and the 8pt scale for consistent, breathable layouts.
- **Do** preserve the pedagogical, transparent tone in UI copy and visual emphasis.

### Don't:
- **Don't** sacrifice readability for visual flair—system fonts and high contrast are non-negotiable.
- **Don't** overuse shadows or decorative effects that compete with instructional content.
- **Don't** introduce colors outside the established palette without functional justification.
- **Don't** break the stepper flow pattern; preserve the guided 4-step structure's clarity.