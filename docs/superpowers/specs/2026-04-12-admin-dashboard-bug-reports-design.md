# Admin Dashboard & Bug Reports — Design Spec

## Overview

Add an admin dashboard for managing quiz data files and reviewing user-submitted bug reports. Add a bug reporting flow for regular users to flag issues with specific questions or the app in general.

## Admin Authentication

- New env var: `ADMIN_USERNAME` (e.g. `ADMIN_USERNAME=rares`)
- `is_admin(user)` helper checks `user.username == os.environ.get("ADMIN_USERNAME")`
- All `/api/admin/*` routes use `Depends(get_admin_user)` which returns 403 for non-admins
- `/api/auth/me` response gains an `is_admin: bool` field so the frontend can show/hide admin UI
- The frontend flag is cosmetic only — the backend is the security boundary
- No changes to the `User` model

## Data Model

### New table: `bug_reports`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | Auto-increment |
| `user_id` | Integer FK → users | Reporter |
| `question_id` | String, nullable | Null for general app bugs |
| `category` | String | One of: `wrong_answer`, `typo`, `missing_answer`, `app_bug`, `other` |
| `description` | Text | Free-form user description |
| `screenshot_path` | String, nullable | Disk path to uploaded screenshot |
| `status` | String | `open` or `resolved`, default `open` |
| `created_at` | DateTime | Auto-set on creation |

No changes to existing tables.

## API Endpoints

### Admin endpoints (all require `Depends(get_admin_user)`)

**File management:**

- `GET /api/admin/grile-info` — Returns metadata about current `grile.json`: file size, last modified timestamp, total question count, source count.
- `POST /api/admin/upload-grile` — Accepts multipart file upload of a new `grile.json`. Validates it parses as JSON, has a `sources` array, and each source has `tests` with `questions`. Rejects with 400 if validation fails. Replaces the current file and triggers `quiz_service.load_data()` to reload in-memory indexes.
- `GET /api/admin/pdfs` — Lists all PDF files in the PDF directory with filenames and file sizes.
- `POST /api/admin/upload-pdf` — Accepts multipart file upload of a PDF. Saves to the PDF directory.
- `DELETE /api/admin/pdf/{filename}` — Deletes a PDF file. Validates filename (no path traversal).
- `GET /api/admin/screenshots/{filename}` — Serves a screenshot file. Validates filename (no path traversal, images only).

**Bug reports:**

- `GET /api/admin/reports?status=open` — Lists bug reports, optionally filtered by status. Each report includes full question data inline (text, choices, correct_answer, type, source_file, year, topic, page_ref) when `question_id` is set.
- `PATCH /api/admin/reports/{id}` — Sets status to `resolved`.
- `DELETE /api/admin/reports/{id}` — Deletes a report and its screenshot file if present.

### User endpoint

- `POST /api/reports` — Submit a bug report. Auth required (regular user). Accepts multipart form with fields: `question_id` (optional), `category` (required), `description` (required), and an optional `screenshot` file. Screenshots are saved to a `screenshots/` subdirectory under the data path. Max file size: 5 MB. Accepted formats: JPEG, PNG, WebP.

## Frontend — Admin Dashboard

### Route

- `/admin` — protected route, only accessible when `is_admin` is true in auth context
- Redirect non-admins to `/dashboard`

### Layout

Tabbed single-page layout with three tabs:

**Tab 1: Bug Reports (default)**
- Filter toggle: Open / Resolved (pill buttons with counts)
- Report list: rows showing category, question ID (or "general"), reporter username, relative timestamp
- Resolve (checkmark) and Delete (X) action buttons per row
- Clicking a row expands it to show:
  - Full description text
  - Screenshot displayed inline (if attached)
  - When question_id is set: question text, all choices, correct answer, type, source file, year, topic, page ref, link to PDF

**Tab 2: Grile.json**
- Current file info: file size, last modified, total questions, number of sources
- Upload button to replace with a new file
- Confirmation dialog before replacing
- Success/error feedback after upload

**Tab 3: PDFs**
- List of PDF files with filenames and sizes
- Upload button for new PDFs
- Delete button per PDF with confirmation
- Success/error feedback

### Navigation

- Admin link visible in the app nav/header only when `is_admin` is true
- "Back to app" link within admin dashboard to return to `/dashboard`

## Frontend — Bug Reporting (Users)

### Report button on question cards

- Small flag/report icon in the corner of `QuestionCard.tsx`
- Clicking opens a modal

### Report modal

- **Category dropdown:** "Raspuns gresit", "Eroare in text", "Raspuns lipsa", "Bug aplicatie", "Altele"
- **Description textarea:** required, free-form
- **Screenshot upload:** optional file picker (images only)
- **Question context (read-only, when reporting from a question):** question ID, source file, page ref displayed so user confirms they're reporting the right thing
- **Submit button** — posts to `POST /api/reports`, closes modal on success with a brief toast/confirmation

### General feedback

- "Raporteaza o problema" link in the dashboard/nav area
- Opens the same modal but without a question attached
- Category defaults to "Bug aplicatie"

### No "My Reports" page — fire-and-forget from the user's perspective.

## Dark Mode Contrast

All new components must have good contrast ratios in dark mode. Additionally, the existing correct-answer indicator in `QuestionCard.tsx` has poor contrast in dark mode — fix it as part of this work when touching that component.

## Environment / Docker Changes

New env vars added to `docker-compose.yml`:
- `ADMIN_USERNAME` (no default — admin disabled if unset)

New volume/path considerations:
- Screenshots stored under the data volume at `/app/data/screenshots/`
- No new services or containers

## Out of Scope

- Admin roles / multiple admins
- User-visible report status tracking
- Pipeline integration (parse/patch/merge)
- Admin notes or priority on bug reports
- Notification system for new reports
