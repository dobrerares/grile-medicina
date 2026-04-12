# UI Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add theme switching (light/dark/system), encouraging Romanian messages, playful CSS animations, and visual polish to the quiz app.

**Architecture:** Pure CSS animations via `@keyframes` (no new deps). Theme stored in `localStorage`, applied via `data-theme` on `<html>`. Messages are static Romanian string arrays selected by score/streak. Backend gets two new fields on `/api/stats` for streak and accuracy trend.

**Tech Stack:** React 18, TypeScript, Vite, vanilla CSS with CSS custom properties, Python/FastAPI backend with SQLAlchemy/SQLite.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `webapp/frontend/index.html` | Modify | Add Inter font, inline theme init script |
| `webapp/frontend/src/index.css` | Modify | Theme selectors, animations, visual polish |
| `webapp/frontend/src/hooks/useTheme.ts` | Create | Theme state + localStorage persistence |
| `webapp/frontend/src/messages.ts` | Create | Romanian message pools + selection logic |
| `webapp/frontend/src/components/Toast.tsx` | Create | Toast notification component |
| `webapp/frontend/src/components/Confetti.tsx` | Create | CSS confetti effect for high scores |
| `webapp/frontend/src/components/ThemeToggle.tsx` | Create | Three-way theme toggle UI |
| `webapp/frontend/src/pages/Dashboard.tsx` | Modify | Theme toggle in header, welcome/milestone messages, animation classes |
| `webapp/frontend/src/pages/Quiz.tsx` | Modify | Toast on answer, streak tracking, slide animations |
| `webapp/frontend/src/pages/Results.tsx` | Modify | Score count-up, confetti, banner message |
| `webapp/frontend/src/components/QuestionCard.tsx` | Modify | Answer pop/shake/glow animations |
| `webapp/frontend/src/types.ts` | Modify | Add `study_streak` and `accuracy_trend` to Stats |
| `webapp/backend/routes.py` | Modify | Compute streak + accuracy trend in stats endpoint |

---

### Task 1: Theme System — CSS Foundation

**Files:**
- Modify: `webapp/frontend/src/index.css:1-38`
- Modify: `webapp/frontend/src/index.css:187-200`

This task refactors the existing dark mode from `@media (prefers-color-scheme)` to `data-theme` attribute selectors, keeping the media query as the system fallback.

- [ ] **Step 1: Replace the first dark mode media query block with data-theme selectors**

In `webapp/frontend/src/index.css`, replace lines 15-38:

```css
/* Forced light */
[data-theme="light"] {
  --color-bg: #f8f9fa;
  --color-surface: #ffffff;
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-text: #1a1a2e;
  --color-text-muted: #6b7280;
  --color-border: #e5e7eb;
  --color-error: #dc2626;
  --color-error-bg: #fef2f2;
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.06);
  color-scheme: light;
}

/* Forced dark */
[data-theme="dark"] {
  --color-bg: #0f1117;
  --color-surface: #1a1b26;
  --color-primary: #3b82f6;
  --color-primary-hover: #60a5fa;
  --color-text: #e2e8f0;
  --color-text-muted: #94a3b8;
  --color-border: #2d3148;
  --color-error: #f87171;
  --color-error-bg: #2d1b1b;
  --color-success: #4ade80;
  --color-success-bg: #052e16;
  --color-warning: #fbbf24;
  --color-warning-bg: #2e2510;
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.2);
  color-scheme: dark;
}

[data-theme="dark"] input,
[data-theme="dark"] select,
[data-theme="dark"] textarea {
  background: var(--color-surface);
  color: var(--color-text);
}

/* System fallback (no data-theme attribute set) */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme]) {
    --color-bg: #0f1117;
    --color-surface: #1a1b26;
    --color-primary: #3b82f6;
    --color-primary-hover: #60a5fa;
    --color-text: #e2e8f0;
    --color-text-muted: #94a3b8;
    --color-border: #2d3148;
    --color-error: #f87171;
    --color-error-bg: #2d1b1b;
    --color-success: #4ade80;
    --color-success-bg: #052e16;
    --color-warning: #fbbf24;
    --color-warning-bg: #2e2510;
    --shadow: 0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.2);
    color-scheme: dark;
  }

  :root:not([data-theme]) input,
  :root:not([data-theme]) select,
  :root:not([data-theme]) textarea {
    background: var(--color-surface);
    color: var(--color-text);
  }
}
```

- [ ] **Step 2: Replace the second dark mode media query block**

In `webapp/frontend/src/index.css`, replace lines 187-200 (the second `@media (prefers-color-scheme: dark)` block with additional color vars):

```css
[data-theme="dark"] {
  --color-cs: #60a5fa;
  --color-cg: #fb923c;
  --color-bg-muted: #1e2030;
  --color-bg-hover: #1e2030;
  --color-bg-detail: #1e2030;
  --color-selected-bg: #1e3a5f;
  --color-badge-cs-bg: #1e3a5f;
  --color-badge-cg-bg: #3b2810;
  --color-btn-secondary-hover: #3d4050;
  --color-unanswered: #6b7280;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme]) {
    --color-cs: #60a5fa;
    --color-cg: #fb923c;
    --color-bg-muted: #1e2030;
    --color-bg-hover: #1e2030;
    --color-bg-detail: #1e2030;
    --color-selected-bg: #1e3a5f;
    --color-badge-cs-bg: #1e3a5f;
    --color-badge-cg-bg: #3b2810;
    --color-btn-secondary-hover: #3d4050;
    --color-unanswered: #6b7280;
  }
}
```

- [ ] **Step 3: Verify the app still renders correctly**

