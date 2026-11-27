# T3. Software design and UML

## 1. Sitemap

```
/                       language gateway (redirects to /kk/, /ru/ or /en/)
├── /kk/  /ru/  /en/    one directory per language, identical structure
│   ├── index.html        Home (landing): hero, then a band per      FR-01
│   │                     section, then a call to action
│   ├── education.html    University, school, learning portfolio     FR-02, FR-03
│   ├── projects.html     Projects with safe links                   FR-05
│   ├── activities.html   Interests, achievements, extracurricular,  FR-04, FR-06
│   │                     future plans
│   └── contact.html      Links, contact form, privacy statement     FR-07, FR-08
├── /contact.php        form handler (POST only)                     FR-07
├── /404.html           trilingual error page                        FR-12
└── /assets/            css, js, img
```

Every content page links to the same page in the other two languages (FR-09) and to the other four pages in its own language (FR-10).

## 2. Wireframes

Low-fidelity wireframes are stored as editable SVG:

- `docs/wireframes/desktop.svg`: 1280 px layout, header with inline navigation and language switch.
- `docs/wireframes/mobile.svg`: 360 px layout, collapsed menu button, single column.

## 3. UML models

Editable PlantUML sources and rendered images are in `docs/diagrams/`:

- `usecase.puml`: use-case diagram (visitor and site owner).
- `sequence-contact.puml`: sequence diagram for sending a contact message.
- `component.puml`: component diagram of the build pipeline and the deployed site.

## 4. Architecture

The site is a **statically generated multi-page site**.

- **Content layer**: `content/kk.json`, `content/ru.json`, `content/en.json` hold every visible string with identical keys, including the texts of the server's result page (`result`). `content/shared.json` holds language-independent data (URLs, language list, page list, the form's length limits and required-field marker). Texts name a limit with a placeholder such as `{max}`, never with the number.
- **Presentation layer**: `build.py` (Python standard library only) contains the page templates and renders `dist/<lang>/<page>.html`. It first checks that every subject, project, page and status in `shared.json` has its texts in all three languages (and the reverse for subjects and projects), fills the placeholders, builds into a temporary directory and replaces `dist/` only when the whole build succeeded. `src/assets/css/style.css` holds all styling; `src/assets/js/main.js` holds behaviour and reads the limits from the `minlength` / `maxlength` attributes.
- **Server layer**: `src/contact.php` is the only dynamic file. It validates a POST, appends the message to a file in a directory closed by `.htaccess`, and answers with JSON (script request) or a small localised HTML page (plain form post). It holds no texts or limits: it loads `dist/contact.config.php`, which `build.py` generates from the content files as one PHP array (languages, default language, GitHub URL, the five length limits, result-page texts per language). The root `.htaccess` denies web access to that file. So the page, the script, the server and the prose all take a limit from the one value in `shared.json`.
- **Deployment**: the contents of `dist/` are uploaded to `htdocs/` on InfinityFree.

**Landing page.** After the author saw the first version, the home page was rebuilt as a landing page: a full-width hero, then one full-width band each for projects, education and activities, and a closing call to action. The bands reuse the same rendering functions as the detail pages (`project_cards`, `education_timeline`, `activity_cards`), so the content is written once. The detail pages remain for the learning portfolio, the tools list, the form and the privacy statement.

**Page structure.** Each page is: skip link, header (site name, primary navigation, language switch), `main` with one `h1` and sections, footer. The header and footer are produced by one function, so navigation is identical on all 15 pages.

**Navigation.** Five links, the current one marked with `aria-current="page"`. Below 760 px the links collapse behind a menu button (`aria-expanded`, closes on Escape). Without JavaScript the menu is always open.

**Language switching.** Each language is a separate URL tree, so the `lang` attribute, title, description and `hreflang` alternates are correct in the HTML itself and work without JavaScript. The switch is three plain links to the same file name in the other trees. `main.js` stores the last chosen language in `localStorage`; the root gateway reads it, then falls back to `navigator.languages`, then to English.

**Storage approach.**

| Data | Where | Why |
|---|---|---|
| Site content | JSON files in the repository | Versioned, reviewable, no database to secure |
| Language preference | `localStorage` key `lang` in the visitor's browser | Not sent to the server, not a cookie |
| Contact messages | `htdocs/data/messages.jsonl` on the host, directory closed by `.htaccess` | InfinityFree cannot send e-mail on the free plan; a file avoids database credentials |
| Source files | Git repository on GitHub, tagged release | Backup and traceability |

## 5. Design decisions and trade-offs

**DD-1. Separate static pages per language instead of client-side translation.**
Chosen: build 15 HTML files from JSON. Alternative: one set of pages with JavaScript swapping `data-i18n` strings.
Gain: correct `lang`, title and metadata without JavaScript; shareable language URLs; better for screen readers and search engines. Cost: a build step, and three times as many files to upload.

**DD-2. No CSS framework or web fonts.**
Chosen: one hand-written stylesheet (under 900 lines) with custom properties and the system font stack. Alternative: Bootstrap or Tailwind, both allowed by the brief.
Gain: no third-party requests (NFR-04), small pages (NFR-06), nothing to license, Kazakh letters render from system fonts. Cost: components such as the mobile menu are written and tested by hand, and the look depends slightly on the visitor's platform font.

**DD-3. No authentication.**
Chosen: the whole site is public and holds nothing private. Alternative: a PHP login protecting a private area.
Gain: no password storage, sessions or brute-force surface to defend on shared free hosting. Cost: no private gallery. The brief gives no credit for cosmetic login, and there is no private content that needs one.

**DD-4. Contact messages stored in a protected file instead of e-mail or a database.**
Gain: works on the free plan, no credentials in the repository. Cost: the owner must read messages through the hosting file manager, and the file must be cleared by hand.

## 6. Reuse and licences

| Component | Origin | Licence |
|---|---|---|
| Site code, styles, scripts, illustrations | Written for this project with AI assistance | MIT (see `LICENSE`) |
| Python standard library (build and tests) | python.org | PSF License, not redistributed |
| PlantUML (diagram rendering only) | plantuml.com | GPL, development tool, not redistributed |
| Third-party runtime libraries | none | |

Reuse inside the project: one layout function for all pages, one stylesheet, one content schema for three languages, one test suite parameterised over languages and pages.
