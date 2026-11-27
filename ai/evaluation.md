# AI-use record and evaluation

**Vibe-coding platform:** Claude Code (Anthropic), model Claude Fable 5.2, run in the terminal on the author's computer. No paid subscription was bought for this assignment and no other AI tool was used.

**How the session worked.** The author gave the assignment file and answered the assistant's questions (exchange 0). From those answers the requirements and design documents were written, and each later step was issued as a written prompt to a Claude Code agent with explicit context: the requirement IDs, a repository map (`AGENTS.md`), constraints and the relevant files. Prompts 1 to 5 were drafted by the assistant inside the session from the author's brief and answers, saved to `ai/` before being run, and their responses were saved unedited. The author's own typed prompts are exchange 0 and the redesign request in exchange 6.

## 1. AI-use record

| # | Phase | Date | Prompt summary | Output used | Problems found | Changes made | Verification source |
|---|---|---|---|---|---|---|---|
| 0 | Planning | 2026-11-24 | Read the assignment, ask questions first, then complete every requirement | 19 clarifying questions; decisions table; requirements, privacy review and design documents | The assistant assumed a Telegram bot it had no details about; it proposed listing in-progress subjects as "completed" | Bot verified in Telegram before being listed; subjects labelled "in progress" | Author's answers; the running bot `@merey_jobfinder_bot`; assignment slides |
| 1 | Implementation | 2026-11-27 | Generate the first version from `AGENTS.md`, the requirements, the design and a fixed list of facts | Whole first version, kept as tag `v0-first-output` | PHP never executed; server texts hard-coded in PHP; submit button touching the privacy box; some wording stronger than the facts | Fixed in exchanges 4 and 5 | Local build; headless Chrome screenshots at 320 to 1280 px |
| 2 | Testing | 2026-11-27 | Write a standard-library test suite mapped to AC-01 to AC-15 and the NFRs; mutation-check it | `tests/test_site.py`, 45 tests | No browser behaviour covered; an SVG path later matched the phone-number pattern (false positive) | Browser checks run separately; path rewritten | `python3 -m unittest`, 14 mutation checks listed in the response |
| 3 | Review | 2026-11-27 | Review v0 against requirements, security, accessibility and maintainability; read-only | 23 findings and 6 unverified hosting assumptions | One finding was wrong (duplicate colour); two proposed fixes were unsuitable | See section 2 | Each finding checked in the code by line before acting |
| 4 | Debugging | 2026-11-27 | Fix 12 verified defects, each with a failing regression test first | 12 fixes, 12 new tests (57 total) | Two new tests had wrong patterns at first; PHP still unexecuted | Patterns corrected by the agent; PHP paths to be exercised on the host | Red-then-green test runs; re-reading of every changed PHP line |
| 5 | Refactoring | 2026-11-27 | Remove duplication: generate the PHP config from content, placeholders for limits, build validation, dead code | Generated `contact.config.php`, `{min}`/`{max}` placeholders, atomic build, 60 tests | The agent correctly refused one requested removal (the "duplicate" colour) | Kept the rule with a comment | Byte-level diff of `dist/` before and after; test suite |
| 6 | Design iteration | 2026-11-27 | Author, after seeing v0 in the browser: "make the site more beautiful" (twice) | New palette, ornament, hero panel, icons, education timeline | First pass judged not enough by the author; ornament path tripped the phone-number test | Second, stronger pass; path syntax changed | Screenshots in light and dark at desktop and phone width; 60 tests |

Files: `ai/00-planning-*`, `ai/01-initial-*`, `ai/02-testing-*`, `ai/03-review-*`, `ai/04-debugging-*`, `ai/05-refactoring-*`.

## 2. Evaluation of the agentic code review

Every finding was opened in the code at the cited line before a decision was made. The commands used were `grep` on the cited patterns and a read of the surrounding function.

### Accepted (implemented as proposed)

