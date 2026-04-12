# UI Enhancements: Animations, Encouraging Messages, Theme Switching

**Date:** 2026-04-12
**Approach:** CSS-only animations, no new dependencies

## Overview

Enhance the quiz app with three features: a three-way theme toggle (light/dark/system), encouraging messages in Romanian throughout the user journey, and playful CSS animations with improved visual polish (typography, card design, spacing).

## 1. Theme Switching

### Toggle UI

Three icon buttons in a pill-shaped group, placed in the top navigation bar next to user/logout:

- ☀️ Light — forces light theme
- 🌙 Dark — forces dark theme
- 💻 System — follows OS `prefers-color-scheme`

Active button gets primary color background; inactive buttons are muted.

### Implementation

- Store preference in `localStorage` key `"theme"` with values `"light"`, `"dark"`, or `"system"`
- Set `data-theme` attribute on `<html>`: `"light"` or `"dark"` for forced modes, remove attribute for system mode
- CSS selectors: `[data-theme="light"]` and `[data-theme="dark"]` override variables. Bare `:root` uses `prefers-color-scheme` as fallback
- **Flash prevention:** Inline `<script>` in `index.html` (before React mounts) reads `localStorage` and sets `data-theme` immediately
- Create a `ThemeContext` or simple hook (`useTheme`) to expose `{theme, setTheme}` to components
- Refactor existing `@media (prefers-color-scheme: dark)` block into a `[data-theme="dark"]` selector, with a `@media` fallback when no `data-theme` is set

### Toggle placement

Inside the dashboard/quiz nav bar, between the app title and user info. On mobile, the toggle collapses to just icons (no labels).

## 2. Encouraging Messages (Romanian)

### Message pools

**Correct answer (quiz, toast):**
- "Excelent!"
- "Foarte bine!"
- "Așa da!"
- "Perfect!"
- "Bravo!"
- "Corect!"
- "Impecabil!"

**Streak messages (quiz, toast, after 3+ consecutive correct):**
- "Trei la rând! Continuă tot așa!" (3)
- "Cinci corecte consecutiv! Ești în formă!" (5)
- "Serie de {n}! Ești de neoprit!" (7+)

**Wrong answer (quiz, toast, gentler tone):**
- "Nu renunța!"
- "Greșelile ne ajută să învățăm"
- "Data viitoare va fi mai bine"
- "Continuă, ești pe drumul cel bun!"
- "Răbdare — progresul vine cu exercițiu"

**Results page (banner, score-based):**
- 90%+: "Rezultat extraordinar! Ești foarte bine pregătit!"
- 70–89%: "Foarte bine! Mai repetă capitolele unde ai greșit."
- 50–69%: "Efort bun! Continuă să exersezi, progresul vine."
- <50%: "Nu te descuraja — fiecare test te face mai bun. Revino și încearcă din nou!"

**Dashboard messages:**
- Welcome: "Bine ai revenit, {username}!"
- Streak: "{n} zile consecutive de studiu!" (requires backend)
- Improvement: "Ai crescut cu {n}% luna aceasta!" (requires backend)
- First visit: "Bine ai venit! Începe primul tău test." (no history)
- Milestone: "Ai răspuns la {n} întrebări în total!" (thresholds: 100, 500, 1000, 5000, 10000)

### Toast component

- Position: bottom-right (desktop), bottom-center (mobile)
- Behavior: one toast at a time, auto-dismiss after 2 seconds
- Animation: slides up with bounce on enter, fades out on exit
- Color: green background tint for correct, warm/orange tint for encouragement on wrong
- Shows random message from the relevant pool

### Backend additions

New data to support dashboard messages:

- **Study streak:** Track consecutive days with at least one completed session. Add a `study_streak` field to the stats endpoint response. Logic: check `completed_at` dates from session history, count consecutive days up to today.
- **Monthly accuracy improvement:** Compare current month's accuracy to previous month's. Add `accuracy_trend` (percentage point change) to stats endpoint.
- **Total answered milestone:** Already available via `total_answered` in stats — frontend picks the appropriate milestone message.

These are lightweight additions to the existing `/api/stats` endpoint, not new endpoints.

## 3. Animations

All CSS `@keyframes`, no JavaScript animation libraries.

### Page/component entrance

- **Staggered fade-in + slide-up:** Cards and sections on any page fade in from 20px below with 50ms stagger between siblings. Animation: `fadeSlideUp 0.4s ease-out forwards`.
- **Dashboard stat cards:** Bounce in with `cubic-bezier(0.34, 1.56, 0.64, 1)` — overshoots slightly then settles. Stagger: 80ms per card.

