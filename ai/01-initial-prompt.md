# Initial implementation prompt

Tool: Claude Code (model Claude Fable 5.2). Date: 2026-11-27.
This is the exact prompt given to the coding agent to generate the first version of the site.

---

You are generating the first working version of a static trilingual personal website. Work in the repository at `/Users/admin/personal-site`.

## Read first (context)

1. `AGENTS.md`: scope, repository map, commands, conventions, content rules, acceptance criteria. Follow it exactly.
2. `docs/01-requirements.md`: FR-01 to FR-12, NFR-01 to NFR-08, acceptance criteria AC-01 to AC-15.
3. `docs/03-design.md`: sitemap, architecture, language switching, storage, design decisions.
4. `docs/wireframes/desktop.svg` and `docs/wireframes/mobile.svg`: layout intent.
5. `docs/02-content-privacy-ethics.md`: what may and may not be published.

## Facts about the author (use only these, invent nothing)

- Name: Merey Bakhytzhan. Role line: Software Engineering student at KBTU.
- University: Kazakh-British Technical University (KBTU), Almaty. Major: Software Engineering. 3rd year (2026/27).
- School: Bereke School, Almaty, graduated in 2024.
- Learning portfolio, all in progress in the Fall 2026 semester:
  - Software Engineering: requirements, UML modelling, testing, agile planning, AI-assisted development.
  - Differential Equations: first- and second-order equations, methods of solution.
  - Fundamentals of Electrical Engineering I: circuit analysis, laboratory work with measurements.
  - Computer Architecture: processor design, pipelining, memory hierarchy, performance.
  - System Administration 1: Linux command line, users and permissions, services, SSH.
  - Philosophy.
- Tools the author works with (no skill levels): Python, FastAPI, Django, PostgreSQL, Docker, Git, REST APIs, Telegram bots, LLM APIs.
- Projects:
  1. Merey Job Finder (featured): a Telegram bot that searches vacancies on hh.kz by the user's profile (position, skills, city or remote, salary, experience), shows a skills-match percentage on every vacancy card with the skills the user has and the ones to learn, keeps a favourites list, and sends a daily digest of new vacancies without repeats at a time the user chooses. Link: https://t.me/merey_jobfinder_bot
  2. Smart Campus Room Availability Checker: a course project that checks whether a campus room can be booked for a time slot; a Python booking rule plus a web prototype. Link: https://github.com/merelymerey/smart-campus-a3
  3. «Шаг» ("Step"): an anti-procrastination web app that helps start a task with one small step; the public repository is a sanitised copy prepared for a risk-register assignment. Link: https://github.com/merelymerey/shag-a5
- Interests: no single fixed hobby; the author picks up whatever is interesting at the moment. Lately that is backend development in Python, Telegram bots and AI-assisted tools.
- Achievements: took part in subject olympiads during school years (no titles claimed).
- Extracurricular: volunteering at KBTU during the first year.
- Future plans: to apply to a university programme in a different major, and to keep building practical software projects.
- Contact: GitHub https://github.com/merelymerey and the contact form. No e-mail, phone or personal Telegram.

## What to build

1. `content/shared.json`, `content/en.json`, `content/ru.json`, `content/kk.json` with identical keys in the three language files. Include page titles, meta descriptions, navigation labels, all page text, form labels, hints, validation messages, status messages, privacy statement, 404 text, footer text and ARIA labels. Write natural Kazakh and Russian, not word-for-word translations; avoid gendered past-tense verbs in first person.
2. `build.py`: standard library only. Renders `dist/{kk,ru,en}/{index,education,projects,activities,contact}.html`, `dist/index.html` (language gateway: saved `localStorage.lang`, then `navigator.languages`, then `en`; visible links for all three languages and a `noscript` fallback), `dist/404.html` (all three languages on one page), copies `src/assets` to `dist/assets`, `src/contact.php` to `dist/contact.php`, `src/htaccess/root.htaccess` to `dist/.htaccess` and `src/htaccess/data.htaccess` to `dist/data/.htaccess`. Each page has `<html lang>`, UTF-8 meta, viewport meta, title, description, `hreflang` alternates, skip link, header with navigation (`aria-current`) and language switch linking to the same page in the other languages, `main`, footer.
3. `src/assets/css/style.css`: original restrained design, light and dark via `prefers-color-scheme`, mobile-first, breakpoint about 760 px, contrast at least 4.5:1, visible `:focus-visible`, system font stack, subtle entrance animations only under `prefers-reduced-motion: no-preference`. No horizontal scroll at 320 px.
4. `src/assets/js/main.js`: menu button (`aria-expanded`, Escape closes), remember language on switch, contact form validation with localised messages taken from `data-` attributes rendered by `build.py`, focus on the first invalid field, `fetch` POST to `/contact.php`, localised success and error states in an `aria-live` region. With JavaScript off the form still posts normally.
5. `src/assets/img/avatar.svg` (original monogram "MB") and `src/assets/img/favicon.svg`.
6. `src/contact.php`: POST only; fields `name` (2 to 80 characters), `contact` (optional, up to 120), `message` (10 to 2000), `lang`, hidden honeypot `website` that must be empty; trims and validates on the server; rate limit of one message per 30 seconds per PHP session is not acceptable because the site must set no cookies, so rate-limit by a hashed IP entry in a small file instead; appends one JSON line (time, lang, name, contact, message) to `data/messages.jsonl` with `LOCK_EX`; never echoes input unescaped; returns JSON `{ok, error}` with status 200, 400, 405, 429 or 500 when the request has `Accept: application/json`, otherwise a minimal localised HTML result page with a link back. No secrets, no database, no mail.
7. `src/htaccess/root.htaccess`: UTF-8 default charset, `ErrorDocument 404 /404.html`, force HTTPS, deny directory listing, basic security headers if `mod_headers` is available. `src/htaccess/data.htaccess`: deny all web access.

## Constraints

- No external requests of any kind from the pages: no CDN, fonts, analytics or embeds.
- No dependencies. No files outside the map in `AGENTS.md`.
- Do not write tests yet; they are a separate step. Do run `python3 build.py` and fix errors until it succeeds.
- Do not commit; leave the working tree for review.

## Report back

List the files created with one line each, any requirement you could not fully meet, any assumption you made, and anything in the content you were unsure how to translate.