Run: `cd webapp/frontend && npx tsc --noEmit`
Expected: no errors (CSS changes don't affect TS, but verify nothing broke)

Open the app in a browser and verify both light and dark modes render correctly.

- [ ] **Step 4: Commit**

```bash
git add webapp/frontend/src/index.css
git commit -m "refactor: convert dark mode from media query to data-theme attribute selectors"
```

---

### Task 2: Theme System — Hook, Toggle Component, Flash Prevention

**Files:**
- Create: `webapp/frontend/src/hooks/useTheme.ts`
- Create: `webapp/frontend/src/components/ThemeToggle.tsx`
- Modify: `webapp/frontend/index.html:14-15`
- Modify: `webapp/frontend/src/index.css` (add theme toggle styles)

- [ ] **Step 1: Create the useTheme hook**

Create `webapp/frontend/src/hooks/useTheme.ts`:

```typescript
import { useEffect, useState, useCallback } from "react";

type Theme = "light" | "dark" | "system";

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  if (theme === "system") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", theme);
  }
  // Update meta theme-color for mobile browsers
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) {
    const isDark =
      theme === "dark" ||
      (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    meta.setAttribute("content", isDark ? "#0f1117" : "#2563eb");
  }
}

function getStoredTheme(): Theme {
  const stored = localStorage.getItem("theme");
  if (stored === "light" || stored === "dark" || stored === "system") return stored;
  return "system";
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(getStoredTheme);

  const setTheme = useCallback((t: Theme) => {
    localStorage.setItem("theme", t);
    applyTheme(t);
    setThemeState(t);
  }, []);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // Listen for OS theme changes when in system mode
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      if (getStoredTheme() === "system") applyTheme("system");
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  return { theme, setTheme } as const;
}
```

- [ ] **Step 2: Create the ThemeToggle component**

Create `webapp/frontend/src/components/ThemeToggle.tsx`:

```tsx
import { useTheme } from "../hooks/useTheme";

const options = [
  { value: "light" as const, icon: "\u2600\uFE0F", label: "Luminos" },
  { value: "dark" as const, icon: "\uD83C\uDF19", label: "Intunecat" },
  { value: "system" as const, icon: "\uD83D\uDCBB", label: "Sistem" },
];

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="theme-toggle" role="radiogroup" aria-label="Tema">
      {options.map((opt) => (
        <button
          key={opt.value}
          className={`theme-toggle-btn${theme === opt.value ? " theme-toggle-active" : ""}`}
          onClick={() => setTheme(opt.value)}
          aria-checked={theme === opt.value}
          role="radio"
          title={opt.label}
          type="button"
        >
          <span aria-hidden="true">{opt.icon}</span>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Add flash prevention script to index.html**

In `webapp/frontend/index.html`, add this inline script before the React entry point (before `<script type="module" src="/src/main.tsx">`):

```html
    <script>
      (function() {
        var t = localStorage.getItem('theme');
        if (t === 'light' || t === 'dark') {
          document.documentElement.setAttribute('data-theme', t);
        }
      })();
    </script>
```

Also add the Inter font link in `<head>` (before `<title>`):

```html
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
```

- [ ] **Step 4: Add theme toggle CSS**

Append to `webapp/frontend/src/index.css` (before the modal section, around line 1700):

```css
/* ------ Theme Toggle ------ */

.theme-toggle {
  display: flex;
  background: var(--color-bg-muted);
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
}

.theme-toggle-btn {
  padding: 5px 9px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
  line-height: 1;
}

.theme-toggle-btn:hover {
  color: var(--color-text);
}

.theme-toggle-active {
  background: var(--color-primary);
  color: #fff;
}

.theme-toggle-active:hover {
  color: #fff;
}
```

- [ ] **Step 5: Verify theme toggle renders and works**

Run: `cd webapp/frontend && npx tsc --noEmit`
Expected: no errors

(Integration with Dashboard header happens in Task 7.)

- [ ] **Step 6: Commit**

```bash
git add webapp/frontend/src/hooks/useTheme.ts webapp/frontend/src/components/ThemeToggle.tsx webapp/frontend/index.html webapp/frontend/src/index.css
git commit -m "feat: add theme toggle hook, component, and flash prevention"
```

---

### Task 3: Romanian Messages Module

**Files:**
- Create: `webapp/frontend/src/messages.ts`

- [ ] **Step 1: Create the messages module**

Create `webapp/frontend/src/messages.ts`:

```typescript
// --- Correct answer toasts ---
const CORRECT_MESSAGES = [
  "Excelent!",
  "Foarte bine!",
  "Așa da!",
  "Perfect!",
  "Bravo!",
  "Corect!",
  "Impecabil!",
];

// --- Streak toasts (shown instead of CORRECT_MESSAGES when on a streak) ---
const STREAK_MESSAGES: Record<number, string> = {
  3: "Trei la rând! Continuă tot așa!",
  5: "Cinci corecte consecutiv! Ești în formă!",
  7: "Serie de 7! Ești de neoprit!",
  10: "10 corecte la rând! Incredibil!",
};

// --- Wrong answer toasts ---
const WRONG_MESSAGES = [
  "Nu renunța!",
  "Greșelile ne ajută să învățăm",
  "Data viitoare va fi mai bine",
  "Continuă, ești pe drumul cel bun!",
  "Răbdare — progresul vine cu exercițiu",
];

// --- Results page banners ---
interface ResultBanner {
  text: string;
  tone: "excellent" | "good" | "decent" | "encourage";
}

function getResultBanner(accuracy: number): ResultBanner {
  if (accuracy >= 0.9) return { text: "Rezultat extraordinar! Ești foarte bine pregătit!", tone: "excellent" };
  if (accuracy >= 0.7) return { text: "Foarte bine! Mai repetă capitolele unde ai greșit.", tone: "good" };
  if (accuracy >= 0.5) return { text: "Efort bun! Continuă să exersezi, progresul vine.", tone: "decent" };
  return { text: "Nu te descuraja — fiecare test te face mai bun. Revino și încearcă din nou!", tone: "encourage" };
}

// --- Dashboard messages ---
interface DashboardMessage {
  text: string;
  type: "streak" | "improvement" | "milestone" | "welcome";
}

function getDashboardMessages(
  username: string,
  totalAnswered: number,
  studyStreak: number,
  accuracyTrend: number,
): DashboardMessage[] {
  const messages: DashboardMessage[] = [];

  if (studyStreak >= 3) {
    messages.push({ text: `${studyStreak} zile consecutive de studiu!`, type: "streak" });
  }

  if (accuracyTrend > 0) {
    messages.push({
      text: `Ai crescut cu ${Math.round(accuracyTrend * 100)}% luna aceasta!`,
      type: "improvement",
    });
  }

  const milestones = [10000, 5000, 1000, 500, 100];
  for (const m of milestones) {
    if (totalAnswered >= m) {
      messages.push({ text: `Ai răspuns la ${m.toLocaleString("ro-RO")} întrebări în total!`, type: "milestone" });
      break;
    }
  }

  return messages;
}

// --- Helpers ---
function pickRandom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function getCorrectToast(streak: number): string {
  // Check for exact streak milestones first
  if (STREAK_MESSAGES[streak]) return STREAK_MESSAGES[streak];
  // For streaks > 10, show generic streak message every 5
  if (streak > 10 && streak % 5 === 0) return `Serie de ${streak}! Ești de neoprit!`;
  return pickRandom(CORRECT_MESSAGES);
}

function getWrongToast(): string {
  return pickRandom(WRONG_MESSAGES);
}

export { getCorrectToast, getWrongToast, getResultBanner, getDashboardMessages };
export type { ResultBanner, DashboardMessage };
```

- [ ] **Step 2: Verify compilation**

Run: `cd webapp/frontend && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add webapp/frontend/src/messages.ts
git commit -m "feat: add Romanian encouraging messages module"
```

---

### Task 4: Toast Component

**Files:**
- Create: `webapp/frontend/src/components/Toast.tsx`
- Modify: `webapp/frontend/src/index.css` (add toast styles + keyframes)

- [ ] **Step 1: Create the Toast component**

Create `webapp/frontend/src/components/Toast.tsx`:

```tsx
import { useEffect, useState } from "react";

interface ToastProps {
  message: string;
  type: "correct" | "wrong";
  onDone: () => void;
}

export default function Toast({ message, type, onDone }: ToastProps) {
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    const fadeTimer = setTimeout(() => setExiting(true), 1700);
    const removeTimer = setTimeout(onDone, 2100);
    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(removeTimer);
    };
  }, [onDone]);

  return (
    <div className={`toast toast-${type}${exiting ? " toast-exit" : ""}`}>
      {message}
    </div>
  );
}
```

- [ ] **Step 2: Add toast CSS and animation keyframes**

Append to `webapp/frontend/src/index.css` (after the theme toggle section):

```css
/* ------ Toast ------ */