### Quiz interactions

- **Question navigation:** Card slides in from right (forward) or left (backward). Uses `slideInRight` / `slideInLeft` keyframes, 0.3s duration.
- **Answer selection:** Chosen option scales to `1.03` briefly (pop) then back to `1`. Transition: 0.2s cubic-bezier bounce.
- **Correct reveal:** Green pulse glow (`box-shadow` animation) on the correct choice + small bounce on a checkmark icon.
- **Wrong reveal:** Horizontal shake — 3 cycles of `translateX(±4px)` over 0.4s.
- **Toast enter/exit:** `slideUpBounce` in (0.4s), `fadeOut` after 2s delay.

### Results page

- **Score count-up:** JS `requestAnimationFrame` loop counting from 0 to final score over ~1s. (CSS counters can't animate incrementally, so this is a small JS piece, not a library.)
- **Accuracy bar fill:** CSS `width` transition from `0%` to final value, 1s ease-out, triggered by adding a class on mount.
- **Confetti (score >= 90%):** 25–30 small colored `<div>`s absolutely positioned, each with randomized `@keyframes confettiFall` (different x-drift, rotation, fall speed). Auto-removed after 3s. Pure CSS + a small JS loop to generate the divs with random inline styles.
- **Question rows:** Staggered `fadeSlideUp` as they appear.

### Dashboard

- **Stat cards:** Bounce-in with stagger (same as above).
- **Chart bars:** Grow from `height: 0` with staggered delay per bar, easing `cubic-bezier(0.34, 1.56, 0.64, 1)`.
- **Progress/improvement indicators:** Gentle pulse when showing positive change.

### Micro-interactions (global)

- **Button press:** `transform: scale(0.95)` on `:active`, spring back on release (transition 0.15s).
- **Hover lift:** Cards/buttons raise `translateY(-2px)` with shadow deepening, 0.2s ease.
- **Toggle/switch:** Smooth slide with slight overshoot via cubic-bezier.

### Respects `prefers-reduced-motion`

All animations wrapped in `@media (prefers-reduced-motion: no-preference)`. Users who prefer reduced motion get instant state changes with no animation.

## 4. Visual Polish

### Typography

- **Font:** Add Inter via Google Fonts (`<link>` in `index.html`). Fallback: existing system font stack.
- **Body line-height:** `1.6` → `1.65`
- **Heading letter-spacing:** `-0.02em` for tighter, modern feel
- **Base font size:** `15px` on body for better card readability

### Card redesign

- **Layered shadows:** Replace single `--shadow` with multi-layer:
  - Light: `0 1px 2px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.06)`
  - Dark: `0 1px 2px rgba(0,0,0,0.2), 0 4px 12px rgba(0,0,0,0.15)`
- **Glassmorphism on stat cards:** `backdrop-filter: blur(12px)` with semi-transparent backgrounds (`rgba` with 0.7–0.8 alpha). Only on dashboard stat cards, not all cards.
- **Border radius:** `8px` → `12px` globally via `--radius`
- **Hover lift:** Cards raise `translateY(-2px)` with shadow deepening on hover.
- **Subtle border:** `1px solid` with low-opacity color (helps dark mode contrast per existing feedback).

### Spacing

- Card inner padding: `1.5rem` → `1.75rem`
- Dashboard grid gap: increase by `0.25rem`
- Section headers: add `0.5rem` more margin-top

## File Changes Summary

| File | Changes |
|------|---------|
| `index.html` | Add Inter font link, inline theme script |
| `src/index.css` | Theme selectors refactor, new animations keyframes, card/typography updates, toast styles |
| `src/pages/Dashboard.tsx` | Theme toggle in nav, welcome/streak/milestone messages, entrance animations via CSS classes |
| `src/pages/Quiz.tsx` | Toast component for encouraging messages, streak tracking state, slide animation on question nav |
| `src/pages/Results.tsx` | Score count-up, confetti on high scores, score-based banner message |
| `src/components/QuestionCard.tsx` | Answer selection pop, correct/wrong reveal animations |
| `src/hooks/useTheme.ts` | New file — theme state hook with localStorage persistence |
| `src/components/Toast.tsx` | New file — reusable toast notification component |
| `src/components/Confetti.tsx` | New file — CSS confetti effect component |
| `src/messages.ts` | New file — Romanian message pools and selection logic |
| Backend: stats endpoint | Add `study_streak` and `accuracy_trend` fields |

## Out of Scope

- Multiple color themes beyond light/dark
- Sound effects
- Animation configuration/settings UI
- Gamification features (XP, levels, badges)
