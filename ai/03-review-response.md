# Response to the agentic code review prompt

Tool: Claude Code (model Claude Fable 5.2), review agent, read-only. Date: 2026-11-27.
Prompt: `ai/03-review-prompt.md`. The agent's complete final report follows, unedited.
The author's verification of each finding and the accept / correct / reject decisions are in `ai/evaluation.md`.

---

Review of /Users/admin/personal-site at tag `v0-first-output` (read-only). I found no high-severity defect; there are 7 medium and 16 low findings, plus four hosting assumptions I could not verify.

How I checked: the code files are identical between the tag and the working tree. I built a `git archive` copy of the tag in the scratchpad so the live `dist/` was not touched. Nothing was run in a browser and PHP was not executed or linted; `contact.php` was read line by line.

## Findings (most severe first)

1. **Medium, accessibility: the form status may not be announced.** `src/assets/css/style.css:631-633` and `build.py:408`.
   - Wrong: `.form-status:empty { display: none }` removes the `role="status"` region from the accessibility tree until text is inserted.
   - Failure: a screen-reader user submits; NVDA or JAWS often does not announce "Sending…" or the success or error text, because the region appeared at the same moment as its content. Focus stays on the button, so the user hears nothing (AC-10, AC-11).
   - Fix: keep the region rendered when empty (drop the `:empty` rule, put the margin and padding on the `.is-*` classes only).

2. **Medium, security: stored messages have no global cap and the rate limit is per address only.** `src/contact.php:180-233` and `235-244`.
   - Wrong: one hit per 30 s per `REMOTE_ADDR`, with no limit on the size of `messages.jsonl` and no global rate.
   - Failure: one client can append up to about 8 KB every 30 s (about 23 MB a day); a rotating IPv6 or proxy pool is unlimited, so the file fills the hosting quota.
   - Related: the hit is recorded before `store_message()`, so a failed store still earns the visitor a 429 on retry.
   - Fix: refuse with 500/`storage_failed` when the file exceeds about 1 MB, add a global counter (for example 20 per hour) in `ratelimit.json`, and record the hit only after a successful store.

3. **Medium, maintainability: visible text and limits are duplicated in `contact.php`.** `src/contact.php:15-58`.
   - Wrong: 24 localised strings, `GITHUB_URL`, `LANGS` and the five limits are hard-coded, against the AGENTS.md rule that every visible string lives in `content/`. The limits now live in three places: `shared.json` `form`, the PHP constants, and the prose of the hints and of `invalid` / `rate` ("half a minute", "2 to 80").
   - Failure: someone changes `message_max` in `shared.json`; the HTML and JS accept 3000 characters, PHP rejects at 2000, and the hint still says 2000. The key-parity check sees none of it.
   - Fix: have `build.py` generate the PHP constants and texts from `content/*.json` and `shared.json` (a generated `contact.config.php` or placeholder substitution), and add `result.*` keys to the content files.

4. **Medium, content: Russian leaves the name undeclined, which marks gender.** `content/ru.json:17, 22, 27, 32, 37, 238`.
   - Wrong: "Личный сайт Мерей Бахытжан", "Образование Мерей Бахытжан", "связаться с Мерей Бахытжан". In Russian an undeclined name of this shape reads as a woman's; a man's would be "Мерея Бахытжана", "с Мереем Бахытжаном".
   - Failure: the text either states a gender the author did not choose (the bias risk in `docs/02` section 4) or is ungrammatical.
   - Fix: the author confirms, or rephrase to nominative ("Мерей Бахытжан: образование…", "Мерей Бахытжан — личный сайт").

5. **Medium, security and usability: the honeypot can be autofilled and gives a misleading error.** `build.py:379-382`, `src/contact.php:264-268`.
   - Wrong: the hidden field is `name="website"` / `id="website"`, a name autofill tools and password managers recognise despite `autocomplete="off"`. A filled value returns 400 `invalid_request`.
   - Failure: a real visitor whose extension filled the field sees "check the lengths" without JS, or "not saved, use GitHub" with JS, with no field to fix, every time.
   - Fix: use a neutral name (for example `hp_field`), and consider answering a tripped honeypot with a fake 200 so bots learn nothing.

