# T6. Testing, security and quality

Test dates: 2026-11-27. Automated suite: `python3 -m unittest discover tests -v` (60 tests, all passing; output in `docs/evidence/unittest-local-2026-11-27.txt`). Hosted checks were run against `https://merey.freedev.app` in Chrome; raw output in `docs/evidence/hosted-responsive-2026-11-27.txt`, screenshots in `docs/evidence/live-*.png`.

## 1. Requirements traceability

Every acceptance criterion maps to at least one automated test and, where behaviour depends on a browser or the host, one hosted check (IDs H-xx are in section 2).

| AC | Requirement | Design element | Automated test(s) in `tests/test_site.py` | Hosted check | Result |
|---|---|---|---|---|---|
| AC-01 | FR-01, FR-11 | Gateway, landing hero | `test_ac01_gateway_links_to_all_language_homes`, `test_ac01_home_has_name_role_intro_and_language_switch` | H-01 | Pass |
| AC-02 | FR-09 | Per-language URL trees | `test_ac02_language_switch_points_to_same_page_in_each_language`, `test_ac02_nfr02_internal_links_resolve` | H-02, H-12 | Pass |
| AC-03 | NFR-08 | `head()` in `build.py` | `test_ac03_lang_attribute_and_charset`, `test_ac03_title_and_description_are_localised`, `test_ac03_kazakh_and_russian_pages_use_their_alphabets`, `test_nfr08_files_are_utf8_without_bom_or_mojibake` | H-02 | Pass |
| AC-04 | FR-02 | `education_timeline` | `test_ac04_education_shows_university_major_year_and_school` | H-02 | Pass |
| AC-05 | FR-03 | Subject list | `test_ac05_education_lists_every_subject_with_status` | H-02 | Pass |
| AC-06 | FR-05 | `external_link` | `test_ac06_external_links_are_https_and_open_safely_in_new_tab`, `test_ac06_every_project_is_on_each_projects_page`, `test_ac06_shared_links_are_https`, `test_ac06_server_result_page_link_follows_the_link_convention` | H-03 | Pass |
| AC-07 | NFR-01 | Mobile-first CSS, menu button | `test_nfr01_viewport_meta_on_every_page`, `test_nfr01_no_fixed_width_above_320px`, `test_ac12_menu_button_has_state_and_controls_navigation` | H-10, H-11 | Pass |
| AC-08 | NFR-01 | 760 px breakpoint | `test_ac08_stylesheet_has_min_width_breakpoint_with_inline_nav` | H-10 | Pass |
| AC-09 | FR-07 | `main.js` validation | `test_ac09_form_structure`, `test_ac09_ac10_ac11_localised_messages_for_every_key_the_script_uses`, `test_ac09_length_limits_match_between_page_script_and_server`, `test_ac09_honeypot_has_a_neutral_name` | H-05 | Pass |
| AC-10 | FR-07 | `contact.php` | `test_ac10_ac11_status_region_stays_rendered_while_empty`, `test_ac10_ac11_server_fallback_texts_match_content` | H-06 | Pass |
| AC-11 | FR-07 | Error states | same as AC-10, plus `test_nfr05_form_handler_validates_on_the_server` | H-07, H-08 | Pass |
| AC-12 | FR-10, NFR-03 | Skip link, focus styles | `test_ac12_skip_link_is_first_focusable_and_target_exists`, `test_ac12_submit_button_keeps_focus_while_sending`, `test_nfr03_focus_style_and_reduced_motion` | H-11, H-12 | Pass |
| AC-13 | NFR-03 | Layout function | `test_ac13_exactly_one_h1_and_heading_order`, `test_ac13_landmarks`, `test_ac13_images_have_alt_and_icons_are_hidden`, `test_ac13_form_controls_have_labels_and_aria_references_resolve`, `test_nfr03_language_switch_name_starts_with_visible_label`, `test_ac13_html_is_well_formed` | H-02 | Pass |
| AC-14 | FR-08, NFR-04 | Privacy section, no third parties | `test_ac14_privacy_statement_on_each_contact_page`, `test_ac14_no_insecure_or_third_party_resources`, `test_ac14_no_inline_handlers_scripts_or_styles`, `test_ac14_no_cookies_analytics_or_remote_calls_in_code`, `test_ac14_no_private_identifiers_in_dist`, `test_ac14_no_private_identifiers_in_content_sources`, `test_ac14_address_hash_statement_matches_the_handler` | H-09, H-13 | Pass, with one host limitation (H-09) |
| AC-15 | FR-12 | `404.html`, `.htaccess` | `test_ac15_404_page_links_to_each_language_home`, `test_ac15_404_page_uses_root_relative_urls`, `test_ac15_htaccess_declares_404_document` | H-04 | Pass |