.toast {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  padding: 0.75rem 1.25rem;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 600;
  z-index: 1100;
  pointer-events: none;
  animation: toastIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.toast-correct {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.toast-wrong {
  background: var(--color-warning-bg, #fffbeb);
  color: var(--color-warning, #d97706);
  border: 1px solid var(--color-warning, #d97706);
}

.toast-exit {
  animation: toastOut 0.3s ease forwards;
}

@keyframes toastIn {
  from { opacity: 0; transform: translateY(20px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes toastOut {
  from { opacity: 1; transform: translateY(0); }
  to { opacity: 0; transform: translateY(-10px); }
}

@media (max-width: 768px) {
  .toast {
    bottom: calc(5rem + env(safe-area-inset-bottom, 0));
    right: 50%;
    transform: translateX(50%);
    left: auto;
    white-space: nowrap;
  }
}
```

- [ ] **Step 3: Verify compilation**

Run: `cd webapp/frontend && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add webapp/frontend/src/components/Toast.tsx webapp/frontend/src/index.css
git commit -m "feat: add toast notification component with slide-bounce animation"
```

---

### Task 5: Confetti Component

**Files:**
- Create: `webapp/frontend/src/components/Confetti.tsx`
- Modify: `webapp/frontend/src/index.css` (add confetti keyframes)

- [ ] **Step 1: Create the Confetti component**

Create `webapp/frontend/src/components/Confetti.tsx`:

```tsx
import { useEffect, useState } from "react";

const COLORS = ["#3b82f6", "#16a34a", "#eab308", "#ef4444", "#8b5cf6", "#ec4899", "#f97316"];

interface Particle {
  id: number;
  left: number;
  delay: number;
  duration: number;
  color: string;
  size: number;
  drift: number;
  rotation: number;
}

function createParticles(count: number): Particle[] {
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    left: Math.random() * 100,
    delay: Math.random() * 0.8,
    duration: 2 + Math.random() * 1.5,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
    size: 6 + Math.random() * 6,
    drift: -30 + Math.random() * 60,
    rotation: Math.random() * 360,
  }));
}

export default function Confetti() {
  const [particles] = useState(() => createParticles(30));
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(false), 3500);
    return () => clearTimeout(timer);
  }, []);

  if (!visible) return null;

  return (
    <div className="confetti-container" aria-hidden="true">
      {particles.map((p) => (
        <div
          key={p.id}
          className="confetti-particle"
          style={{
            left: `${p.left}%`,
            width: p.size,
            height: p.size,
            background: p.color,
            animationDelay: `${p.delay}s`,
            animationDuration: `${p.duration}s`,
            "--drift": `${p.drift}px`,
            "--rotation": `${p.rotation}deg`,
          } as React.CSSProperties}
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Add confetti CSS**

Append to `webapp/frontend/src/index.css`:

```css
/* ------ Confetti ------ */

.confetti-container {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 1200;
  overflow: hidden;
}

.confetti-particle {
  position: absolute;
  top: -10px;
  border-radius: 2px;
  animation: confettiFall linear forwards;
}

@keyframes confettiFall {
  0% {
    transform: translateY(0) translateX(0) rotate(0deg);
    opacity: 1;
  }
  100% {
    transform: translateY(100vh) translateX(var(--drift, 0px)) rotate(calc(var(--rotation, 0deg) + 720deg));
    opacity: 0;
  }
}
```

- [ ] **Step 3: Verify compilation**

Run: `cd webapp/frontend && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add webapp/frontend/src/components/Confetti.tsx webapp/frontend/src/index.css
git commit -m "feat: add CSS confetti celebration component"
```

---

### Task 6: Animation Keyframes + Visual Polish CSS

**Files:**
- Modify: `webapp/frontend/src/index.css`

This task adds all the animation keyframes, updates typography, card styles, and spacing.

- [ ] **Step 1: Update typography and base styles**

In `webapp/frontend/src/index.css`, update the `body` rule (around line 49):

Change:
```css
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.6;
```

To:
```css
body {
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 15px;
  line-height: 1.65;
```

- [ ] **Step 2: Update CSS custom properties for visual polish**

In `webapp/frontend/src/index.css`, in the `:root` block (line 1-13), change:
```css
  --radius: 8px;
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.06);
```
To:
```css
  --radius: 12px;
  --shadow: 0 1px 2px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.06);
```

In the `[data-theme="dark"]` block, change the shadow to:
```css
  --shadow: 0 1px 2px rgba(0, 0, 0, 0.2), 0 4px 12px rgba(0, 0, 0, 0.15);
```

And in the `@media (prefers-color-scheme: dark) { :root:not([data-theme])` block, same shadow change.

- [ ] **Step 3: Update card padding and stat card styles**

In `.stat-card` (around line 1042), change:
```css
.stat-card {
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 1.25rem;
```
To:
```css
.stat-card {
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 1.5rem;
  border: 1px solid var(--color-border);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
```

In `.question-card` (around line 502), change:
```css
.question-card {
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 1.5rem;
}
```
To:
```css
.question-card {
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 1.75rem;
  border: 1px solid var(--color-border);
}
```

Update `.stats-grid` gap (around line 1035):
```css
  gap: 1rem;
```
To:
```css
  gap: 1.25rem;
```

Update `.dash-section-title` (around line 1078):
```css
.dash-section-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
}
```
To:
```css
.dash-section-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  letter-spacing: -0.02em;
}
```

Update `.results-card h1`, `.setup-card h1`, `.dash-header h1`, and `.admin-header h1` — add `letter-spacing: -0.02em;` to each.

- [ ] **Step 4: Add hover lift to cards**

Append these rules:

```css
/* ------ Hover Lift ------ */

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06), 0 8px 20px rgba(0, 0, 0, 0.08);
}

.weak-item,
.resume-card,
.stats-chart,
.admin-report-row {
  border: 1px solid var(--color-border);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.weak-item:hover,
.stats-chart:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06), 0 8px 20px rgba(0, 0, 0, 0.08);
}
```

- [ ] **Step 5: Add all animation keyframes**

Append to `webapp/frontend/src/index.css`:

```css
/* ------ Animation Keyframes ------ */

@media (prefers-reduced-motion: no-preference) {

  @keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes bounceIn {
    0% { opacity: 0; transform: scale(0.8); }
    60% { opacity: 1; transform: scale(1.05); }
    100% { transform: scale(1); }
  }

  @keyframes slideInRight {
    from { opacity: 0; transform: translateX(30px); }
    to { opacity: 1; transform: translateX(0); }
  }

  @keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-30px); }
    to { opacity: 1; transform: translateX(0); }
  }

  @keyframes popIn {
    0% { transform: scale(1); }
    50% { transform: scale(1.04); }
    100% { transform: scale(1); }
  }

  @keyframes correctGlow {
    0% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.4); }
    50% { box-shadow: 0 0 0 8px rgba(22, 163, 74, 0); }
    100% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0); }
  }

  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    20% { transform: translateX(-4px); }
    40% { transform: translateX(4px); }
    60% { transform: translateX(-4px); }
    80% { transform: translateX(4px); }
  }

  @keyframes pulseGlow {
    0%, 100% { opacity: 0.7; }
    50% { opacity: 1; }
  }

  @keyframes countUp {
    from { opacity: 0; transform: scale(0.5); }
    to { opacity: 1; transform: scale(1); }
  }

  /* Entrance animations */
  .anim-fade-slide-up {
    opacity: 0;
    animation: fadeSlideUp 0.4s ease-out forwards;
  }

  .anim-bounce-in {
    opacity: 0;
    animation: bounceIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  }

  .anim-slide-right {
    animation: slideInRight 0.3s ease-out;
  }

  .anim-slide-left {
    animation: slideInLeft 0.3s ease-out;
  }

  /* Quiz answer feedback */
  .anim-pop { animation: popIn 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); }
  .anim-correct-glow { animation: correctGlow 0.6s ease-out; }
  .anim-shake { animation: shake 0.4s ease-in-out; }

  /* Results */
  .anim-count-up { animation: countUp 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; }

  /* Micro-interactions */
  .btn:active:not(:disabled) {
    transform: scale(0.95);
    transition: transform 0.1s;
  }

  /* Chart bar grow animation */
  .bar-fill {
    transition: width 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  /* Progress bar improvement indicator pulse */
  .anim-pulse {
    animation: pulseGlow 2s ease-in-out infinite;
  }

}
```

- [ ] **Step 6: Verify compilation and visual appearance**

Run: `cd webapp/frontend && npx tsc --noEmit`
Expected: no errors

Open the app, check that cards have the updated border-radius, shadows, and spacing.

- [ ] **Step 7: Commit**

```bash
git add webapp/frontend/src/index.css
git commit -m "feat: add animation keyframes, visual polish, and hover effects"
```

---

### Task 7: Dashboard — Theme Toggle, Messages, Entrance Animations

**Files:**
- Modify: `webapp/frontend/src/pages/Dashboard.tsx`
- Modify: `webapp/frontend/src/types.ts:66-78`
- Modify: `webapp/frontend/src/index.css` (dashboard message styles)

- [ ] **Step 1: Add study_streak and accuracy_trend to Stats type**

In `webapp/frontend/src/types.ts`, change the `Stats` interface:

```typescript
export interface Stats {
  total_answered: number;
  total_correct: number;
  accuracy: number;
  study_streak: number;
  accuracy_trend: number;
  by_topic: Record<
    string,
    { total: number; correct: number; accuracy: number }
  >;
  by_year: Record<
    string,
    { total: number; correct: number; accuracy: number }
  >;
}
```

- [ ] **Step 2: Add dashboard message CSS**

Append to `webapp/frontend/src/index.css`:

```css
/* ------ Dashboard Messages ------ */

.dash-messages {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
}

.dash-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  border-radius: var(--radius);
  font-size: 0.875rem;
  font-weight: 500;
}

.dash-message-streak {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.dash-message-improvement {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.dash-message-milestone {
  background: var(--color-badge-cs-bg);
  color: var(--color-cs);
  border: 1px solid var(--color-cs);
}
```

- [ ] **Step 3: Update Dashboard.tsx**

Replace the full content of `webapp/frontend/src/pages/Dashboard.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getStats, getHistory, getWeakest, generateQuiz, generateReviewQuiz } from "../api";
import type { Stats, HistorySession, WeakQuestion } from "../types";
import StatsCharts from "../components/StatsCharts";
import ReportModal from "../components/ReportModal";
import ThemeToggle from "../components/ThemeToggle";
import { getDashboardMessages } from "../messages";

function formatTopic(raw: string): string {
  return raw.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("ro-RO", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function sessionTypeLabel(t: string): string {
  if (t === "review") return "Recapitulare";
  return "Exercitiu";
}

export default function Dashboard() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const [showReport, setShowReport] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [history, setHistory] = useState<HistorySession[]>([]);
  const [weakest, setWeakest] = useState<WeakQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    Promise.all([
      getStats().catch(() => null),
      getHistory().catch(() => []),
      getWeakest().catch(() => []),
    ]).then(([s, h, w]) => {
      setStats(s);
      setHistory(h as HistorySession[]);
      setWeakest(w as WeakQuestion[]);
      setLoading(false);
    });
  }, []);

  async function handleQuickQuiz() {
    if (generating) return;
    setGenerating(true);
    setError("");
    try {
      const res = await generateQuiz({ cs_count: 30, cg_count: 0 });
      navigate(`/quiz/${res.session_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Eroare la generarea testului");
      setGenerating(false);
    }
  }

  async function handleReviewQuiz() {
    if (generating) return;
    setGenerating(true);
    setError("");
    try {
      const res = await generateReviewQuiz({ count: 20 });
      navigate(`/quiz/${res.session_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Eroare la generarea testului");
      setGenerating(false);
    }
  }

  if (loading) {
    return <div className="loading">Se incarca...</div>;
  }

  const hasData = stats && stats.total_answered > 0;

  const inProgress = history.filter((s) => !s.completed_at);

  const dashMessages = hasData
    ? getDashboardMessages(
        user?.username ?? "",
        stats!.total_answered,
        stats!.study_streak ?? 0,
        stats!.accuracy_trend ?? 0,
      )
    : [];

  const topicData = stats?.by_topic
    ? Object.entries(stats.by_topic)
        .map(([key, val]) => ({
          label: formatTopic(key),
          value: val.correct,
          total: val.total,
        }))
        .sort((a, b) => {
          const pctA = a.total ? a.value / a.total : 0;
          const pctB = b.total ? b.value / b.total : 0;
          return pctB - pctA;
        })
    : [];

  const yearData = stats?.by_year
    ? Object.entries(stats.by_year)
        .map(([key, val]) => ({
          label: key,
          value: val.correct,
          total: val.total,
        }))
        .sort((a, b) => a.label.localeCompare(b.label))
    : [];

  return (
    <div className="dashboard-page">
      <header className="dash-header">
        <div>
          <h1>Bine ai venit, {user?.username}!</h1>
          <p className="dash-subtitle">Panou de control</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <ThemeToggle />
          {isAdmin && (
            <button className="btn btn-secondary" onClick={() => navigate("/admin")}>
              Admin
            </button>
          )}
          <button className="btn btn-secondary" onClick={logout}>
            Deconectare
          </button>
        </div>
      </header>

      {error && <div className="auth-error">{error}</div>}

      {/* Encouraging dashboard messages */}
      {dashMessages.length > 0 && (
        <div className="dash-messages">
          {dashMessages.map((msg, i) => (
            <div
              key={msg.type}
              className={`dash-message dash-message-${msg.type} anim-fade-slide-up`}
              style={{ animationDelay: `${i * 0.1}s` }}
            >
              {msg.type === "streak" && "🔥 "}
              {msg.type === "improvement" && "📈 "}
              {msg.type === "milestone" && "🏆 "}
              {msg.text}
            </div>
          ))}
        </div>
      )}

      {/* Resume in-progress quizzes */}
      {inProgress.length > 0 && (
        <div className="dash-section">
          <h2 className="dash-section-title">Continua testul</h2>
          <div className="resume-list">
            {inProgress.map((s) => (
              <div
                key={s.session_id}
                className="resume-card"
                onClick={() => navigate(`/quiz/${s.session_id}`)}
              >
                <div className="resume-info">
                  <span className="resume-type">
                    {sessionTypeLabel(s.session_type)}
                  </span>
                  <span className="resume-date">
                    {formatDate(s.started_at)}
                  </span>
                </div>
                <div className="resume-progress">
                  <div className="resume-progress-bar">
                    <div
                      className="resume-progress-fill"
                      style={{
                        width: `${
                          s.total_questions
                            ? Math.round(
                                (s.answered / s.total_questions) * 100
                              )
                            : 0
                        }%`,
                      }}
                    />
                  </div>
                  <span className="resume-progress-text">
                    {s.answered}/{s.total_questions}
                  </span>
                </div>
                <button className="btn btn-primary btn-sm" type="button">
                  Continua
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {!hasData ? (
        <div className="dash-empty anim-fade-slide-up">
          <h2>Nicio activitate inca</h2>
          <p>Incepe primul tau test pentru a vedea statisticile aici.</p>
          <button
            className="btn btn-primary"
            onClick={() => navigate("/quiz/setup")}
          >
            Incepe primul test
          </button>
        </div>
      ) : (
        <>
          {/* Stats cards with bounce-in animation */}
          <div className="stats-grid">
            {[
              { value: stats!.total_answered, label: "Intrebari raspunse", accent: false },
              { value: `${Math.round(stats!.accuracy * 100)}%`, label: "Acuratete generala", accent: true },
              { value: stats!.total_correct, label: "Raspunsuri corecte", accent: false },
              { value: history.length, label: "Sesiuni completate", accent: false },
            ].map((card, i) => (
              <div
                key={card.label}
                className={`stat-card${card.accent ? " stat-card-accent" : ""} anim-bounce-in`}
                style={{ animationDelay: `${i * 0.08}s` }}
              >
                <span className="stat-value">{card.value}</span>
                <span className="stat-label">{card.label}</span>
              </div>
            ))}
          </div>

          {/* Quick actions */}
          <div className="dash-section anim-fade-slide-up" style={{ animationDelay: "0.3s" }}>
            <h2 className="dash-section-title">Actiuni rapide</h2>
            <div className="quick-actions">
              <button
                className="btn btn-primary"
                disabled={generating}
                onClick={handleQuickQuiz}
              >
                Test rapid 30
              </button>
              <button
                className="btn btn-primary"
                disabled={generating || weakest.length === 0}
                onClick={handleReviewQuiz}
              >
                Exerseaza punctele slabe
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => navigate("/quiz/setup")}
              >
                Test nou
              </button>
              <button className="btn btn-secondary" onClick={() => setShowReport(true)}>
                Raporteaza o problema
              </button>
            </div>
          </div>

          {/* Charts */}
          {topicData.length > 0 && (
            <div className="dash-section anim-fade-slide-up" style={{ animationDelay: "0.4s" }}>
              <StatsCharts data={topicData} title="Acuratete pe tema" />
            </div>
          )}

          {yearData.length > 0 && (
            <div className="dash-section anim-fade-slide-up" style={{ animationDelay: "0.5s" }}>
              <StatsCharts data={yearData} title="Acuratete pe an" />
            </div>
          )}

          {/* Recent sessions */}
          {history.length > 0 && (
            <div className="dash-section anim-fade-slide-up" style={{ animationDelay: "0.6s" }}>
              <h2 className="dash-section-title">Sesiuni recente</h2>
              <div className="history-table-wrap">
                <table className="history-table">
                  <thead>
                    <tr>
                      <th>Data</th>
                      <th>Tip</th>
                      <th>Intrebari</th>
                      <th>Scor</th>
                      <th>Acuratete</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.filter((s) => s.completed_at).slice(0, 20).map((s) => (
                      <tr
                        key={s.session_id}
                        className="history-row"
                        onClick={() =>
                          navigate(`/quiz/${s.session_id}/results`)
                        }
                      >
                        <td>{formatDate(s.started_at)}</td>
                        <td>
                          <span className="type-badge badge-cs">
                            {sessionTypeLabel(s.session_type)}
                          </span>
                        </td>
                        <td>{s.total_questions}</td>
                        <td>
                          {s.correct}/{s.answered}
                        </td>
                        <td>{Math.round(s.accuracy * 100)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Weakest questions */}
          {weakest.length > 0 && (
            <div className="dash-section anim-fade-slide-up" style={{ animationDelay: "0.7s" }}>
              <h2 className="dash-section-title">Intrebari problematice</h2>
              <div className="weak-list">
                {weakest.slice(0, 20).map((q) => (
                  <div className="weak-item" key={q.question_id}>
                    <div className="weak-text">
                      {q.text.length > 120
                        ? q.text.slice(0, 120) + "..."
                        : q.text}
                    </div>
                    <div className="weak-meta">
                      {q.topic && (
                        <span className="topic-label">
                          {formatTopic(q.topic)}
                        </span>
                      )}
                      {q.year && (
                        <span className="year-label">{q.year}</span>
                      )}
                      <span
                        className="weak-rate"
                        style={{
                          color:
                            q.error_rate >= 0.7
                              ? "var(--color-error)"
                              : q.error_rate >= 0.5
                              ? "var(--color-warning)"
                              : "var(--color-text-muted)",
                        }}
                      >
                        {Math.round(q.error_rate * 100)}% greseli
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
      {showReport && (
        <ReportModal
          onClose={() => setShowReport(false)}
          defaultCategory="app_bug"
        />
      )}
    </div>
  );
}
```

- [ ] **Step 4: Verify compilation**

Run: `cd webapp/frontend && npx tsc --noEmit`
Expected: no errors

Open dashboard in browser. Verify: theme toggle in header, stat cards bounce in, sections fade in staggered, messages show if backend returns streak/trend.

- [ ] **Step 5: Commit**

```bash
git add webapp/frontend/src/pages/Dashboard.tsx webapp/frontend/src/types.ts webapp/frontend/src/index.css
git commit -m "feat: add theme toggle, encouraging messages, and animations to dashboard"
```

---

### Task 8: Quiz Page — Toast Messages, Streak Tracking, Slide Animations

**Files:**
- Modify: `webapp/frontend/src/pages/Quiz.tsx`

- [ ] **Step 1: Update Quiz.tsx with toast, streak, and animations**

Replace the full content of `webapp/frontend/src/pages/Quiz.tsx`:

```tsx
import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { getQuiz, submitAnswer, completeQuiz } from "../api";
import type { QuizDetail, SessionQuestion, AnswerResult } from "../types";
import QuestionCard from "../components/QuestionCard";
import ComplementGrupatInfo from "../components/ComplementGrupatInfo";
import Toast from "../components/Toast";
import { getCorrectToast, getWrongToast } from "../messages";

export default function Quiz() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [quiz, setQuiz] = useState<QuizDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<
    Record<number, { selected: string; result: AnswerResult }>
  >({});
  const [pendingAnswer, setPendingAnswer] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const examMode =
    (location.state as { hideResults?: boolean } | null)?.hideResults ?? false;
  const [examSelections, setExamSelections] = useState<
    Record<number, string>
  >({});
  const timerRef = useRef<number>(Date.now());
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Toast & streak state
  const [toast, setToast] = useState<{ message: string; type: "correct" | "wrong" } | null>(null);
  const [streak, setStreak] = useState(0);
  const prevIndexRef = useRef(0);
  const [slideDir, setSlideDir] = useState<"right" | "left">("right");

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    getQuiz(Number(sessionId))
      .then((data) => {
        setQuiz(data);
        const restored: Record<
          number,
          { selected: string; result: AnswerResult }
        > = {};
        data.questions.forEach((q) => {
          if (q.answered && q.user_answer) {
            restored[q.session_question_id] = {
              selected: q.user_answer,
              result: {
                is_correct: false,
                correct_answer: "",
              },
            };
          }
        });
        setAnswers(restored);
        const firstUnanswered = data.questions.findIndex(
          (q) => !q.answered && !q.user_answer
        );
        if (firstUnanswered > 0) {
          setCurrentIndex(firstUnanswered);
        }
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Eroare")
      )
      .finally(() => setLoading(false));
  }, [sessionId]);

  useEffect(() => {
    timerRef.current = Date.now();
  }, [currentIndex]);

  const questions: SessionQuestion[] = quiz?.questions ?? [];
  const currentQuestion = questions[currentIndex] ?? null;
  const currentAnswer = currentQuestion
    ? answers[currentQuestion.session_question_id]
    : undefined;

  const handleConfirm = useCallback(async () => {
    if (!currentQuestion || !pendingAnswer || !sessionId) return;
    setSubmitting(true);
    const timeMs = Date.now() - timerRef.current;
    try {
      const result = await submitAnswer(
        Number(sessionId),
        currentQuestion.question_id,
        pendingAnswer,
        timeMs
      );
      setAnswers((prev) => ({
        ...prev,
        [currentQuestion.session_question_id]: {
          selected: pendingAnswer,
          result,
        },
      }));
      setQuiz((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          questions: prev.questions.map((q) =>
            q.session_question_id === currentQuestion.session_question_id
              ? { ...q, answered: true, user_answer: pendingAnswer }
              : q
          ),
        };
      });

      // Show toast (not in exam mode)
      if (!examMode) {
        if (result.is_correct) {
          const newStreak = streak + 1;
          setStreak(newStreak);
          setToast({ message: getCorrectToast(newStreak), type: "correct" });
        } else {
          setStreak(0);
          setToast({ message: getWrongToast(), type: "wrong" });
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eroare la trimitere");
    } finally {
      setSubmitting(false);
    }
  }, [currentQuestion, pendingAnswer, sessionId, examMode, streak]);

  async function handleFinish() {
    if (!sessionId) return;
    setFinishing(true);
    try {
      if (examMode) {
        await Promise.all(
          Object.entries(examSelections).map(([sqId, answer]) => {
            const q = questions.find(
              (q) => q.session_question_id === Number(sqId)
            );
            if (q) {
              return submitAnswer(
                Number(sessionId),
                q.question_id,
                answer
              );
            }
          })
        );
      }
      await completeQuiz(Number(sessionId));
      navigate(`/quiz/${sessionId}/results`);
    } catch {
      navigate(`/quiz/${sessionId}/results`);
    }
  }

  function goTo(idx: number) {
    setSlideDir(idx > currentIndex ? "right" : "left");
    prevIndexRef.current = currentIndex;
    setPendingAnswer(null);
    setCurrentIndex(idx);
    setSidebarOpen(false);
  }

  if (loading) return <div className="loading">Se incarca quiz-ul...</div>;
  if (error) return <div className="page-error">{error}</div>;
  if (!quiz || questions.length === 0) {
    return <div className="page-error">Quiz-ul nu a fost gasit.</div>;
  }

  const answeredCount = examMode
    ? Object.keys(examSelections).length
    : questions.filter(
        (q) => q.answered || answers[q.session_question_id]
      ).length;
  const progressPct = Math.round((answeredCount / questions.length) * 100);

  return (
    <div className="quiz-page">
      {sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <div className={`quiz-sidebar${sidebarOpen ? " sidebar-open" : ""}`}>
        <div className="sidebar-header">
          <h3>Intrebari</h3>
          <span className="sidebar-progress">
            {answeredCount}/{questions.length}
          </span>
          <button
            className="sidebar-close-btn"
            onClick={() => setSidebarOpen(false)}
            type="button"
            aria-label="Inchide"
          >
            &times;
          </button>
        </div>
        <div className="question-nav-grid">
          {questions.map((q, idx) => {
            const ans = answers[q.session_question_id];
            let cls = "nav-btn";
            if (idx === currentIndex) cls += " nav-current";
            if (!examMode && ans) {
              cls += ans.result.is_correct ? " nav-correct" : " nav-wrong";
            } else if (
              examMode
                ? examSelections[q.session_question_id]
                : ans || q.answered
            ) {
              cls += " nav-answered";
            }
            return (
              <button
                key={q.session_question_id}
                className={cls}
                onClick={() => goTo(idx)}
                type="button"
              >
                {q.position}
              </button>
            );
          })}
        </div>
        <ComplementGrupatInfo />
      </div>

      <button
        className="sidebar-toggle"
        onClick={() => setSidebarOpen(true)}
        type="button"
      >
        <span className="sidebar-toggle-grid">&#9783;</span>
        <span className="sidebar-toggle-count">
          {answeredCount}/{questions.length}
        </span>
      </button>

      <div className="quiz-main">
        <div className="quiz-top-bar">
          <div className="quiz-progress-info">
            Intrebarea {currentIndex + 1} din {questions.length}
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <button
            className="btn btn-danger finish-btn"
            onClick={handleFinish}
            disabled={finishing}
            type="button"
          >
            {finishing ? "Se finalizeaza..." : "Finalizeaza Quiz"}
          </button>
        </div>

        {currentQuestion && (
          <div
            key={currentQuestion.session_question_id}
            className={slideDir === "right" ? "anim-slide-right" : "anim-slide-left"}
          >
            <QuestionCard
              question={currentQuestion}
              selectedAnswer={
                examMode
                  ? examSelections[currentQuestion.session_question_id] ?? null
                  : currentAnswer?.selected ?? pendingAnswer
              }
              onSelectAnswer={(a) => {
                if (examMode) {
                  const isFirst =
                    !examSelections[currentQuestion.session_question_id];
                  setExamSelections((prev) => ({
                    ...prev,
                    [currentQuestion.session_question_id]: a,
                  }));
                  if (isFirst && currentIndex < questions.length - 1) {
                    goTo(currentIndex + 1);
                  }
                } else {
                  if (!currentAnswer) setPendingAnswer(a);
                }
              }}
              onConfirm={handleConfirm}
              result={examMode ? null : (currentAnswer?.result ?? null)}
              sourceFile={currentQuestion.source_file}
              pageRef={currentQuestion.page_ref}
              examMode={examMode}
            />
          </div>
        )}

        {submitting && <div className="submitting-overlay">Se trimite...</div>}

        <div className="quiz-nav-buttons">
          <button
            className="btn btn-secondary"
            onClick={() => goTo(currentIndex - 1)}
            disabled={currentIndex === 0}
            type="button"
          >
            Anterioara
          </button>
          <button
            className="btn btn-primary"
            onClick={() => goTo(currentIndex + 1)}
            disabled={currentIndex >= questions.length - 1}
            type="button"
          >
            Urmatoarea
          </button>
        </div>
      </div>

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDone={() => setToast(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify compilation**

Run: `cd webapp/frontend && npx tsc --noEmit`
Expected: no errors

Open a quiz in the browser. Answer questions — verify toast appears on correct/wrong, question card slides on navigation.

- [ ] **Step 3: Commit**

```bash
git add webapp/frontend/src/pages/Quiz.tsx
git commit -m "feat: add encouraging toasts, streak tracking, and slide animations to quiz"
```

---

### Task 9: QuestionCard — Answer Feedback Animations

**Files:**
- Modify: `webapp/frontend/src/components/QuestionCard.tsx`

- [ ] **Step 1: Add animation classes to answer choices on result reveal**

Replace the full content of `webapp/frontend/src/components/QuestionCard.tsx`:

```tsx
import { useState } from "react";
import type { SessionQuestion, AnswerResult } from "../types";
import ReportModal from "./ReportModal";

const CG_LEGEND: Record<string, string> = {
  A: "afirmatiile 1, 2, 3 sunt corecte",
  B: "afirmatiile 1, 3 sunt corecte",
  C: "afirmatiile 2, 4 sunt corecte",
  D: "numai afirmatia 4 este corecta",
  E: "toate afirmatiile sunt corecte",
};

interface QuestionCardProps {
  question: SessionQuestion;
  selectedAnswer: string | null;
  onSelectAnswer: (answer: string) => void;
  onConfirm: () => void;
  result: AnswerResult | null;
  sourceFile?: string;
  pageRef?: string;
  examMode?: boolean;
}

export default function QuestionCard({
  question,
  selectedAnswer,
  onSelectAnswer,
  onConfirm,
  result,
  sourceFile,
  pageRef,
  examMode,
}: QuestionCardProps) {
  const [showReport, setShowReport] = useState(false);
  const isCG = question.type === "complement_grupat";
  const showResult = result !== null;
  const confirmed = showResult || question.answered;

  const statementKeys = isCG
    ? Object.keys(question.choices).filter((k) => /^\d+$/.test(k))
    : [];
  const answerKeys = isCG
    ? ["A", "B", "C", "D", "E"]
    : Object.keys(question.choices).sort();

  function getChoiceClass(key: string): string {
    if (!showResult) {
      return selectedAnswer === key ? "choice-selected anim-pop" : "";
    }
    const classes: string[] = [];
    if (key === result.correct_answer) {
      classes.push("choice-correct");
      classes.push("anim-correct-glow");
    }
    if (selectedAnswer === key && key !== result.correct_answer) {
      classes.push("choice-wrong");
      classes.push("anim-shake");
    }
    if (selectedAnswer === key) {
      classes.push("choice-selected");
    }
    return classes.join(" ");
  }

  function handlePdfOpen() {
    if (!sourceFile) return;
    let page = 1;
    if (pageRef) {
      const match = pageRef.match(/(\d+)/);
      if (match) page = parseInt(match[1], 10);
    }
    const url =
      "/api/pdf/" +
      encodeURIComponent(sourceFile + ".pdf") +
      "#page=" +
      page;
    window.open(url, "_blank");
  }

  return (
    <div className="question-card">
      <div className="question-header">
        <span className="question-number">
          Intrebarea {question.position}
        </span>
        <span className={`type-badge ${isCG ? "badge-cg" : "badge-cs"}`}>
          {isCG ? "CG" : "CS"}
        </span>
        {question.topic && (
          <span className="topic-label">{question.topic}</span>
        )}
        {question.year && (
          <span className="year-label">{question.year}</span>
        )}
        {pageRef && (
          <span className="page-label">{pageRef}</span>
        )}
        <button
          className="report-flag-btn"
          onClick={() => setShowReport(true)}
          title="Raporteaza o problema"
          type="button"
        >
          &#9873;
        </button>
      </div>

      <p className="question-text">{question.text}</p>

      {isCG && statementKeys.length > 0 && (
        <ol className="cg-statements">
          {statementKeys.map((k) => (
            <li
              key={k}
              className={
                showResult && result.correct_statements?.includes(Number(k))
                  ? "statement-correct"
                  : ""
              }
            >
              {question.choices[k]}
            </li>
          ))}
        </ol>
      )}

      <div className="choices-list">
        {answerKeys.map((key) => (
          <label
            key={key}
            className={`choice-row ${getChoiceClass(key)}`}
          >
            <input
              type="radio"
              name={`q-${question.session_question_id}`}
              value={key}
              checked={selectedAnswer === key}
              onChange={() => onSelectAnswer(key)}
              disabled={confirmed}
            />
            <span className="choice-letter">{key}</span>
            <span className="choice-text">
              {isCG ? CG_LEGEND[key] : question.choices[key]}
            </span>
          </label>
        ))}
      </div>

      {showResult && result.correct_statements && (
        <div className="correct-statements-info">
          Afirmatii corecte: {result.correct_statements.join(", ")}
        </div>
      )}

      <div className="question-actions">
        {!confirmed && !examMode && (
          <button
            className="btn btn-primary"
            onClick={onConfirm}
            disabled={!selectedAnswer}
          >
            Confirma
          </button>
        )}
        {sourceFile && (
          <button
            className="btn btn-secondary"
            onClick={handlePdfOpen}
            type="button"
          >
            Vezi in PDF
          </button>
        )}
      </div>
      {showReport && (
        <ReportModal
          onClose={() => setShowReport(false)}
          questionId={question.question_id}
          sourceFile={sourceFile}
          pageRef={pageRef}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify compilation and test in browser**

Run: `cd webapp/frontend && npx tsc --noEmit`
Expected: no errors

Test: select an answer (should pop), confirm correct answer (should glow green), confirm wrong answer (should shake).

- [ ] **Step 3: Commit**

```bash
git add webapp/frontend/src/components/QuestionCard.tsx
git commit -m "feat: add pop, glow, and shake animations to answer choices"
```

---

### Task 10: Results Page — Score Count-Up, Confetti, Banner Message

**Files:**
- Modify: `webapp/frontend/src/pages/Results.tsx`
- Modify: `webapp/frontend/src/index.css` (results banner styles)

- [ ] **Step 1: Add results banner CSS**

Append to `webapp/frontend/src/index.css`:

```css
/* ------ Results Banner ------ */

.results-banner {
  text-align: center;
  padding: 0.875rem 1.25rem;
  border-radius: var(--radius);
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
}

.results-banner-excellent {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.results-banner-good {
  background: var(--color-badge-cs-bg);
  color: var(--color-cs);
  border: 1px solid var(--color-cs);
}

.results-banner-decent {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.results-banner-encourage {
  background: var(--color-bg-muted);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}
```

- [ ] **Step 2: Update Results.tsx with count-up, confetti, and banner**

Replace the full content of `webapp/frontend/src/pages/Results.tsx`:

```tsx
import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { completeQuiz, generateReviewQuiz } from "../api";
import { getResultBanner } from "../messages";
import Confetti from "../components/Confetti";

interface QuestionResult {
  question_id: string;
  position: number;
  text: string;
  type: string;
  choices: Record<string, string>;
  correct_answer: string;
  correct_statements: number[] | null;
  user_answer: string | null;
  is_correct: boolean;
  time_spent_ms: number | null;
}

interface CompletionResult {
  session_id: number;
  completed_at: string;
  total_questions: number;
  total_answered: number;
  correct_count: number;
  accuracy: number;
  results: QuestionResult[];
}

function useCountUp(target: number, duration = 1000): number {
  const [value, setValue] = useState(0);
  const startRef = useRef<number | null>(null);
  const rafRef = useRef<number>(0);

  const animate = useCallback(
    (timestamp: number) => {
      if (startRef.current === null) startRef.current = timestamp;
      const elapsed = timestamp - startRef.current;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      }
    },
    [target, duration]
  );

  useEffect(() => {
    if (target === 0) return;
    startRef.current = null;
    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, animate]);

  return value;
}

export default function Results() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<CompletionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [barAnimated, setBarAnimated] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    completeQuiz(Number(sessionId))
      .then((res) => setData(res as CompletionResult))
      .catch(async (err) => {
        if (err instanceof Error && err.message.includes("400")) {
          try {
            const res = await completeQuiz(Number(sessionId));
            setData(res as CompletionResult);
          } catch {
            setError("Nu s-au putut incarca rezultatele.");
          }
        } else {
          setError(
            err instanceof Error ? err.message : "Eroare la incarcarea rezultatelor"
          );
        }
      })
      .finally(() => setLoading(false));
  }, [sessionId]);

  // Trigger bar animation after mount
  useEffect(() => {
    if (data) {
      const timer = setTimeout(() => setBarAnimated(true), 100);
      return () => clearTimeout(timer);
    }
  }, [data]);

  const displayCount = useCountUp(data?.correct_count ?? 0);

  async function handleReviewMistakes() {
    if (!data) return;
    const wrongCount = data.results.filter((r) => !r.is_correct).length;
    if (wrongCount === 0) return;
    setReviewLoading(true);
    try {
      const result = await generateReviewQuiz({ count: wrongCount });
      navigate(`/quiz/${result.session_id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Eroare la generare review"
      );
    } finally {
      setReviewLoading(false);
    }
  }

  if (loading) return <div className="loading">Se incarca rezultatele...</div>;
  if (error) return <div className="page-error">{error}</div>;
  if (!data) return <div className="page-error">Rezultate indisponibile.</div>;

  const pct = Math.round(data.accuracy * 100);
  const wrongCount = data.results.filter((r) => !r.is_correct).length;
  const unansweredCount = data.results.filter(
    (r) => r.user_answer === null
  ).length;
  const banner = getResultBanner(data.accuracy);
  const showConfetti = data.accuracy >= 0.9;

  return (
    <div className="results-page">
      {showConfetti && <Confetti />}
      <div className="results-card">
        <h1 className="anim-fade-slide-up">Rezultate</h1>

        <div className={`results-banner results-banner-${banner.tone} anim-fade-slide-up`} style={{ animationDelay: "0.1s" }}>
          {banner.text}
        </div>

        <div className="results-summary anim-fade-slide-up" style={{ animationDelay: "0.2s" }}>
          <div className="score-display anim-count-up">
            <span className="score-number">{displayCount}</span>
            <span className="score-divider">/</span>
            <span className="score-total">{data.total_questions}</span>
          </div>
          <div className="accuracy-bar">
            <div
              className="accuracy-fill"
              style={{
                width: barAnimated ? `${pct}%` : "0%",
                background:
                  pct >= 70
                    ? "var(--color-success)"
                    : pct >= 50
                      ? "var(--color-warning)"
                      : "var(--color-error)",
                transition: "width 1s cubic-bezier(0.34, 1.56, 0.64, 1)",
              }}
            />
          </div>
          <div className="accuracy-label">{pct}% corect</div>
          <div className="results-meta">
            <span>Raspunse: {data.total_answered}</span>
            {unansweredCount > 0 && (
              <span>Fara raspuns: {unansweredCount}</span>
            )}
            <span>Gresite: {wrongCount}</span>
          </div>
        </div>

        <div className="results-actions anim-fade-slide-up" style={{ animationDelay: "0.3s" }}>
          {wrongCount > 0 && (
            <button
              className="btn btn-primary"
              onClick={handleReviewMistakes}
              disabled={reviewLoading}
              type="button"
            >
              {reviewLoading ? "Se genereaza..." : `Exerseaza punctele slabe (${wrongCount})`}
            </button>
          )}
          <button
            className="btn btn-secondary"
            onClick={() => navigate("/dashboard")}
            type="button"
          >
            Inapoi la Dashboard
          </button>
        </div>

        <h2 className="results-list-title anim-fade-slide-up" style={{ animationDelay: "0.4s" }}>Detalii intrebari</h2>
        <div className="results-list">
          {data.results.map((r, i) => {
            const isCG = r.type === "complement_grupat";
            const rowClass = r.user_answer === null
              ? "result-row result-unanswered"
              : r.is_correct
                ? "result-row result-correct"
                : "result-row result-wrong";
            const expanded = expandedId === r.question_id;

            return (
              <div
                key={r.question_id}
                className={`${rowClass} anim-fade-slide-up`}
                style={{ animationDelay: `${0.4 + Math.min(i, 10) * 0.03}s` }}
              >
                <div
                  className="result-row-header"
                  onClick={() =>
                    setExpandedId(expanded ? null : r.question_id)
                  }
                >
                  <span className="result-position">{r.position}.</span>
                  <span className="result-text-preview">
                    {r.text.length > 100
                      ? r.text.slice(0, 100) + "..."
                      : r.text}
                  </span>
                  <span
                    className={`type-badge ${isCG ? "badge-cg" : "badge-cs"}`}
                  >
                    {isCG ? "CG" : "CS"}
                  </span>
                  <span className="result-answers">
                    {r.user_answer ?? "-"} / {r.correct_answer}
                  </span>
                  <span className="result-expand">
                    {expanded ? "\u25B2" : "\u25BC"}
                  </span>
                </div>
                {expanded && (
                  <div className="result-row-detail">
                    <p className="detail-question-text">{r.text}</p>
                    <div className="detail-choices">
                      {Object.entries(r.choices).map(([key, val]) => {
                        let cls = "detail-choice";
                        if (key === r.correct_answer) cls += " detail-correct";
                        if (
                          key === r.user_answer &&
                          key !== r.correct_answer
                        )
                          cls += " detail-wrong";
                        return (
                          <div key={key} className={cls}>
                            <strong>{key}.</strong> {val}
                          </div>
                        );
                      })}
                    </div>
                    {r.correct_statements && (
                      <p className="detail-statements">
                        Afirmatii corecte: {r.correct_statements.join(", ")}
                      </p>
                    )}
                    {r.time_spent_ms != null && (
                      <p className="detail-time">
                        Timp: {(r.time_spent_ms / 1000).toFixed(1)}s
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify compilation**

Run: `cd webapp/frontend && npx tsc --noEmit`
Expected: no errors

Open results page in browser. Verify: score counts up, accuracy bar fills, banner message shows, confetti appears for 90%+ scores.

- [ ] **Step 4: Commit**

```bash
git add webapp/frontend/src/pages/Results.tsx webapp/frontend/src/index.css
git commit -m "feat: add score count-up, confetti, and encouraging banner to results page"
```

---

### Task 11: Backend — Study Streak and Accuracy Trend

**Files:**
- Modify: `webapp/backend/routes.py:364-417`

- [ ] **Step 1: Update the stats endpoint to include streak and accuracy trend**

In `webapp/backend/routes.py`, replace the `get_stats` function (lines 364-417) with:

```python
@router.get("/api/stats")
def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Fetch all answers for user
    rows = (
        db.query(QuizSessionQuestion.question_id, QuizAnswer.user_answer)
        .join(QuizAnswer, QuizAnswer.session_question_id == QuizSessionQuestion.id)
        .join(QuizSession, QuizSession.id == QuizSessionQuestion.session_id)
        .filter(QuizSession.user_id == current_user.id)
        .all()
    )

    total = 0
    correct = 0
    by_topic: dict[str, dict] = {}
    by_year: dict[int, dict] = {}

    for question_id, user_answer in rows:
        q = quiz_service.get_question(question_id)
        if not q:
            continue

        total += 1
        is_correct = q.get("correct_answer") == user_answer
        if is_correct:
            correct += 1

        topic = q.get("topic", "unknown")
        if topic not in by_topic:
            by_topic[topic] = {"total": 0, "correct": 0}
        by_topic[topic]["total"] += 1
        if is_correct:
            by_topic[topic]["correct"] += 1

        year = q.get("year")
        if year is not None:
            if year not in by_year:
                by_year[year] = {"total": 0, "correct": 0}
            by_year[year]["total"] += 1
            if is_correct:
                by_year[year]["correct"] += 1

    # Compute study streak: consecutive days with at least one completed session
    import datetime as _dt
    completed_dates = (
        db.query(func.date(QuizSession.completed_at))
        .filter(QuizSession.user_id == current_user.id, QuizSession.completed_at.isnot(None))
        .distinct()
        .order_by(func.date(QuizSession.completed_at).desc())
        .all()
    )
    study_streak = 0
    today = _dt.date.today()
    check_date = today
    for (d,) in completed_dates:
        if isinstance(d, str):
            d = _dt.date.fromisoformat(d)
        if d == check_date:
            study_streak += 1
            check_date -= _dt.timedelta(days=1)
        elif d < check_date:
            break

    # Compute accuracy trend: this month vs last month
    now = _dt.datetime.utcnow()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    first_of_last_month = (first_of_month - _dt.timedelta(days=1)).replace(day=1)

    def _month_accuracy(start: _dt.datetime, end: _dt.datetime) -> float | None:
        month_rows = (
            db.query(QuizSessionQuestion.question_id, QuizAnswer.user_answer)
            .join(QuizAnswer, QuizAnswer.session_question_id == QuizSessionQuestion.id)
            .join(QuizSession, QuizSession.id == QuizSessionQuestion.session_id)
            .filter(
                QuizSession.user_id == current_user.id,
                QuizAnswer.answered_at >= start,
                QuizAnswer.answered_at < end,
            )
            .all()
        )
        if not month_rows:
            return None
        m_correct = sum(
            1 for qid, ua in month_rows
            if (qq := quiz_service.get_question(qid)) and qq.get("correct_answer") == ua
        )
        return m_correct / len(month_rows)

    this_month_acc = _month_accuracy(first_of_month, now)
    last_month_acc = _month_accuracy(first_of_last_month, first_of_month)
    accuracy_trend = 0.0
    if this_month_acc is not None and last_month_acc is not None and last_month_acc > 0:
        accuracy_trend = this_month_acc - last_month_acc

    return {
        "total_answered": total,
        "total_correct": correct,
        "accuracy": correct / total if total > 0 else 0,
        "study_streak": study_streak,
        "accuracy_trend": accuracy_trend,
        "by_topic": {
            k: {**v, "accuracy": v["correct"] / v["total"] if v["total"] > 0 else 0}
            for k, v in sorted(by_topic.items())
        },
        "by_year": {
            k: {**v, "accuracy": v["correct"] / v["total"] if v["total"] > 0 else 0}
            for k, v in sorted(by_year.items())
        },
    }
```

- [ ] **Step 2: Ensure `func` is imported from sqlalchemy**

Check that `from sqlalchemy import func` (or `from sqlalchemy.sql import func`) is present in the imports at the top of `routes.py`. If not, add it.

- [ ] **Step 3: Verify the backend starts without errors**

Run: `cd webapp/backend && python -c "from routes import router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Test the endpoint**

Start the backend, call `GET /api/stats` with a valid auth token. Verify the response now includes `study_streak` (integer) and `accuracy_trend` (float).

- [ ] **Step 5: Commit**

```bash
git add webapp/backend/routes.py
git commit -m "feat: add study_streak and accuracy_trend to stats endpoint"
```

---

### Task 12: Integration Testing and Final Verification

**Files:** None new — this is verification only.

- [ ] **Step 1: Run TypeScript type check**

Run: `cd webapp/frontend && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 2: Start backend and frontend dev servers**

Run backend: `cd webapp/backend && uvicorn main:app --reload --port 8000`
Run frontend: `cd webapp/frontend && npm run dev`

- [ ] **Step 3: Test theme toggle**

1. Open the app in a browser
2. Click the sun icon — should force light mode
3. Click the moon icon — should force dark mode
4. Click the monitor icon — should follow OS preference
5. Refresh — theme should persist
6. Verify no flash of wrong theme on reload

- [ ] **Step 4: Test quiz encouraging messages**

1. Start a quiz and answer a question correctly — verify green toast appears
2. Answer correctly 3 times in a row — verify streak message
3. Answer incorrectly — verify warm/orange encouraging toast
4. Verify toasts auto-dismiss after ~2 seconds
5. Verify only one toast at a time

- [ ] **Step 5: Test results page**

1. Complete a quiz and navigate to results
2. Verify score counts up from 0
3. Verify accuracy bar fills progressively
4. Verify Romanian banner message matches score tier
5. If score >= 90%, verify confetti appears and disappears after ~3s
6. Verify result rows stagger in

- [ ] **Step 6: Test dashboard**

1. Navigate to dashboard
2. Verify stat cards bounce in with stagger
3. Verify sections fade in with stagger
4. Verify theme toggle is in header
5. If study streak >= 3, verify streak message appears
6. If total_answered hits a milestone, verify milestone message

- [ ] **Step 7: Test animations**

1. Verify question card slides right when going forward, left when going back
2. Verify answer selection has a subtle pop
3. Verify correct answer has green glow
4. Verify wrong answer shakes
5. Verify cards have hover lift effect
6. Verify buttons have scale-down on press

- [ ] **Step 8: Test mobile responsiveness**

1. Open in mobile view (or resize browser)
2. Verify toast appears at bottom-center
3. Verify theme toggle still fits in header
4. Verify all animations work on mobile
5. Verify no horizontal overflow from animations

- [ ] **Step 9: Test reduced motion preference**

1. Enable "reduce motion" in OS accessibility settings
2. Verify all animations are disabled — elements appear instantly
3. Verify the app is still fully functional

- [ ] **Step 10: Commit any fixes**

If any issues were found and fixed during testing:

```bash
git add -A
git commit -m "fix: address integration testing issues"
```
