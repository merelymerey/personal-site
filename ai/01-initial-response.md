# Response to the initial implementation prompt

Tool: Claude Code (model Claude Fable 5.2), coding agent. Date: 2026-11-27.
Prompt: `ai/01-initial-prompt.md`. The generated code is preserved as commit/tag `v0-first-output`.
The agent's complete final report follows, unedited.

---

First version of the site is generated in `/Users/admin/personal-site`; `python3 build.py` succeeds and writes 15 language pages plus `index.html` and `404.html`. Nothing is committed, and no tests were written. One thing is unverified: `contact.php` has never been executed or linted, because this machine has no PHP.

## What was checked
- **Layout:** headless Chrome at 320, 360, 768 and 1280 px on all 15 pages plus the 404 page (360 px with JS off, dark mode, for the gateway and one content page) showed no horizontal scroll and exactly one `h1` per content page.
- **Behaviour:** the menu button opens and closes (Escape works), the language switch keeps the same page, and the gateway follows the saved choice and then the browser language.
- **Form, client side:** empty submit shows Kazakh messages and focuses the first invalid field. Against the local preview server (no PHP) a valid submit shows the localised error state with the GitHub link.
- **JS off:** navigation stays open and the gateway shows its links and the `noscript` text.
- **Contrast:** all text colour pairs compute to at least 6.1:1 in both themes; input borders are about 4:1.
- **External URLs:** the built pages contain only the three project/profile links, as `<a>` targets.

## Files created
- `content/shared.json`: languages, page list, external URLs, subject and project lists with status, form limits, empty `site_url`.
- `content/en.json`, `content/ru.json`, `content/kk.json`: all visible text, identical keys.
- `build.py`: templates and renderer, standard library only; fails on key mismatch, empty strings or non-https external links.
- `src/assets/css/style.css`: light/dark design, mobile-first, 760 px breakpoint, animations only under `prefers-reduced-motion: no-preference`.
- `src/assets/js/main.js`: gateway redirect, language memory, menu, form validation and `fetch` submit.
- `src/assets/img/avatar.svg`, `src/assets/img/favicon.svg`: original MB monogram and icon.
- `src/contact.php`: the form handler as specified, with a salted hashed-IP rate limit and JSON or localised HTML responses.
- `src/htaccess/root.htaccess`: charset, 404 document, HTTPS redirect, no listings, security headers including a CSP.
- `src/htaccess/data.htaccess`: denies all web access.

## Requirements not fully met
- **`contact.php` untested:** status codes, rate limiting and file writing need a run on InfinityFree or a local PHP.
- **Result-page text is hard-coded in PHP:** the no-JS result page keeps its three-language strings inside `contact.php`, because the file is copied as-is and cannot read `content/*.json`. They duplicate the content files and must be kept in step by hand.
- **`hreflang` URLs are root-relative:** the production domain is unknown, so `site_url` is empty. Setting it in `shared.json` makes them absolute.
- **768 px header wraps for Kazakh and Russian:** the language switch drops to a second row there; it is a single row from about 1000 px.
- **Browser-language validation with JS off:** the form posts normally, but the browser's native messages are in the browser's language, not the page's.

## Assumptions
- **Name spelling:** Russian "Мерей Бахытжан", Kazakh "Мерей Бақытжан". The author should confirm.
- **Language switch placement:** it is always visible in the header on mobile, in a row under the brand, not hidden inside the collapsed menu as the mobile wireframe shows. I did this for FR-01 and NFR-02 (one-click switch).
- **Gateway script:** the redirect lives in `main.js`, triggered by a `data-gateway` attribute, so the CSP can forbid inline scripts.
- **URLs:** all are root-absolute (`/en/`, `/assets/...`), so the site must sit at the domain root and cannot be previewed from `file://`.
- **Rate limit:** it uses `REMOTE_ADDR` and creates `data/ratelimit.json` on the host at runtime, holding a random salt and hashes younger than 30 seconds. If the host proxies all traffic through one address, the limit becomes global.
- **Honeypot:** a filled honeypot returns 400 `invalid_request`.
- **Privacy statement:** it discloses the short-lived hashed address record and says "the code of this site sets no cookies". InfinityFree's own anti-bot check may set a cookie, so the wording should be checked on the live host.
- **Contact page links:** it shows GitHub and the public bot, as in the content inventory; the bot is labelled as a project demo, not a personal chat.
- **Philosophy:** no description was supplied, so it reads "A course of the Fall 2026 semester".
- **Extra headers and files:** CSP, `X-Frame-Options`, a deny rule for `.json`/`.jsonl`, and a `.htaccess` that `contact.php` recreates in `data/` if missing. No HSTS.

## Translations to review
- **Role line (Russian):** "Изучаю программную инженерию в КБТУ" avoids "студент/студентка".
- **Major:** "Программная инженерия (Software Engineering)" in Russian, "Бағдарламалық инженерия (Software Engineering)" in Kazakh.
- **University abbreviation:** "КБТУ" and "ҚБТУ" are used where English has "KBTU".
- **"Activities":** "Активности" in Russian, "Белсенділік" in Kazakh; extracurricular is "Сабақтан тыс істер".
- **"Apply to a programme":** "подать документы" / "құжат тапсыру".
- **Technical terms:** "sanitised copy" is "очищенная копия" / "тазартылған көшірме"; "risk register" is "реестр рисков" / "тәуекелдер тізілімі"; "pipelining" is "конвейерная обработка" / "конвейерлік өңдеу"; "AI-assisted" is "с помощью ИИ" / "ЖИ көмегімен".
- **In-progress status (Kazakh):** "Оқылып жатыр".
- **«Шаг»:** glossed as "Step" in English and «Қадам» in Kazakh, left unglossed in Russian.
- **Kazakh overall:** it needs a native read-through; it uses non-gendered past forms such as "оқыдым".