6. **Medium, privacy: the statement about the address hash is stronger than the code.** `content/en.json:226` (same item in `ru.json` and `kk.json`), `src/contact.php:206-223`.
   - Wrong: entries are pruned only when the next valid submission arrives, so on a quiet site the last sender's hash stays indefinitely, not "for a short time". The salt sits in the same file, so an IPv4 address is recoverable by brute force in minutes by anyone who can read the file.
   - Failure: the privacy statement (FR-08, AC-14) promises something the code does not do.
   - Fix: reword honestly ("until the next message arrives; readable only by the site owner"), or store a truncated hash, or rotate the salt whenever `hits` is empty.

7. **Medium, accessibility: language switch fails WCAG 2.5.3 Label in Name.** `build.py:181-182`.
   - Wrong: the visible text "KK / RU / EN" is `aria-hidden`, and the accessible name is "Қазақша / Русский / English".
   - Failure: a voice-control user says "click RU" and nothing matches.
   - Fix: drop `aria-hidden` and make the name contain the visible label, for example `RU<span class="visually-hidden"> · Русский</span>`.

8. **Low, requirements: without JavaScript a rejected post loses the visitor's text.** `src/contact.php:150`.
   - Wrong: the result page's only way back is a fresh link to `/<lang>/contact.html`.
   - Failure: a whitespace-only name passes native `required`, the server answers 400 with a generic message, the visitor follows "Back to the contact page" and the message is gone (AC-11 "nothing is lost silently"; AC-09 is only met with JS).
   - Fix: tell the visitor to use the browser Back button, or re-render the form with escaped values.

9. **Low, security: cross-site posts are accepted.** `src/contact.php:253-257`.
   - Wrong: no `Origin` or `Sec-Fetch-Site` check.
   - Failure: any third-party page can auto-submit a form to `/contact.php` from visitors' browsers, storing spam under their addresses and bypassing the per-address limit.
   - Fix: reject when `Origin` is present and its host differs from `HTTP_HOST`.

10. **Low, security: PHP error display is not switched off.** `src/contact.php`, top of file.
    - Failure: if the host has `display_errors` on, an unsuppressed warning (for example from `flock` or `fwrite`) prints the absolute `htdocs` path, breaks the JSON body and the later `header()` calls.
    - Fix: `ini_set('display_errors', '0');` after `declare`.

11. **Low, security: invisible characters pass validation.** `src/contact.php:77-93`.
    - Wrong: only `\p{Cc}` is stripped; format characters (`\p{Cf}`: zero-width space, bidi overrides) are kept and counted.
    - Failure: a name of two zero-width spaces passes `NAME_MIN`; a right-to-left override garbles the line in the file manager.
    - Fix: also remove `\p{Cf}` before measuring length.

12. **Low, security: no HSTS, and the HTTPS redirect trusts a client header.** `src/htaccess/root.htaccess:17-19, 33-39`.
    - Failure: a plain-HTTP request carrying `X-Forwarded-Proto: https` is not redirected; without `Strict-Transport-Security` a first visit can be downgraded.
    - Fix: add `Header always set Strict-Transport-Security "max-age=31536000"` once HTTPS is confirmed on the host. See also the unverified loop risk below.

13. **Low, security: the external link on the PHP result page breaks the project convention.** `src/contact.php:130-132`.
    - Wrong: the GitHub link has `rel` but no `target="_blank"` and no "opens in a new tab" note, unlike `external_link()` in `build.py`.
    - Fix: generate it the same way (ties into finding 3).

