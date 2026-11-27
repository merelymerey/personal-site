# Response to the refactoring prompt

Tool: Claude Code (model Claude Fable 5.2), coding agent. Date: 2026-11-27.
Prompt: `ai/05-refactoring-prompt.md`. The agent's complete final report follows, unedited.

---

The refactoring from `ai/05-refactoring-prompt.md` is done in `/Users/admin/personal-site`, nothing committed. The suite passes: 60 tests, OK (57 before, 3 added). PHP is not installed here, so `contact.php` and the generated config were never executed.

## What changed per item

**1. Single source for server texts and limits (findings 3, 13)**
- `build.py` now writes `dist/contact.config.php`: one returned array with `langs`, `default_lang`, `github_url`, `limits` (the five ints) and `texts` per language.
- `src/contact.php` loads it with `define('CONFIG', require __DIR__ . '/contact.config.php');`. The `TEXT` table, `LANGS`, `DEFAULT_LANG`, `GITHUB_URL` and the five limit constants are gone; `RATE_SECONDS`, `MAX_BODY_BYTES` and `MAX_STORE_BYTES` stay.
- PHP string literals are single-quoted with backslash and quote escaped (`php_string` in `build.py`).
- `src/htaccess/root.htaccess` denies the file with a `<Files "contact.config.php">` block (Apache 2.4 and 2.2 forms).
- The result-page GitHub link now has `target="_blank"`, `rel="noopener noreferrer"` and the hidden new-tab note from `a11y.new_tab`.
- **Deviation:** the new top-level `result` key holds only five strings (`title_ok`, `title_fail`, `invalid`, `method`, `back`). The other three server texts were already identical to `contact.form.success`, `error_rate` and `error`, so the config takes them from there instead of copying them into `result`.
- I checked by script that every moved string equals the old PHP literal.

**2. Hints that cannot drift**
- Hint and validation strings use `{min}` / `{max}`, filled in `build.py` from `shared.json`.
- `result.invalid` names all five limits, so it uses `{name_min}`, `{name_max}`, `{contact_max}`, `{message_min}`, `{message_max}`; PHP fills these from the config (`fill_limits`).
- An unknown placeholder fails the build.

**3. Limits rendered once (finding 18)**
- `data-min` / `data-max` are removed; `main.js` reads `field.minLength` / `field.maxLength` (treating -1 as absent).

**4. Build validation and atomic output (finding 17)**
- `validate_shared` and `validate_ids` check pages, subjects, statuses and projects against all three languages, and the reverse for subjects and projects. They also check that the limits are positive ints.
- The build goes into a `.dist-new-*` directory next to `dist/` and is swapped in only on success; `.gitignore` covers leftovers.
- On a scratch copy, eight broken inputs each gave a one-line `Build failed: …` message, and a mid-build failure (missing assets directory) left `dist/` untouched with no leftover directory.

**5. Asterisk (finding 19)**
- The marker is `form.required_marker` in `content/shared.json`; `required_note` uses `{marker}`, and the label marks render the same value.

**6. Dead code (finding 21)**
- Removed classes without rules: `hero-text`, `subject-body`, `status-in-progress`, `icon-menu`, `project-link`.
- Removed the `.button[disabled]` selector (no such element exists).
- Removed unused parameters: `lang` from `render_education` and `render_projects`, `shared` and `lang` from `render_activities`, `css_class` from `external_link`. The `RENDERERS` dict became `render_page()`.
- **Not removed:** the "duplicate" colour in `.card .badge`. The finding is wrong: without it `.card p` (muted) overrides `.badge`, and the badge would change colour. I left a comment saying so.
- `privacy` now has a rule from the defect fixes, so it stays.

**Docs:** the `AGENTS.md` repository map and conventions, and the architecture section of `docs/03-design.md`, describe the generated file and the placeholders.

## `dist/` diff
- **New:** `contact.config.php`.
- **17 HTML files:** `index.html` and `404.html` are byte-identical. The 15 language pages differ only by the five removed classes and, on the contact pages, the removed `data-min` / `data-max`. I confirmed this by stripping exactly those from the old build and comparing: 0 files differ. Filled placeholders give the same text as before.
- **`contact.php`, `main.js`, `.htaccess`:** the source changes above.
- **`style.css`:** one selector removed, one comment added.
- **Result page (PHP, not in the static diff):** the GitHub link gains `target="_blank"` and the new-tab note; the texts are otherwise the same.

## Tests
- Tests that read the old PHP constants now parse the generated config with a small parser in the test file.
- Three new tests: the config (exists, limits, all `result` keys for three languages, denied by `.htaccess`), PHP string escaping round-trip, and the result-page link convention. Existing tests were extended for the marker, the absence of `data-min` / `data-max`, and no numbers in hint strings.
- Six deliberate regressions on a scratch copy each failed the expected test.

## Unverified or left alone
- **PHP:** I re-read every touched line of `src/contact.php` (header comment, `define('CONFIG', …)`, `fill_limits`, `respond`, language selection, the limit checks) and the generated config. `define` with an array needs PHP 7.0 or newer; the file already needed 7.1.
- **Hosting:** whether InfinityFree allows `<Files>` in `.htaccess` is untested; it is the same directive class as the existing `<FilesMatch>`.
- **Browser:** `main.js` passes `node --check` only; `minLength` / `maxLength` were not exercised in a browser.
- **Kazakh suffixes:** "{min}-ден" and "{min}-нан" follow vowel harmony for the current numbers (2, 10). A changed limit may need the suffix edited by hand.
- **Rate period:** "30 seconds" and "half a minute" in the privacy and rate texts are still prose beside `RATE_SECONDS`; this was outside the listed limits. The existing test still ties the privacy text to the constant.
- **Other docs:** `README.md` and `docs/diagrams/component.puml` do not mention the generated config; they were not in scope.