Non-functional requirements without their own AC: NFR-05 (`test_nfr05_*`, nine tests, and H-07, H-08, H-14), NFR-06 (`test_nfr06_page_weight_under_budget`), NFR-07 (`test_nfr07_build_produces_expected_files`, `test_nfr05_generated_form_config`, `test_nfr05_config_string_escaping_round_trips`), NFR-08 (`test_nfr08_*`, four tests).

## 2. Executed tests on the deployed site

| ID | Area | Steps | Expected | Actual | Result |
|---|---|---|---|---|---|
| H-01 | Navigation, deployed site | Open `https://merey.freedev.app/` | Redirect to a language home page | Redirected to `/en/` (browser language English); hero, name, role and language switch shown | Pass |
| H-02 | Three languages | Fetch all 15 pages | Status 200, `lang` matches the directory, one `h1`, UTF-8, Kazakh letters intact | 15 of 15 pages: 200, correct `lang`, one `h1`, UTF-8 header, Kazakh letters present on `kk` pages | Pass |
| H-03 | Links and assets | Follow every internal link and asset from the 15 pages | All return 200 | 20 distinct URLs, none failing | Pass |
| H-04 | Error handling | Open `/no-such-page-xyz` | Status 404, page offers three language links | 404; links to `/kk/`, `/ru/`, `/en/` present | Pass |
| H-05 | Forms, validation | On `/kk/contact.html` submit the empty form | Kazakh messages, focus on the first invalid field | "Есіміңізді жазыңыз.", "Хабарлама жазыңыз."; focus on the name field; both fields `aria-invalid` | Pass |
| H-06 | Forms, success | Submit a valid message containing Kazakh letters | Confirmation in Kazakh | "Рақмет, хабарламаңыз сақталды. Жақын арада оқимын." | Pass |
| H-07 | Forms, rate limit | Submit a second message immediately | Localised rate-limit message, nothing stored | "Қысқа уақыт ішінде тым көп хабарлама жіберілді…" (HTTP 429) | Pass |
| H-08 | Error handling, server validation | POST directly: 1-character name; 5-character message; filled honeypot; 81-character name; markup in the name | 400 with an error code each time | `invalid_name`, `invalid_message`, `invalid_request`, `invalid_name`, `invalid_message`; `GET /contact.php` gives 405 | Pass |
| H-09 | Privacy | Read the cookies and network hosts of a page | No cookie from the site's code; only the site's own host contacted | Only host contacted: `merey.freedev.app`. One cookie, `__test`, set by InfinityFree's anti-bot check | Pass for the site's code; host limitation recorded as D-14 |
| H-10 | Responsive layouts | Load five pages at 320, 360, 768 and 1280 px | No horizontal overflow; menu button below 760 px only | 20 of 20 loads without overflow; button shown at 320 and 360, hidden at 768 and 1280 | Pass |
| H-11 | Accessibility, menu | At 360 px press the menu button, then Escape | `aria-expanded` true then false, navigation shown then hidden | Navigation hidden, then `aria-expanded="true"` and visible, then `false` after Escape | Pass |
| H-12 | Accessibility, navigation | On `/ru/education.html` inspect the first focusable element and the EN switch | Skip link first; EN leads to the same page | First focusable is the skip link to `#main`; EN points to `/en/education.html`; RU marked current | Pass |
| H-13 | Security, data exposure | Open `/data/`, `/data/messages.jsonl`, `/contact.config.php`, `/.htaccess` | Access denied | 403 Forbidden for all | Pass |
| H-14 | Security, HTTPS | Open `http://merey.freedev.app/ru/projects.html`; inspect the certificate and headers | Redirect to HTTPS; valid certificate; security headers | Redirected to `https://…`; certificate for `*.freedev.app` (ZeroSSL) valid; CSP `default-src 'self'`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` present | Pass |
| H-15 | Browser compatibility | Open the site in Chrome on macOS (desktop and emulated phone) | Renders and works | Works in Chrome 2026 desktop and emulated 360 px phone. Safari, Firefox and a real phone are covered by the manual session in section 4 | Partly done, see section 4 |

Fifteen hosted checks were executed in addition to the 60 automated tests.

## 3. Defect log

| ID | Found by | Defect | Correction | Verified by |
|---|---|---|---|---|
| D-01 | Code review | Form status region hidden while empty, so screen readers may miss the result | Region stays rendered; spacing moved to state classes | `test_ac10_ac11_status_region_stays_rendered_while_empty` |
| D-02 | Code review | Language switch name did not contain its visible label | Name is now "KK Қазақша" etc. | `test_nfr03_language_switch_name_starts_with_visible_label` |
| D-03 | Code review | Honeypot field named `website` could be autofilled | Renamed `hp_field` | `test_ac09_honeypot_has_a_neutral_name`, H-08 |
| D-04 | Code review | Rate-limit hit recorded before the message was stored; unlimited file growth | Hit recorded after a successful store; 1 MB cap | `test_nfr05_rate_hit_is_recorded_only_after_a_successful_store`, H-06, H-07 |
| D-05 | Code review | Cross-site posts accepted | `Origin` host must match | `test_nfr05_cross_site_posts_are_rejected` |
| D-06 | Code review | PHP errors could be displayed | `display_errors` off | `test_nfr05_php_errors_are_not_displayed` |
| D-07 | Code review | Invisible characters passed length checks | Format characters stripped | `test_nfr05_format_characters_are_stripped_before_measuring` |
| D-08 | Code review | Privacy statement promised more than the code did about the address hash | Pruning on every request; statement reworded | `test_ac14_address_hash_statement_matches_the_handler` |
| D-09 | Code review | Disabling the focused submit button could drop keyboard focus | `aria-disabled` instead | `test_ac12_submit_button_keeps_focus_while_sending` |
| D-10 | Screenshot of v0 | Submit button touched the privacy box on phones | Margin restored | `test_nfr01_privacy_box_is_separated_from_the_form`, screenshot |
| D-11 | Code review | Russian name forms implied a gender | Nominative phrasing | `test_nfr08_russian_name_stays_in_the_nominative` |
| D-12 | Code review | Introduction overstated experience; awkward Russian and Kazakh wording | Texts corrected | `test_nfr08_reviewed_wording_is_not_reintroduced` |
| D-13 | Automated test | Compressed image bytes matched the e-mail pattern (false positive) | Images are checked for metadata instead of text patterns | `test_ac14_no_private_identifiers_in_dist` |
| D-14 | Hosted check H-09 | Host sets a `__test` cookie although NFR-04 said "no cookies" | Cannot be removed on the free plan; NFR-04 and the privacy statement now disclose it | Privacy item 6 in all three languages |
| D-15 | Author review of v0 | Home page looked plain; palette disliked; ornament unwanted | Landing page rebuilt twice; palette changed; ornament removed | Screenshots `v0-*` against `live-*` |

## 4. Manual user testing with another person

Status: **pending**. The session is run by the author with one other person ("Tester 1") on the live site, using the script below. Results are written into the table by the author; nothing is filled in before the session takes place.

Script (about 10 minutes, on the tester's own phone and browser):

1. Open `https://merey.freedev.app`. Which language did you get? Is it clear whose site this is?
2. Switch to Kazakh, then Russian, then English from the projects page. Did you stay on the same page each time?
3. Find the school the author went to. How many taps did it take?
4. Open the Telegram bot link. Did it open in a new tab?
5. Send the contact form empty, then with a real message. Were the messages clear and in your language?
6. Read the privacy section. Is anything unclear or worrying?
7. Anything that looked broken, hard to read or hard to tap?