14. **Low, requirements: gateway, 404 and PHP result pages have only a `main` landmark.** `build.py:428-495`, `src/contact.php:135-153`.
    - Wrong: no `header`, `nav`, footer or skip link, while FR-10 says "every page" and AC-13 says "any page".
    - Also AC-01: with JS off the root shows only the name and the language links, not role and introduction.
    - Fix: narrow FR-10 and AC-13 to the 15 content pages, or add a minimal header and footer.

15. **Low, requirements: NFR-02 "one click" is not literally met below 760 px with JS.** `src/assets/css/style.css:285-287`.
    - Wrong: the navigation is collapsed, so reaching another page takes two taps.
    - Fix: reword NFR-02, or keep the nav open on mobile.

16. **Low, requirements: `hreflang` alternates are relative URLs.** `content/shared.json:3`, `build.py:115-117`.
    - Wrong: `site_url` is empty, and search engines ignore non-absolute `hreflang` values.
    - Fix: set `site_url` once the subdomain is known, and have the build warn when it is empty.

17. **Low, maintainability: `shared.json` is not validated and the build is not atomic.** `build.py:74-101, 261-262, 232, 515-517, 523`.
    - Failure: a subject, project, page id or status in `shared.json` with no matching content key gives a raw `KeyError` traceback after `dist/` was already deleted, leaving a half-built site. Content subjects missing from `shared.json` are silently not rendered.
    - Adding a page needs five coordinated edits: `pages`, `RENDERERS`, `pages.<id>` in three files, `home.cards.<id>` in three files.
    - Fix: validate ids up front and raise `BuildError`; build into a temporary directory and swap.

18. **Low, maintainability: validation limits are rendered twice per field.** `build.py:385-386, 393-394, 401-402`.
    - Wrong: both `minlength` / `maxlength` and `data-min` / `data-max` carry the limits.
    - Fix: read `field.minLength` / `field.maxLength` in `main.js:106-107`.

19. **Low, maintainability: the required-field asterisk is hard-coded.** `build.py:356`, `content/*.json` `required_note`.
    - Wrong: `*` is in `build.py` while the note that explains it is in the content files, so the two must be changed together.

20. **Low, maintainability: the site only works at a domain root.** `build.py:19-22, 110-111`, `content/shared.json:34`.
    - Wrong: every URL is root-relative. This is fine for `htdocs/` but breaks under a sub-path or `file://`.
    - Fix: document it.

21. **Low, maintainability: small drift and dead code.**
    - `docs/03-design.md:67` says "about 400 lines" of CSS; the file has 859.
    - Classes `project-link`, `hero-text`, `subject-body`, `status-in-progress`, `icon-menu` and `privacy` (on the `section`) have no rules of their own.
    - `style.css:516-519` repeats the colour already set at line 498.
    - `render_education` and `render_activities` take an unused `lang`.

22. **Low, content: slight overstatement and wording.**
    - `content/en.json:42` "I build backend services in Python" (and the ru/kk equivalents) is stronger than the supplied facts, which list backend as an interest plus one bot, one booking rule and one web app. Suggest "I am learning backend development in Python and build Telegram bots…".
    - `content/ru.json:42, 171` "инструменты с помощью ИИ" is ungrammatical in the interests sentence and ambiguous. Use "инструменты на основе ИИ" or "с использованием ИИ".
    - `content/kk.json:213-214` and `src/contact.php:52` use "Ат" for "name", which also reads as "horse". "Есім" / "Есіміңіз" is safer.
    - `content/kk.json:152` "деңгей бағасынсыз" is awkward; "деңгейі көрсетілмеген" reads better. My Kazakh judgement here needs the author's confirmation.

23. **Low, accessibility: disabling the focused submit button.** `src/assets/js/main.js:178`.
    - Wrong: `submit.disabled = true` while the button has focus can drop keyboard focus in some browsers during sending.
    - Fix: use `aria-disabled="true"` with the existing early-return guard.

## Unverified (cannot be checked without the host or PHP)

