# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

static HTML/CSS/Vanilla JavaScript

## Users

Primary users: potential MotoKaizen customers (non-technical - clients, executives, investors, sales advisors). They need to understand step-by-step how collective self-financing (30-person groups) works vs traditional bank credit in an interactive, visual way.

## Product Purpose

The MotoKaizen Customer Experience Simulator demonstrates how the collective financing model (tandas de 30 personas) works from start to finish. Success means clearly explaining the model, building trust (no credit bureau checks), showing transparent comparisons vs bank loans, and making the group process understandable.

## Positioning

Interactive educational simulator that explains a collective financing (tanda) model with full transparency. Emphasizes 0% usurious interest, group solidarity, no Datacrédito checks, and clear comparative savings vs traditional credit.

## Operating Context

Used in sales demos/presentations, investor pitches, or standalone. Runs entirely in browser (no backend required), portable, works on mobile/tablet/desktop. Spanish-speaking Colombian audience.

## Capabilities and Constraints

- 4-step guided flow (QR product scan + payment methods, plan config, data/docs/biometric validation, group assignment + email notification)
- QR-based product landing with MotoKaizen convenio payment method (partner stores)
- Interactive motorcycle catalog (as "choose another product" picker)
- Identity document photo upload (mobile camera) + **local document validation** (OpenCV contour + Tesseract OCR): confirms the image is a real identity document (cédula/DNI/passport/etc.), rejects random images, and falls back to simulated acceptance when the server/OCR is unavailable
- Facial biometric validation with real camera using Python/OpenCV (`servidor-simulador.py` serves `/api/validate-face`); auto-falls back to simulated mode when camera/server is unavailable
- Local Python server (`servidor-simulador.py`) enabling camera access, face detection, document OCR validation, and static hosting (used via `servidor-local.bat`); ships `tessdata/` with eng+spa languages
- Guaranteed group availability in test environment with random cupo assignment
- Group visualization of 30 members (own cupo highlighted)
- Simulated email notification with group code and cupo
- Must work offline/opened directly via index.html (standalone)
- Formal light banking theme (white surfaces, navy/orange)
- Mobile-first: touch targets 44px, camera capture, safe-area, numeric keypads
- Responsive design, custom CSS variables

## Brand Commitments

- Name: MotoKaizen
- Spanish (Colombia) UI/UX
- Corporate/banking formal aesthetic (current theme)
- Educational/pedagogical tone - clear, trustworthy, non-technical
- Transparency focus (explicit fee/interest comparisons)

## Evidence on Hand

index.html (~2950 lines) contains full implementation with real camera biometric flow and local document validation (OpenCV + Tesseract OCR, simulated fallback). servidor-simulador.py provides the OpenCV face-detection and document-OCR APIs (tessdata/ ships eng+spa). README.md documents the 4-stage journey (QR product scan → plan → validation with documents/biometrics → group + email).

## Product Principles

1. Clarity over complexity - explain financial model simply for non-technical users
2. Transparency first - show comparisons and costs openly
3. Trust by design - highlight no credit checks, money stays intact, rules explained
4. Educational demonstration - prioritize pedagogy over gamification
5. Accessible standalone - runs directly in browser without installation

## Accessibility & Inclusion

Spanish-first interface. Must remain clear and usable for non-technical audience across devices.
