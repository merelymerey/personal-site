# Refactoring prompt

Tool: Claude Code (model Claude Fable 5.2). Date: 2026-11-27.

---

Refactor `/Users/admin/personal-site` to remove the duplication and fragility listed below without changing what visitors see or how the form behaves. The defects from `ai/04-debugging-prompt.md` are already fixed; do not undo them.

## Context to read

`AGENTS.md` (the rule "every visible string lives in `content/<lang>.json`" is the reason for this step), `docs/03-design.md`, `build.py`, `src/contact.php`, `src/assets/js/main.js`, `src/assets/css/style.css`, `content/*.json`, `tests/test_site.py`, and review findings 3, 13, 17, 18, 19 and 21 in `ai/03-review-response.md`.

## Changes

1. **Single source for server texts and limits (finding 3, 13).** `src/contact.php` hard-codes its localised result-page strings, the GitHub URL, the language list and the five length limits. Move the strings into `content/<lang>.json` under a new `result` key (same keys in all three files), and have `build.py` write a generated `dist/contact.config.php` that returns one PHP array with the texts, limits, languages and GitHub URL taken from `content/*.json` and `shared.json`. `contact.php` loads it with `require __DIR__ . '/contact.config.php'`. Generate PHP string literals safely: single-quoted, with backslash and single quote escaped. Deny direct web access to `contact.config.php` in `src/htaccess/root.htaccess`. The external link on the result page must follow the project convention (`target="_blank"`, `rel="noopener noreferrer"`, new-tab note from content).
2. **Hints that cannot drift (finding 3).** The hint and validation strings repeat the numeric limits in prose. Replace the numbers with `{min}` and `{max}` placeholders in the content files and substitute them from `shared.json` in `build.py` (and from the config in PHP).
3. **Validation limits rendered once (finding 18).** Remove `data-min` / `data-max`; read `minLength` / `maxLength` in `main.js`.
4. **Build validation and atomic output (finding 17).** Before rendering, check that every subject, project, page id and status in `shared.json` has matching content keys in all three languages and that no content subject or project is missing from `shared.json`; fail with a clear `BuildError` message. Build into a temporary directory and replace `dist/` only on success.
5. **Asterisk (finding 19).** Take the required-field marker from one place so the note and the marker cannot disagree.
6. **Dead code (finding 21).** Remove CSS classes without rules or rules without elements, the duplicate colour declaration, and unused function parameters.

## Rules

- Behaviour-preserving: apart from the generated config file, the placeholders being filled in, and removed unused attributes and classes, the built HTML must be the same as before. Diff `dist/` before and after and explain every difference in the report.
- Update tests that read the old PHP constants so they check the generated config instead; add a test that the config exists, contains the limits from `shared.json` and all `result` keys for the three languages, and is denied by `.htaccess`. The suite must pass.
- Update the repository map in `AGENTS.md` and the architecture section of `docs/03-design.md` for the generated file.
- PHP cannot be run here: re-read every PHP line you touch and state that you did.
- Do not commit.

## Report back

What changed per item, the `dist/` diff summary, test count and result, and anything unverified.