- **InfinityFree anti-bot challenge.** As I recall, the free plan serves a JavaScript challenge that sets a `__test` cookie before any page loads. If so, the site is unreachable with JS off (AGENTS.md criterion 4, FR-11's noscript fallback, the no-JS form post), and "no cookies" in NFR-04 and AC-14 holds only for the site's own code. The privacy text already says "the code of this site". Record this as a host limitation (R-04) after testing; it would be high severity if confirmed.
- **`REMOTE_ADDR`.** If the host puts a proxy address there, every visitor shares one rate-limit bucket and one spammer posting every 30 s locks the form for everyone (`contact.php:209`).
- **HTTPS redirect loop.** `root.htaccess:17-19` loops if the host terminates TLS upstream and sets neither `HTTPS=on` nor `X-Forwarded-Proto`. Test with `curl -I` after upload.
- **`.htaccess` directives.** `Options -Indexes`, `ErrorDocument` and `Header always set` being allowed on the plan is unverified; a disallowed directive gives a site-wide 500. A file manager that skips dotfiles would also drop the root `.htaccess` (losing the redirect, CSP and the `.json` deny). `data/.htaccess` is recreated by PHP, which is good.
- **PHP runtime.** I found no syntax error and no `strict_types` type error by reading. It needs PHP 7.1 or newer.
- **Responsive layout.** No horizontal scroll at 320 / 360 px and the menu behaviour were read from the CSS only.

## Checked and found fine

- **Requirements:** FR-01 to FR-09 and FR-12 content is present in all three languages. 15 pages each have exactly one `h1` and no skipped heading levels. `lang`, title and description are per language. The language switch links to the same page. `aria-current="page"` is set. The skip link targets `main` with `tabindex="-1"`. The largest page is under 40 KB with CSS, JS and images (NFR-06). The built pages contain no inline script, inline style or event-handler attribute, and every `src`/`href` generated by `build.py` is root-relative or one of the https links in `shared.json`.
- **PHP:**
  - No user input reaches headers or file paths.
  - All HTML output goes through `h()`.
  - `json_encode` neutralises newlines in the log.
  - UTF-8 is validated.
  - CRLF is normalised so lengths match the JS code-point count.
  - `ratelimit.json` is read and rewritten under one `LOCK_EX`.
  - Appends use `LOCK_EX`.
  - An unwritable `data/` gives 500 `storage_failed` and a localised message with the GitHub link (AC-11).
  - `X-Forwarded-For` is not trusted.
  - There are no cookies or sessions.
- **`.htaccess`:** the CSP `default-src 'self'` matches what the pages load. `data/` is closed three ways (its own file, the root `FilesMatch` on `.json` / `.jsonl`, and the PHP-written guard), and it fails closed.
- **JS:** no `innerHTML`; DOM is built with `textContent` and `createElement`. No globals. `localStorage` access is wrapped in try/catch. The gateway order is saved choice, then `navigator.languages`, then default. A non-JSON or challenge response falls to the error state with the form contents kept. A script failure leaves the nav open and the form posting natively.
- **Accessibility:** two labelled `nav` landmarks; the menu button has `aria-expanded` and `aria-controls`, closes on Escape and returns focus. `aria-describedby` points at the hint and the error, `aria-invalid` is toggled, and focus goes to the first invalid field. Decorative SVG is `aria-hidden`. External links have `rel="noopener noreferrer"` and a hidden "opens in a new tab" note.
- **Contrast:** all text pairs are at least 6.1:1 in light and 7.6:1 in dark; control borders are at least 3.98:1.
- **CSS:** animations and smooth scrolling sit only inside `prefers-reduced-motion: no-preference`, and there is no `!important`.
- **Content:** key parity holds and `build.py` enforces it. There is no phone number, e-mail address, student ID, grade or date of birth. Strings identical across languages are only proper names and tool names. There is no gendered first-person past tense in Russian ("какая школа была", "принял" refer to nouns). No awards, skill levels or dates beyond `ai/01-initial-prompt.md`; all six subjects are marked in progress.
