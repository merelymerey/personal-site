# Response to the testing prompt

Tool: Claude Code (model Claude Fable 5.2), coding agent. Date: 2026-11-27.
Prompt: `ai/02-testing-prompt.md`. The agent's complete final report follows, unedited.

---

The test suite is written at `/Users/admin/personal-site/tests/test_site.py` and all 45 tests pass against the current site. No test exposed a defect in the site. Nothing outside `tests/` was changed and nothing was committed.

## Command and result

```
cd /Users/admin/personal-site && python3 -m unittest discover tests -v
...
Ran 45 tests in 0.221s

OK
```

The suite uses only `unittest` and the standard library. `setUpModule` runs `build.py` once, and loops over languages and pages use `subTest`.

## Tests and the AC/NFR each covers

| Class | Test | Covers |
|---|---|---|
| TestBuildOutput | `test_nfr07_build_produces_expected_files` | NFR-07 |
| | `test_ac13_html_is_well_formed` | AC-13 / NFR-03 |
| TestHome | `test_ac01_gateway_links_to_all_language_homes` | AC-01 (FR-11) |
| | `test_ac01_home_has_name_role_intro_and_language_switch` | AC-01 |
| TestNavigation | `test_ac02_language_switch_points_to_same_page_in_each_language` | AC-02 |
| | `test_ac02_nfr02_internal_links_resolve` | AC-02 / NFR-02 |
| | `test_nfr02_primary_nav_links_all_pages_and_marks_current` | NFR-02 (FR-10) |
| TestInternationalisation | `test_nfr08_content_files_have_identical_keys_and_no_empty_strings` | NFR-08 |
| | `test_nfr08_files_are_utf8_without_bom_or_mojibake` | NFR-08 / AC-03 |
| | `test_ac03_lang_attribute_and_charset` | AC-03 / NFR-08 |
| | `test_ac03_title_and_description_are_localised` | AC-03 / NFR-08 |
| | `test_ac03_kazakh_and_russian_pages_use_their_alphabets` | AC-03 |
| TestEducation | `test_ac04_education_shows_university_major_year_and_school` | AC-04 |
| | `test_ac05_education_lists_every_subject_with_status` | AC-05 |
| TestExternalLinks | `test_ac06_external_links_are_https_and_open_safely_in_new_tab` | AC-06 |
| | `test_ac06_every_project_is_on_each_projects_page` | AC-06 |
| | `test_ac06_shared_links_are_https` | AC-06 |
| TestResponsive | `test_nfr01_viewport_meta_on_every_page` | AC-07 / NFR-01 |
| | `test_ac08_stylesheet_has_min_width_breakpoint_with_inline_nav` | AC-07 / AC-08 |
| | `test_nfr01_no_fixed_width_above_320px` | AC-07 / NFR-01 |
| TestContactForm | `test_ac09_form_structure` | AC-09 / AC-10 |
| | `test_ac09_ac10_ac11_localised_messages_for_every_key_the_script_uses` | AC-09, AC-10, AC-11 |
| | `test_ac09_length_limits_match_between_page_script_and_server` | AC-09 / NFR-05 |
| | `test_ac10_ac11_server_fallback_texts_match_content` | AC-10 / AC-11 |
| TestAccessibility | `test_ac12_skip_link_is_first_focusable_and_target_exists` | AC-12 |
| | `test_ac12_menu_button_has_state_and_controls_navigation` | AC-12 / AC-07 |
| | `test_ac13_exactly_one_h1_and_heading_order` | AC-13 / NFR-03 |
| | `test_ac13_landmarks` | AC-13 / NFR-03 |
| | `test_ac13_images_have_alt_and_icons_are_hidden` | AC-13 / NFR-03 |
| | `test_ac13_form_controls_have_labels_and_aria_references_resolve` | AC-13 / NFR-03 |
| | `test_nfr03_focus_style_and_reduced_motion` | AC-12 / NFR-03 |
| TestPrivacy | `test_ac14_no_insecure_or_third_party_resources` | AC-14 / NFR-04 |
| | `test_ac14_no_inline_handlers_scripts_or_styles` | AC-14 / NFR-05 |
| | `test_ac14_no_cookies_analytics_or_remote_calls_in_code` | AC-14 / NFR-04 |
| | `test_ac14_privacy_statement_on_each_contact_page` | AC-14 (FR-08) |
| | `test_ac14_no_private_identifiers_in_dist` | AC-14 / NFR-04 |
| | `test_ac14_no_private_identifiers_in_content_sources` | NFR-04 |
| TestNotFound | `test_ac15_404_page_links_to_each_language_home` | AC-15 |
| | `test_ac15_404_page_uses_root_relative_urls` | AC-15 |
| | `test_ac15_htaccess_declares_404_document` | AC-15 |
| TestSecurity | `test_nfr05_data_directory_is_closed` | NFR-05 |
| | `test_nfr05_root_htaccess_forces_https` | NFR-05 |
| | `test_nfr05_form_handler_validates_on_the_server` | NFR-05 |
| | `test_nfr05_no_secrets_in_repository` | NFR-05 |
| TestPerformance | `test_nfr06_page_weight_under_150_kb` | NFR-06 |

