# T1. Requirements baseline and Agile plan

Project: trilingual personal website of Merey Bakhytzhan (KBTU, Software Engineering).
Baseline date: 2026-11-27. Written before any code was generated.

## 1. Context

| Item | Definition |
|---|---|
| Target audience | (1) The course teacher assessing TSIS #01. (2) Recruiters and internship coordinators in Kazakhstan who read Kazakh, Russian or English. (3) Classmates and project collaborators. |
| User goals | Find out in under a minute who the author is, what they study, what they have built, and how to reach them, in the visitor's preferred language and on any device. |
| Project scope | A static, public, three-language (Kazakh, Russian, English) personal site with five content pages per language, a contact form, a privacy statement and a 404 page, hosted on InfinityFree over HTTPS. |
| Constraints | Free InfinityFree hosting and subdomain only (PHP available, no Python/Node on the server, no outgoing e-mail on the free plan). No paid tools, hosts, domains or subscriptions. Truthful content only. No private identifiers, home address, phone number, grades or documents. Individual work. Deadline 2026-12-06 23:59. |
| Exclusions | No authentication or restricted area (see design decision DD-3). No blog, CMS, comments, analytics, advertising, cookies or third-party scripts. No real photograph of the author. No fourth language. |

## 2. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | Kazakh or Russian text is mistranslated or left in English | Medium | High | Key-parity test across the three content files; author reviews every string before launch |
| R-02 | Oversharing personal data | Medium | High | Content inventory with public / private / omitted classification (T2) |
| R-03 | AI-generated text contains fabricated claims | Medium | High | Every claim checked against facts supplied by the author; unverifiable items removed |
| R-04 | InfinityFree limitations break the site (anti-bot cookie check, no mail, downtime) | Medium | Medium | Static pages; form degrades gracefully; limitations recorded in `04_Demo.txt` |
| R-05 | Contact form abused for spam or injection | Medium | Medium | Server-side validation, honeypot, length limits, rate limit, storage outside public access |
| R-06 | Layout breaks on small screens | Low | High | Mobile-first CSS, tests at 360, 768 and 1280 px |
| R-07 | Secrets committed to the public repository | Low | High | No secrets needed by design; secret scan before every push |
| R-08 | Loss of source files | Low | High | Git history on GitHub plus tagged release archive |

## 3. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | The home page shows the author's name, role, a short introduction and a clearly visible language selector. | Must |
| FR-02 | The education page presents KBTU, the major and year of study, and the previous high school. | Must |
| FR-03 | The education page presents a learning portfolio: selected subjects with accurate descriptions and their status (completed / in progress). | Must |
| FR-04 | The activities page presents interests, achievements and extracurricular activities. | Must |
| FR-05 | The projects page presents projects as evidence of skills, with external links only where they are safe to publish. | Must |
| FR-06 | The activities page presents future study and career plans. | Must |
| FR-07 | The contact page provides professional links and a contact form with client-side and server-side validation. | Must |
| FR-08 | The contact page contains a short privacy statement. | Must |
| FR-09 | Every page offers a Kazakh / Russian / English switch that opens the same page in the chosen language and remembers the choice. | Must |
| FR-10 | Every content page (the 15 language pages) has the same primary navigation, with the current page marked, and a skip-to-content link. | Must |
| FR-11 | The root URL sends the visitor to a language version (saved choice, then browser language, then English) and offers manual links when JavaScript is off. | Should |
| FR-12 | Unknown URLs show a 404 page with links back to each language's home page. | Should |

## 4. Non-functional requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Responsiveness | All pages are usable from 320 px to 1920 px wide with no horizontal scrolling. |
| NFR-02 | Usability | Any content page is reachable from any other in one click on wide screens and in two taps (menu, link) below 760 px; language can be switched in one click at every width. |
| NFR-03 | Accessibility | Pages meet WCAG 2.1 AA for the checks we run: landmarks, one `h1`, labelled controls, alternative text, visible focus, keyboard operation, contrast of at least 4.5:1, reduced-motion support. |
| NFR-04 | Privacy | No cookies, analytics or third-party requests. No private identifiers, phone number, address, grades or documents are published. |
| NFR-05 | Security | Served over HTTPS. All form input validated on the server. No secrets in the repository. Stored messages are not web-accessible. |
| NFR-06 | Performance | Each page transfers under 150 KB uncompressed (HTML + CSS + JS + images) and uses no framework or web font download. |
| NFR-07 | Maintainability | Content lives in per-language JSON files separate from templates and styles; one build command produces the site; automated checks run with one command. |
| NFR-08 | Internationalisation | UTF-8 everywhere; correct `lang` attribute, title and description per language; the three content files have identical keys. |

## 5. User stories and acceptance criteria