| Finding | Why accepted | Evidence |
|---|---|---|
| 1. Status region hidden while empty | `style.css` really had `.form-status:empty { display: none }`; a live region inserted together with its text is often not announced | Fix D-01; test `test_ac10_ac11_status_region_stays_rendered_while_empty` |
| 7. Language switch name does not contain the visible label | `build.py` wrapped `KK` in `aria-hidden`; fails WCAG 2.5.3 | Fix D-02; link text is now `KK` plus a hidden language name |
| 9. Cross-site posts accepted | No `Origin` check existed in `contact.php` | Fix D-05; test `test_nfr05_cross_site_posts_are_rejected` |
| 10, 11. Error display and invisible characters | Neither `display_errors` nor `\p{Cf}` appeared in the file | Fixes D-06 and D-07 |
| 3, 13, 17, 18, 19. Duplicated texts and limits, unvalidated build | 24 strings and 5 limits were typed into PHP against the project's own rule | Refactoring commit; `dist/` diff showed no visible change |
| 4, 22. Gendered Russian name forms, overstated introduction | The undeclined name in oblique cases states a gender the author did not choose; "I build backend services" went beyond the facts | Fixes D-11 and D-12 |

### Corrected (problem real, proposed fix changed)

| Finding | What was proposed | What was done instead, and why |
|---|---|---|
| 2. Unbounded message file | A 1 MB cap **and** a global counter of about 20 messages per hour | The cap and the hit-after-store ordering were implemented. The global counter was left out: on a site with one shared limit, a single spammer would lock the form for every real visitor, which is worse than the problem it solves. The cap already bounds the damage. |
| 5. Honeypot named `website` | Rename it and answer a tripped honeypot with a fake success | Renamed to `hp_field`. The fake success was not adopted: a real visitor whose password manager filled the field would be told the message was saved when it was not, breaking AC-11. The request still gets an error. |
| 6. Privacy statement stronger than the code | Reword the statement, or truncate the hash, or rotate the salt | Both sides were changed: the code now prunes on every request and renews the salt when the list is empty, and the statement says plainly that the hash can stay longer when nobody visits. |

### Rejected

| Finding | Reason | Evidence |
|---|---|---|
| 12. Add `Strict-Transport-Security` for one year | The site sits on a free subdomain whose certificate is issued and renewed by the host, outside the author's control. If the certificate lapses, HSTS removes the browser's "proceed anyway" path and locks visitors out for a year. The HTTPS redirect and same-origin-only pages already cover the realistic risk for a site with no login. To be revisited if the host proves stable. | `src/htaccess/root.htaccess` keeps the redirect; hosting limitations in `docs/05-launch.md` |
| 21 (part). "Duplicate" colour on `.card .badge` | The finding is wrong. `.card p` has specificity (0,1,1) and beats `.badge` (0,1,0), so without the repeated colour the badge text turns grey. The refactoring agent reached the same conclusion independently. | Comment in `style.css` above the rule |
| 14. Add header and footer to the gateway and 404 pages | These are deliberately minimal single-purpose pages. The requirement was over-stated, so FR-10 and AC-13 were narrowed to the 15 content pages instead of adding chrome. | Change log in `docs/01-requirements.md` section 9 |

### Deferred

- **8. A rejected post without JavaScript loses the text.** Left as a known limitation: the host's own anti-bot check requires JavaScript, so this path cannot occur for real visitors (to be confirmed on the host).
- **16. Relative `hreflang`.** Resolved at deployment by setting `site_url`.

## 3. Overall judgement

- **Where the AI was reliable:** generating consistent structure across 15 pages, writing mutation-checked tests, and finding real accessibility and security defects in its own first draft when asked to review with explicit axes.
- **Where it was not:** it could not run PHP, so every server path was verified by reading only; it over-claimed in the biography until told the exact facts; one review finding was simply wrong; its Kazakh needs a native check.
- **What context engineering changed:** the first version followed the repository map and conventions because they were in `AGENTS.md`, and the review cited requirement IDs because the prompt supplied them. The one vague prompt of the project, "make it more beautiful", needed two rounds.
