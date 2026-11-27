# Merey Bakhytzhan: personal website

A static personal website in Kazakh, Russian and English, built for the KBTU Software Engineering course (TSIS #01, "Vibe-Coded Personal Website") and hosted on InfinityFree.

- **Live site:** see `docs/05-launch.md` (filled in at deployment)
- **AI tool used:** Claude Code (model Claude Fable 5.2). Prompts and responses are in `ai/`.

## What is in the site

| Page | Content |
|---|---|
| Home | Introduction and language selector |
| Education | KBTU, major, previous school, learning portfolio |
| Projects | Merey Job Finder bot, Smart Campus checker, «Шаг» |
| Activities | Interests, achievements, volunteering, future plans |
| Contact | GitHub link, contact form, privacy statement |

Each page exists as `/kk/…`, `/ru/…` and `/en/…`. The language switch always opens the same page in the other language.

## How it works

Content is kept in `content/kk.json`, `content/ru.json` and `content/en.json`. `build.py` renders it into plain HTML in `dist/`. The only server-side code is `src/contact.php`, which validates a contact message and stores it in a directory closed to web access. There are no frameworks, no third-party requests, no cookies and no dependencies.

## Commands

Requires Python 3.9 or newer. Nothing to install.

```
python3 build.py                        # build the site into dist/
python3 -m unittest discover tests -v   # run the automated checks
python3 -m http.server 8000 -d dist     # preview at http://localhost:8000
```

The contact form needs PHP, so it only works on the host; the local preview shows its error state.

## Deployment

1. Run `python3 build.py`.
2. Upload the **contents** of `dist/` (including the hidden `.htaccess` and the `data/` folder) into `htdocs/` on InfinityFree with the File Manager or FTP.
3. Open the HTTPS address of the subdomain and run the hosted checks in `docs/04-testing.md`.

## Repository layout

```
content/     site text in three languages + shared data
build.py     templates and renderer
src/         styles, script, images, contact.php, .htaccess sources
tests/       automated checks
docs/        requirements, privacy review, design, diagrams, wireframes, tests, launch record
ai/          saved AI prompts, responses and evaluation
AGENTS.md    instructions for AI coding agents
```

## Documents

- `docs/01-requirements.md`: requirements, user stories, acceptance criteria, backlog, iterations
- `docs/02-content-privacy-ethics.md`: content inventory, data classification, risk assessment
- `docs/03-design.md`: sitemap, architecture, design decisions; diagrams in `docs/diagrams/*.puml`
- `docs/04-testing.md`: traceability table, test results, defects, security review
- `docs/05-launch.md`: public URL, release, hosting limitations, reflection

## Licence

Code, text and illustrations are original work released under the MIT licence (`LICENSE`). No third-party assets or libraries are included.
