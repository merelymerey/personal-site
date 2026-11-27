# Debugging prompt

Tool: Claude Code (model Claude Fable 5.2). Date: 2026-11-27.

---

Fix the verified defects listed below in `/Users/admin/personal-site`. Each was found by the code review (`ai/03-review-response.md`, finding numbers given) or by looking at the page, and was confirmed in the code by the author before this prompt was written.

## Context to read

`AGENTS.md`, `docs/01-requirements.md`, then the files named in each item. Tests: `tests/test_site.py`, run with `python3 -m unittest discover tests -v` (45 pass now).

## Method

For every defect that a static test can detect, first add a failing regression test to `tests/test_site.py` named after the AC or NFR, confirm it fails, then fix the code, then confirm the whole suite passes. Say in the report which tests were red first.

## Defects

- **D-01 (review 1, AC-10/AC-11).** `src/assets/css/style.css` line 631: `.form-status:empty { display: none }` hides the live region until text arrives, so screen readers may not announce the result. Keep the region rendered when empty and move spacing to the state classes.
- **D-02 (review 7, NFR-03).** `build.py` line 181: the language switch hides its visible label (`KK`, `RU`, `EN`) from assistive technology, so the accessible name does not contain the visible text. Make the name start with the visible label followed by the language name.
- **D-03 (review 5, AC-09).** Honeypot field is named `website` in `build.py` line 380 and `src/contact.php` line 265, which autofill tools fill in. Rename it to a neutral name in both places and in the tests. Keep the 400 response.
- **D-04 (review 2, NFR-05).** `src/contact.php`: the rate-limit hit is recorded before `store_message()` runs, so a failed store still blocks the retry; and `messages.jsonl` can grow without limit. Record the hit only after a successful store, and refuse with `storage_failed` when the file is larger than 1 MB. Do not add a global hourly counter.
- **D-05 (review 9, NFR-05).** `src/contact.php` accepts cross-site posts. Reject with 400 when an `Origin` header is present and its host differs from `HTTP_HOST`.
- **D-06 (review 10, NFR-05).** `src/contact.php`: switch `display_errors` off at the top of the file.
- **D-07 (review 11, NFR-05).** `src/contact.php` `clean` function: also strip Unicode format characters (`\p{Cf}`) before measuring length.
- **D-08 (review 6, AC-14).** The privacy statement says the hashed address record is kept "for a short time", but entries are pruned only when the next message arrives. Fix the code so that the statement is true: prune expired entries on every request that reaches `contact.php`, and when no live entries remain write an empty list with a fresh salt. Then reword the fourth privacy item in all three content files to say plainly what happens (a salted hash of the network address is kept for up to 30 seconds of activity and is replaced when the next request arrives; the address itself is never stored). Keep it honest rather than reassuring.
- **D-09 (review 23, AC-12).** `src/assets/js/main.js` line 178: disabling the focused submit button can drop keyboard focus. Use `aria-disabled` with the existing guard and style it like the disabled state.
- **D-10 (visual, NFR-01).** On the contact page at 360 px the submit button touches the privacy box below it (see `docs/evidence/v0-mobile-contact-kk.png`). Add vertical space between the form and the privacy section.
- **D-11 (review 4, content).** `content/ru.json`: the undeclined name in genitive and instrumental phrases ("Личный сайт Мерей Бахытжан", "связаться с Мерей Бахытжан") implies a gender. Rephrase the six strings so the name stays in the nominative, for example "Мерей Бахытжан: образование, …".
- **D-12 (review 22, content).** Soften the overstatement in the home introduction in all three languages to "I am learning backend development in Python and build Telegram bots and AI-assisted tools" (natural equivalents in Russian and Kazakh). In `ru.json` replace "инструменты с помощью ИИ" with "инструменты на основе ИИ". In `kk.json` use "Есіміңіз" for the name label and its validation messages, and replace "деңгей бағасынсыз" with "деңгейі көрсетілмеген". Change the achievements text in all three languages to singular school-olympiad participation without the word "subject".

## Rules

- Do not refactor beyond these items; a separate step follows.
- `contact.php` cannot be run here (no PHP). Re-read every changed PHP line for syntax and `strict_types` errors and say so in the report.
- Do not commit.

## Report back

For each defect: root cause in one sentence, files and lines changed, the regression test (or why none is possible), and anything you could not verify.
