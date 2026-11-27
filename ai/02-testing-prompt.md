# Testing prompt

Tool: Claude Code (model Claude Fable 5.2). Date: 2026-11-27.

---

Write the automated test suite for the static site in `/Users/admin/personal-site`.

## Context to read

- `AGENTS.md` (conventions, commands, acceptance criteria).
- `docs/01-requirements.md`, section 5: acceptance criteria AC-01 to AC-15. Every test must name the AC or NFR it verifies.
- `build.py`, `content/*.json`, `src/assets/js/main.js`, `src/contact.php`, `src/htaccess/*.htaccess`.

## Task

Create `tests/test_site.py` using only `unittest` and the Python standard library (`html.parser`, `json`, `pathlib`, `re`, `subprocess`). `setUpModule` runs `python3 build.py` once. Tests read the files in `dist/`; no browser and no network.

Cover at least:

1. AC-01: gateway `dist/index.html` links to all three language home pages; each home page has the author's name in an `h1`, a role line and a language switch.
2. AC-02: on each of the 15 pages the language switch has three links pointing to the same file name in `/kk/`, `/ru/`, `/en/`, and the current language is marked.
3. AC-03 / NFR-08: `<html lang>` matches the directory; `<meta charset="utf-8">`; non-empty title and description that differ between languages; Kazakh pages contain Kazakh-specific letters (ә ғ қ ң ө ұ ү і); files decode as UTF-8; the three content files have identical key sets and no empty strings.
4. AC-04, AC-05: education pages contain the university, major, year and school values from the content file, and one entry per subject in `shared.json` with a status.
5. AC-06: every external link is `https`, has `target="_blank"` and `rel` containing `noopener`; every project in `shared.json` appears on each projects page.
6. Links (AC-02, NFR-02): every internal `href` and `src` on every page resolves to a file in `dist/`; every page links to all five pages of its language; exactly one `aria-current="page"` in the primary navigation.
7. AC-07, AC-08 / NFR-01: viewport meta present; stylesheet contains a `min-width` media query and no fixed widths above 320 px on layout containers (a simple static check is enough; browser checks are done separately).
8. AC-09 to AC-11: the contact form has labelled `name`, `contact`, `message` fields, the honeypot, `method="post"`, an `aria-live` status region, and localised validation and status messages for every key the script uses; `contact.php` contains the same length limits as `shared.json`.
9. AC-12, AC-13 / NFR-03: skip link is the first focusable element and its target exists; exactly one `h1`; `header`, `nav`, `main`, `footer` present; every `img` has `alt`; every form control has a `label`; menu button has `aria-expanded` and `aria-controls` pointing to an existing id.
10. AC-14 / NFR-04: no `http://` or `//` resources, no `<script src>` or `<link href>` to another origin, no inline event handlers, no `document.cookie` in the script; the privacy section exists on each contact page; no e-mail address, phone-number pattern or student-ID pattern (`\d{2}[A-Z]\d{6}`) anywhere in `dist/`.
11. AC-15: `dist/404.html` exists and links to the three language home pages; `.htaccess` declares it as the 404 document.
12. NFR-05: `dist/data/.htaccess` denies access; `dist/.htaccess` forces HTTPS; no file in the repository tree (excluding `.git` and `dist`) matches common secret patterns (bot tokens, `sk-` keys, `password=`).
13. NFR-06: for each page, HTML + CSS + JS + referenced images total under 150 KB.

## Rules

- Parameterise over languages and pages with `subTest`; do not copy-paste per language.
- A test must fail for the right reason: for at least three tests, temporarily break the site, confirm the test fails, restore, and say which ones you checked.
- Do not change any file outside `tests/`. If a test exposes a real defect in the site, leave the test failing and report it; do not weaken the test and do not fix the site.
- Do not commit.

## Report back

The exact command and its final output summary, the list of tests with the AC/NFR each covers, which tests you mutation-checked, and every defect found with file and line.
