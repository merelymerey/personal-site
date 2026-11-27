# T2. Content, privacy and ethical review

## 1. Content inventory (identical structure in Kazakh, Russian and English)

| Page | Block | Content | Source of the facts | KK | RU | EN |
|---|---|---|---|---|---|---|
| Home | Hero | Name, role, short introduction | Author | yes | yes | yes |
| Home | Sample bot card | An example vacancy card in the format Merey Job Finder shows (illustrative vacancy, labelled as an example) | Format checked in the running bot on 2026-11-27; the vacancy itself is invented and captioned as an example | yes | yes | yes |
| Home | Figures | Number of site languages, linked projects and current subjects | Counted by the build from `content/shared.json` | yes | yes | yes |
| Home | Section bands | Projects, education and activities, reusing the detail-page content | Same sources as the detail pages | yes | yes | yes |
| Home | Questions and answers | Four questions answered from facts already on the site | Author's facts; privacy statement | yes | yes | yes |
| Education | University | KBTU, Software Engineering, 3rd year | Author | yes | yes | yes |
| Education | School | Bereke School, Almaty, graduated 2024 | Author | yes | yes | yes |
| Education | Learning portfolio | Selected subjects with description and status | Author's course list and coursework | yes | yes | yes |
| Projects | Merey Job Finder | Telegram bot: description, features, link to the bot | Checked in the running bot on 2026-11-27 | yes | yes | yes |
| Projects | Smart Campus checker | Description, link to public repository | Author's public GitHub repository | yes | yes | yes |
| Projects | «Шаг» | Description, link to public repository | Author's public GitHub repository | yes | yes | yes |
| Activities | Interests | Areas the author currently explores | Author | yes | yes | yes |
| Activities | Achievements | School olympiad participation | Author | yes | yes | yes |
| Activities | Extracurricular | Volunteering at KBTU in the first year | Author | yes | yes | yes |
| Activities | Future plans | Plan to apply to a university programme in a different major | Author | yes | yes | yes |
| Contact | Links | GitHub profile, Telegram bot | Author | yes | yes | yes |
| Contact | Form | Labels, hints, validation and status messages | Written for this site | yes | yes | yes |
| Contact | Privacy statement | What is collected and why | Written for this site | yes | yes | yes |
| All | Navigation, footer, metadata | Labels, titles, descriptions, skip link | Written for this site | yes | yes | yes |
| 404 | Error text | Message and links home | Written for this site | yes | yes | yes |

## 2. Media and external items

| Item | Type | Source | Owner | Licence / permission |
|---|---|---|---|---|
| `avatar.svg` | Illustration (monogram avatar) | Drawn in code for this site with Claude Code | Author | Original work, MIT with the repository |
| Card icons (11) | Inline SVG | Drawn in code for this site | Author | Original work |
| `favicon.svg` | Icon | Drawn in code for this site | Author | Original work |
| Navigation and link icons | Inline SVG | Drawn in code for this site | Author | Original work |
| Fonts | System font stack | Visitor's device | n/a | Nothing is downloaded or redistributed |
| Link to GitHub | External link | github.com | GitHub | Plain hyperlink, no logo used |
| Link to Telegram bot | External link | t.me | Telegram | Plain hyperlink, no logo used |
| Photographs | none | | | No photographs are published |
| Certificates | none | | | No certificates or documents are published |

No photograph, icon set, font file, template or library from a third party is included.

**Design guidance reused.** The landing page follows the structure of a landing-page design guide the author had downloaded earlier as an agent skill (`landing-page-guide-v2`: header, large hero title, primary call to action, figures, media, benefits, questions, final call to action, footer). Only the checklist of ideas was used. Its Next.js and ShadCN code was not, because the host runs static files and PHP only. Its "customer testimonials" and urgency elements were left out because the site has no customers and inventing them would be a false claim.

## 3. Personal data classification

| Detail | Class | Reason |
|---|---|---|
| Name (Merey Bakhytzhan) | Public | Needed to identify the author; already public on GitHub |
| University, major, year of study | Public | Required by the brief |
| High school name, city, graduation year | Public | Required by the brief; no class or address |
| Subjects studied (names only) | Public | Required by the brief |
| Grades, GPA, transcripts | Omitted | Forbidden by the brief |
| Student ID | Omitted | Private identifier; also kept out of the subdomain |
| Phone number, home address, date of birth | Omitted | Forbidden by the brief |
| Personal e-mail address | Omitted | Not needed: the form and GitHub cover contact |
| Personal Telegram account | Omitted | Only the public bot is linked |
| Real photograph | Omitted | Author's choice; an illustration is used |
| Job-search preferences stored in the bot (salary, experience) | Private | Seen during verification, not published |
| GitHub username | Public | Professional link chosen by the author |
| Olympiad participation, volunteering | Public | Stated in general terms, without documents |
| Messages sent through the form | Private | Stored outside public access, see privacy statement |

**Other people.** The site contains no information about and no photographs of any other person, so no third-party permission was needed. The person who helped with manual testing is referred to only as "Tester 1" in the report, with their consent.

## 4. Privacy and ethical risk assessment

| Risk | Assessment | Control |
|---|---|---|
| Oversharing | A personal site invites adding birthday, phone, address or student ID, which enable doxxing and account recovery attacks. | Classification table above; automated test that searches the built site for phone-number and student-ID patterns and e-mail addresses. |
| Copyright | Generated sites often pull in stock photos, icon fonts or copied templates with unclear licences. The design references given in the brief must not be cloned. | All visuals drawn for this site; no third-party assets; the layout is original and only general ideas (concise identity, simple navigation) were taken from the references. |
| False claims | An assistant tends to inflate a CV: invented awards, "expert" skill levels, finished projects that are not finished. | Every claim traced to a fact supplied by the author or checked in a public repository or the running bot. Achievements are stated modestly. In-progress subjects are labelled as such. |
| Bias in generated text | Generated biography text can assume gender, age or background, and translation can add gendered or honorific forms not chosen by the author. | Texts use neutral first-person phrasing; Russian and Kazakh versions avoid gendered past-tense forms where possible; the author reviews all three versions. |
| Account security | The hosting, GitHub and Telegram accounts could be hijacked and the site defaced; credentials could leak through the repository or the submission. | No credentials in the repository or the submission package; deployment through the hosting file manager in the author's own browser session; a bot token found hard-coded in an unrelated old local folder was flagged to the author and kept out of this project. |
| Visitor data | The form collects a name, an optional reply contact and a message. | Minimal fields, stated purpose, no cookies or trackers, storage in a directory closed to web access, deletion after reply. |

## 5. Contact method

Visitors can contact the author in two ways, neither of which exposes a phone number, address or personal e-mail:

1. The contact form on the site (name, optional reply contact, message).
2. The public GitHub profile `github.com/merelymerey`.
