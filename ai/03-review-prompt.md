# Agentic code review prompt

Tool: Claude Code (model Claude Fable 5.2). Date: 2026-11-27.

---

Review the code of the static site in `/Users/admin/personal-site` at tag `v0-first-output`. You are a reviewer: do not modify any file.

## Context to read

- `AGENTS.md`: conventions and acceptance criteria the code must follow.
- `docs/01-requirements.md`: FR-01 to FR-12, NFR-01 to NFR-08, AC-01 to AC-15.
- `docs/02-content-privacy-ethics.md`: what may be published.
- `docs/03-design.md`: intended architecture and design decisions.
- Code under review: `build.py`, `content/*.json`, `src/assets/css/style.css`, `src/assets/js/main.js`, `src/contact.php`, `src/htaccess/root.htaccess`, `src/htaccess/data.htaccess`. Build with `python3 build.py` and inspect `dist/` where useful.

Hosting facts: InfinityFree free plan, Apache with PHP, files in `htdocs/`, no outgoing mail, `.htaccess` supported, HTTPS on the free subdomain. PHP is not installed on this machine, so `contact.php` has never been executed: read it with extra care.

## Review along four axes

1. **Requirements**: is each FR, NFR and AC actually met by the code? Name any that is missing, partial or contradicted.
2. **Security**: `contact.php` (input handling, file writes and locking, races, path handling, header and log injection, rate-limit bypass, information leaks, PHP syntax or runtime errors, behaviour when `data/` is not writable), `.htaccess` rules (HTTPS redirect loops behind a proxy, CSP correctness versus what the pages really load, exposure of `data/`), DOM handling in `main.js` (any `innerHTML` with untrusted data), external links.
3. **Accessibility**: landmarks, heading order, focus management, the menu button, form error association (`aria-describedby`, `aria-invalid`), live regions, contrast, reduced motion, behaviour without JavaScript, `lang` correctness.
4. **Maintainability**: duplication, dead code, hard-coded visible text outside `content/`, unclear names, fragile build logic, anything that will make adding a page or changing a string error-prone.

Also check content for claims that go beyond the facts listed in `ai/01-initial-prompt.md`, and Russian or Kazakh strings that are untranslated, misleading or use gendered first-person past tense.

## Output format

A numbered list of findings, most severe first. For each: severity (high / medium / low), axis, file and line, what is wrong, a concrete failure scenario, and a suggested fix. Only report things you verified in the code; mark anything you could not verify as "unverified". Finish with what you checked and found to be fine.