All 13 items in the prompt are covered. The page-weight budget is 150,000 bytes.

## Mutation checks

Because the other agent was reading the repository and I may not touch files outside `tests/`, I broke a scratch copy of the repository (without `.git` and `dist`) rather than the real one. Each mutation below made the named test fail, and the copy was deleted afterwards.

| Mutation | Test that failed |
|---|---|
| `build.py`: removed `rel="noopener noreferrer"` | `test_ac06_external_links_are_https_and_open_safely_in_new_tab` |
| `src/contact.php`: `NAME_MAX = 81` | `test_ac09_length_limits_match_between_page_script_and_server` |
| `root.htaccess`: removed `ErrorDocument 404` | `test_ac15_htaccess_declares_404_document` |
| Content files: added a fake student-ID string, a fake phone number, a fake e-mail (three separate runs) | `test_ac14_no_private_identifiers_in_dist` and `..._in_content_sources` |
| `style.css`: added `width: 600px` | `test_nfr01_no_fixed_width_above_320px` |
| `build.py`: `aria-current="page"` on every nav item | `test_nfr02_primary_nav_links_all_pages_and_marks_current` |
| `build.py`: `<html lang="en">` hard-coded | `test_ac03_lang_attribute_and_charset` |
| `data.htaccess`: `Require all granted` | `test_nfr05_data_directory_is_closed` |
| `build.py`: language switch always links to home | `test_ac02_language_switch_points_to_same_page_in_each_language` |
| `build.py`: page URLs point to non-existent files | `test_ac02_nfr02_internal_links_resolve`, plus the language-switch, primary-nav and privacy-statement tests |
| `build.py`: skip link moved after the brand link | `test_ac12_skip_link_is_first_focusable_and_target_exists` |
| `kk.json`: one validation message replaced by the English text | `test_ac09_ac10_ac11_localised_messages_for_every_key_the_script_uses` |
| `build.py`: `<body onload>` and an `http://` image | `test_ac14_no_inline_handlers_scripts_or_styles`, `test_ac14_no_insecure_or_third_party_resources`, plus `test_nfr06_page_weight_under_150_kb` |
| `README.md`: fake `sk-` key | `test_nfr05_no_secrets_in_repository` |

## Defects found

None; no test is left failing.

One inconsistency I noticed but did not turn into a test, because it is outside the stated ACs: `/Users/admin/personal-site/src/contact.php` line 131. The GitHub link on the no-JavaScript error page has `rel="noopener noreferrer"` but no `target="_blank"`, while the `AGENTS.md` convention for external links asks for both.

## What the suite does not cover

- **Browser behaviour:** actual rendering at 360 and 1280 px, contrast, visible focus, focus moving to the first invalid field, and live form submission are not tested. The responsive and focus checks are static readings of the CSS.
- **Content parity:** `build.py` already aborts on a key mismatch or empty string, so if that defect occurs every test errors in `setUpModule` rather than the parity test failing on its own.
- **Side effects:** each run rebuilds `dist/`, as the prompt requires. Running the tests also created `tests/__pycache__/`, which is gitignored.