**US-01** As a visitor, I want to land on an introduction in my language so that I immediately know whose site this is.
- **AC-01** Given I open the root URL, when the page loads, then I am shown a home page with the author's name, role and introduction, and a visible language selector.

**US-02** As a multilingual visitor, I want to switch language anywhere so that I never lose my place.
- **AC-02** Given I am on any page in one language, when I choose another language, then the same page opens in that language.
- **AC-03** Given a page in language X, when it is rendered, then its `lang` attribute, title and meta description are in language X and Kazakh/Cyrillic letters display correctly.

**US-03** As a teacher or recruiter, I want to see the author's education and coursework so that I can judge their background.
- **AC-04** Given I open the education page, then I see KBTU, the major, the year of study and the previous school.
- **AC-05** Given I open the education page, then I see the subject list with a description and status for each subject.

**US-04** As a recruiter, I want to see real projects so that I can verify skills.
- **AC-06** Given I open the projects page, when I follow a project link, then it opens a working HTTPS page in a new tab and the site itself stays open.

**US-05** As a mobile visitor, I want the site to fit my phone so that I can read it comfortably.
- **AC-07** Given a 360 px wide screen, when I open any page, then there is no horizontal scroll and navigation works through a menu button.
- **AC-08** Given a 1280 px wide screen, when I open any page, then navigation is shown inline and content uses the wider layout.

**US-06** As a visitor, I want to send a message without exposing or needing the author's personal contacts.
- **AC-09** Given the contact form is empty or invalid, when I submit, then I see validation messages in the page language and focus moves to the first invalid field.
- **AC-10** Given valid input, when I submit, then I see a confirmation in the page language.
- **AC-11** Given the server cannot store the message, when I submit, then I see an error in the page language that points to the alternative contact link, and nothing is lost silently.

**US-07** As a keyboard or screen-reader user, I want accessible navigation so that I can use the whole site.
- **AC-12** Given I use only the keyboard, then I can reach a skip link first, every interactive element has a visible focus, and the menu can be opened and closed.
- **AC-13** Given any content page, then it has landmarks, exactly one `h1`, labelled form controls and alternative text for meaningful images.

**US-08** As a privacy-conscious visitor, I want to know what happens to my data.
- **AC-14** Given the contact page in any language, then a privacy statement explains what is collected and why, and the site sets no cookies and makes no third-party requests.

**US-09** As a visitor who mistypes an address, I want to get back on track.
- **AC-15** Given an unknown URL, then a 404 page offers links to the home page in each language.

## 6. Prioritised backlog

| # | Item | Stories | Priority | Iteration |
|---|---|---|---|---|
| B-01 | Content inventory and privacy classification | US-08 | Must | 1 |
| B-02 | Sitemap, wireframes, UML, architecture | all | Must | 1 |
| B-03 | Build pipeline: JSON content to static pages | US-01, US-02 | Must | 1 |
| B-04 | Five pages in three languages with navigation and language switch | US-01 to US-05 | Must | 1 |
| B-05 | Responsive layout and menu | US-05 | Must | 1 |
| B-06 | Contact form with validation and storage | US-06 | Must | 2 |
| B-07 | Accessibility pass | US-07 | Must | 2 |
| B-08 | Automated checks and traceability table | all | Must | 2 |
| B-09 | Agentic code review and corrections | all | Must | 2 |
| B-10 | Deployment to InfinityFree, hosted tests, release tag | all | Must | 2 |
| B-11 | 404 page and root language detection | US-09, US-01 | Should | 2 |
| B-12 | Animations with reduced-motion fallback | US-01 | Could | 2 |

## 7. Iterations

| Iteration | Dates | Goal | Outcome |
|---|---|---|---|
| 1 | 2026-11-24 to 2026-11-27 | Requirements, content decisions, design, first generated version | See report section "Iteration log" |
| 2 | 2026-11-27 to 2026-12-06 | Quality: form, accessibility, tests, review, deployment, evidence | See report section "Iteration log" |

## 8. Teacher supervision checkpoints

No checkpoint had taken place when this baseline was written. Each row is filled in after the real meeting.

| Checkpoint | Topic | Date | Feedback received | What changed afterwards |
|---|---|---|---|---|
| #01 | Requirements approval | pending | | |
| #02 | Design approval | pending | | |
| #03 | Prototype review | pending | | |
| #04 | Quality review | pending | | |
| #05 | Launch review | pending | | |

## 9. Change log of this baseline

| Date | Change | Reason |
|---|---|---|
| 2026-11-27 | FR-10 and AC-13 narrowed from "every page" to "every content page" | Code review finding 14: the language gateway, 404 page and form result page are deliberately minimal single-purpose pages |
| 2026-11-27 | NFR-02 reworded to allow two taps on small screens | Code review finding 15: the collapsed mobile menu makes "one click" untrue below 760 px |