| Date | Device and browser | Task | Observation | Defect raised | Correction |
|---|---|---|---|---|---|
| | | | | | |

## 5. Security and dependability review

| Topic | Finding | Evidence |
|---|---|---|
| HTTPS | The free subdomain is served with a valid wildcard certificate; HTTP redirects to HTTPS. HSTS was considered and rejected (the certificate is controlled by the host). | H-14; `ai/evaluation.md`, rejected finding 12 |
| Input validation | Validated twice: in the browser for convenience and in `contact.php` for safety (length, UTF-8, control and format characters, honeypot, origin, rate). Output is escaped. | H-05 to H-08; `test_nfr05_*` |
| Secret handling | The project needs no secrets. The repository is scanned for token and key patterns by a test. The hosting password was generated by the host and never typed, stored or submitted by the project. | `test_nfr05_no_secrets_in_repository` |
| Authentication | None, by design (DD-3). No private content exists. | `docs/03-design.md` |
| Stored data | Messages and the rate file live in `data/`, closed by `.htaccess` and by a root rule for `.json` / `.jsonl`. | H-13 |
| Graceful failure | A server or network failure shows a localised error with the GitHub link and keeps the typed text. Without JavaScript the navigation is fully expanded; the host itself, however, requires JavaScript once for its anti-bot check. | Local preview without PHP; D-14 |
| Headers | `Content-Security-Policy: default-src 'self'`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`. | H-14 |
| Backup of source files | Git history on GitHub (`merelymerey/personal-site`), tagged release, plus the local working copy. The hosted `data/` folder is not backed up and holds nothing that needs to be kept. | `docs/05-launch.md` |
| Remaining risks | Shared free hosting can be slow or suspended; a determined spammer with many addresses can still fill the 1 MB message file; the Kazakh text needs a native review. | Section "Known limitations" in `docs/05-launch.md` |
