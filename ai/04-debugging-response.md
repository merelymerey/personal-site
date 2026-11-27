# Response to the debugging prompt

Tool: Claude Code (model Claude Fable 5.2), coding agent. Date: 2026-11-27.
Prompt: `ai/04-debugging-prompt.md`. The agent's complete final report follows, unedited.

---

All 12 defects are fixed in `/Users/admin/personal-site`; the suite is at 57 tests, all passing (45 before, 12 new). Nothing is committed. `contact.php` was not executed (no PHP here), so every PHP change is verified by reading only.

## Red-first tests
All 12 new tests failed before the fixes and pass after. Two existing tests (`test_ac09_form_structure`, `test_nfr05_form_handler_validates_on_the_server`) were also updated for the honeypot rename.

Two of my new tests had pattern mistakes that I corrected after the fix:
- The D-08 regex needed `(?s)` to match across lines.
- The D-12 ban on "с помощью ИИ" also hit the legitimate SE subject text "разработка с помощью ИИ", so I narrowed it to "инструменты с помощью ИИ".

## Per defect

| ID | Root cause | Files changed | Regression test |
|---|---|---|---|
| D-01 | `.form-status:empty { display:none }` removed the live region from the accessibility tree until text arrived. | `src/assets/css/style.css` (`.form-status` block), `src/assets/js/main.js` (sending call) | `test_ac10_ac11_status_region_stays_rendered_while_empty` |
| D-02 | The visible `KK/RU/EN` label was `aria-hidden`, so the accessible name was only the language name. | `build.py` ~l.181 | `test_nfr03_language_switch_name_starts_with_visible_label` |
| D-03 | The honeypot was named `website`, which autofill tools complete. | `build.py` ~l.379, `src/contact.php` (honeypot read), tests | `test_ac09_honeypot_has_a_neutral_name` |
| D-04 | The hit was written inside `rate_limited()` before `store_message()`, and the message file had no size cap. | `src/contact.php` (rate functions, `store_message`, request tail) | `test_nfr05_rate_hit_is_recorded_only_after_a_successful_store` |
| D-05 | There was no Origin check. | `src/contact.php` (new `cross_site_request()`, called after the 405 check) | `test_nfr05_cross_site_posts_are_rejected` |
| D-06 | `display_errors` was left to the host default. | `src/contact.php` (after `declare`) | `test_nfr05_php_errors_are_not_displayed` |
| D-07 | `clean_field` stripped only `\p{Cc}`. | `src/contact.php` (`clean_field`) | `test_nfr05_format_characters_are_stripped_before_measuring` |
| D-08 | Pruning ran only inside the rate check of a valid submission, so the last hash stayed indefinitely. | `src/contact.php` (new `prune_rate_file()`), fourth privacy item in all three content files | `test_ac14_address_hash_statement_matches_the_handler` |
| D-09 | `submit.disabled = true` on the focused button can drop keyboard focus. | `src/assets/js/main.js` (submit handler), `src/assets/css/style.css` (`.button[disabled]` rule) | `test_ac12_submit_button_keeps_focus_while_sending` |
| D-10 | `.card { margin-top: 0 }` cancelled the `section` top margin on the privacy box. | `src/assets/css/style.css` (new `.privacy` rule after `.card`) | `test_nfr01_privacy_box_is_separated_from_the_form` |
| D-11 | The name sat in genitive and instrumental positions in six strings. | `content/ru.json` (five page descriptions, gateway description) | `test_nfr08_russian_name_stays_in_the_nominative` |
| D-12 | Overstated and awkward wording. | `content/en.json`, `content/ru.json`, `content/kk.json`, `src/contact.php` (kk `invalid` text) | `test_nfr08_reviewed_wording_is_not_reintroduced` |

## Details worth knowing

- **D-01:** "Sending…" previously had no state class, so I added an `is-pending` state to carry its spacing. The empty region now takes no room.
- **D-02:** the link text is now `KK<span class="visually-hidden"> Қазақша</span>`, giving the name "KK Қазақша".
- **D-03:** the new name and id are `hp_field` (the reviewer's suggestion). The 400 response is kept.
- **D-04:** `rate_limited()` is replaced by `rate_open`, `rate_read`, `rate_write`, `rate_close` and `rate_key`. The lock is held from the check through the store to the recording, so two requests from one address cannot both pass. The cap is `MAX_STORE_BYTES = 1048576`; `store_message` returns false above it, which gives 500 `storage_failed`. No global hourly counter was added.
- **D-04 behaviour change:** if writing the hit fails after the message is already stored, the reply is now 200, because the message was saved.
- **D-05:** an `Origin: null` header or a missing `Host` is treated as cross-site. Requests with no Origin header pass.
- **D-08:** pruning runs before the method check, so GET requests prune too. When no live entry remains, an empty list with a fresh salt is written. It does nothing until the first message has created the file.
- **D-08 wording (EN):** "To limit spam, the server keeps a salted hash of the sender's network address. The hash is used for 30 seconds and is deleted or replaced when the next request reaches the form after that, so when nobody visits it stays in the file longer. The address itself is never stored." RU and KK are equivalents. This goes slightly beyond the wording in the prompt by saying outright that the hash stays longer on a quiet site.
- **D-11:** the strings now read "Мерей Бахытжан, образование: …", "Мерей Бахытжан: личный сайт на …" and similar.
- **D-12:** the kk `invalid` text in `contact.php` ("ат" to "есім") was not listed in the prompt; I changed it because review finding 22 cites it. I left "атыңыз" in kk privacy item 1 and in `contact_hint` (there it means a messenger username).

## PHP re-read
I re-read every changed PHP line for syntax and `strict_types` errors and found none. Functions that take or return the file handle are deliberately untyped; the rest use `?array`, `bool`, `void` and `string`, so PHP 7.1 or newer is still required. `preg_replace`, `parse_url` and `filesize` results are checked with `is_string` or `=== false` before use.

## Not verified
- **PHP runtime behaviour:** locking, pruning, the 1 MB cap and the Origin check have not been run.
- **Host behaviour:** whether InfinityFree passes `Origin` and `Host` unchanged is unknown; a proxy that rewrites `Host` would make every form post return 400. Test on the host with one real submission.
- **D-01 and D-09:** no screen-reader or keyboard test was done; the tests are static only.
- **D-10:** I checked a headless Chrome screenshot and the gap is visible, but at 500 px width (Chrome's minimum window), not 360 px. The same CSS applies at both widths. `docs/evidence/` was not updated.
- **Kazakh wording:** the new intro ("…бэкенд әзірлеуді үйреніп жүрмін, сондай-ақ Telegram-боттар мен ЖИ көмегімен жұмыс істейтін құралдар жасаймын"), the privacy item ("тұз қосылған хеш") and "Мектеп олимпиадасына қатысу" need the author's review.
- **Client and server length mismatch:** the JS check still counts format characters that the server now strips, so a value padded with invisible characters passes in the browser and gets the server field error. I left this alone as out of scope.
