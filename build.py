#!/usr/bin/env python3
"""Build the trilingual static site into dist/.

Standard library only. Usage: python3 build.py
All visible text comes from content/<lang>.json; this file holds markup only.
The site is built in a temporary directory that replaces dist/ only on success.
"""

import json
import os
import re
import shutil
import sys
import tempfile
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
SRC = ROOT / "src"
DIST = ROOT / "dist"

CSS_URL = "/assets/css/style.css"
JS_URL = "/assets/js/main.js"
FAVICON_URL = "/assets/img/favicon.svg"
AVATAR_URL = "/assets/img/avatar.svg"
PHOTO_URL = "/assets/img/kbtu.webp"

# Decorative inline icons (drawn for this site). Always aria-hidden.
ICON_EXTERNAL = (
    '<svg class="icon" aria-hidden="true" focusable="false" viewBox="0 0 16 16" width="14" height="14">'
    '<path d="M6 3H3v10h10v-3M9 3h4v4M13 3 7.5 8.5" fill="none" stroke="currentColor" '
    'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)
ICON_ARROW = (
    '<svg class="icon" aria-hidden="true" focusable="false" viewBox="0 0 16 16" width="14" height="14">'
    '<path d="M3,8 h10 M9,4 l4,4 l-4,4" fill="none" stroke="currentColor" stroke-width="1.6" '
    'stroke-linecap="round" stroke-linejoin="round"/></svg>'
)
ICON_MENU = (
    '<svg class="icon" aria-hidden="true" focusable="false" viewBox="0 0 16 16" width="16" height="16">'
    '<path class="icon-open" d="M2 4h12M2 8h12M2 12h12" fill="none" stroke="currentColor" '
    'stroke-width="1.6" stroke-linecap="round"/>'
    '<path class="icon-close" d="M3 3l10 10M13 3 3 13" fill="none" stroke="currentColor" '
    'stroke-width="1.6" stroke-linecap="round"/></svg>'
)


# Pages that have a template in render_page().
PAGE_IDS = ("home", "education", "projects", "activities", "contact")
# Length limits in shared.json "form"; contact.php reads them from the generated config.
FORM_LIMITS = ("name_min", "name_max", "contact_max", "message_min", "message_max")
FORM_FIELDS = ("name", "contact", "message")
CONFIG_FILE = "contact.config.php"
PLACEHOLDER = re.compile(r"\{(\w+)\}")


class BuildError(Exception):
    pass


def e(value):
    """Escape any content value for use in HTML text or attribute values."""
    return escape(str(value), quote=True)


# ---------------------------------------------------------------- content

def load_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as error:
        raise BuildError(f"Cannot read {path}: {error}") from error


def flatten(node, prefix=""):
    """Return {dotted.key: leaf} for a nested structure of dicts and lists."""
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}.{key}" if prefix else key))
    elif isinstance(node, list):
        if not node:
            out[prefix + "[]"] = None
        for index, value in enumerate(node):
            out.update(flatten(value, f"{prefix}[{index}]"))
    else:
        out[prefix] = node
    return out


def require(node, path, where):
    """Return node[a][b]... for the dotted path, or fail with a clear message."""
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            raise BuildError(f"{where}: missing '{path}'")
        node = node[key]
    return node


def ids_of(shared, name, fields):
    """Ids of a shared.json list after checking each entry has the given fields."""
    entries = require(shared, name, "shared.json")
    if not isinstance(entries, list) or not entries:
        raise BuildError(f"shared.json: '{name}' must be a non-empty list")
    for index, entry in enumerate(entries):
        for field in fields:
            value = require(entry, field, f"shared.json: {name}[{index}]")
            if not isinstance(value, str) or not value:
                raise BuildError(f"shared.json: {name}[{index}].{field} must be a non-empty string")
    ids = [entry[fields[0]] for entry in entries]
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        raise BuildError(f"shared.json: duplicate {fields[0]} in '{name}': {duplicates}")
    return ids


def validate_shared(shared):
    """Check the shape of shared.json before any content file is read."""
    codes = ids_of(shared, "languages", ("code", "label", "name"))
    if require(shared, "default_lang", "shared.json") not in codes:
        raise BuildError("shared.json: default_lang is not in languages")

    pages = ids_of(shared, "pages", ("id", "file"))
    unknown = sorted(set(pages) - set(PAGE_IDS))
    if unknown:
        raise BuildError(f"shared.json: pages without a template in build.py: {unknown}")
    ids_of(shared, "subjects", ("id", "status"))
    ids_of(shared, "projects", ("id", "url"))

    urls = [require(shared, f"links.{name}", "shared.json") for name in ("github", "bot")]
    for url in urls + [project["url"] for project in shared["projects"]]:
        if not isinstance(url, str) or not url.startswith("https://"):
            raise BuildError(f"shared.json: external link must use https: {url}")

    for name in ("action", "required_marker"):
        value = require(shared, f"form.{name}", "shared.json")
        if not isinstance(value, str) or not value.strip():
            raise BuildError(f"shared.json: form.{name} must be a non-empty string")
    form = shared["form"]
    for name in FORM_LIMITS:
        value = require(form, name, "shared.json: form")
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise BuildError(f"shared.json: form.{name} must be a positive whole number")
    for field in ("name", "message"):
        if form[f"{field}_min"] > form[f"{field}_max"]:
            raise BuildError(f"shared.json: form.{field}_min is greater than form.{field}_max")
    return codes


def validate_ids(shared, texts):
    """Every id and status in shared.json has its texts in each language, and
    no subject or project text is left without an entry in shared.json."""
    for code, t in texts.items():
        where = f"{code}.json"
        for page in shared["pages"]:
            for key in ("nav", "title", "description"):
                require(t, f"pages.{page['id']}.{key}", where)
            if page["id"] != "home":
                for key in ("title", "text"):
                    require(t, f"home.cards.{page['id']}.{key}", where)
        for subject in shared["subjects"]:
            for key in ("name", "text"):
                require(t, f"education.portfolio.subjects.{subject['id']}.{key}", where)
            require(t, f"education.portfolio.status.{subject['status']}", where)
        for project in shared["projects"]:
            for key in ("name", "text", "features", "link"):
                require(t, f"projects.items.{project['id']}.{key}", where)
        for name, path in (("subjects", "education.portfolio.subjects"), ("projects", "projects.items")):
            listed = {entry["id"] for entry in shared[name]}
            unlisted = sorted(set(require(t, path, where)) - listed)
            if unlisted:
                raise BuildError(f"{where}: '{path}' has entries missing from shared.json {name}: {unlisted}")


def fill(text, values, where):
    """Replace each {key} in text with values[key]; an unknown key is an error."""
    def swap(match):
        key = match.group(1)
        if key not in values:
            raise BuildError(f"{where}: unknown placeholder {{{key}}}")
        return str(values[key])
    return PLACEHOLDER.sub(swap, text)


def fill_form_texts(shared, texts):
    """Put the limits and the required-field marker from shared.json into the
    form texts, so the prose cannot drift from the values that are enforced.
    result.invalid keeps its placeholders: contact.php fills them from the config."""
    form = shared["form"]
    for code, t in texts.items():
        strings = require(t, "contact.form", f"{code}.json")
        for key, text in strings.items():
            field = key.partition("_")[0]
            values = {}
            if key == "required_note":
                values = {"marker": form["required_marker"]}
            elif field in FORM_FIELDS:
                values = {"max": form[f"{field}_max"]}
                if f"{field}_min" in form:
                    values["min"] = form[f"{field}_min"]
            strings[key] = fill(text, values, f"{code}.json: contact.form.{key}")
        for key, text in require(t, "result", f"{code}.json").items():
            values = {name: form[name] for name in FORM_LIMITS} if key == "invalid" else {}
            fill(text, values, f"{code}.json: result.{key}")


def load_content():
    shared = load_json(CONTENT / "shared.json")
    codes = validate_shared(shared)
    texts = {code: load_json(CONTENT / f"{code}.json") for code in codes}

    flat = {code: flatten(texts[code]) for code in codes}
    reference = set(flat[codes[0]])
    for code in codes[1:]:
        missing = sorted(reference - set(flat[code]))
        extra = sorted(set(flat[code]) - reference)
        if missing or extra:
            raise BuildError(
                f"Key mismatch between {codes[0]}.json and {code}.json: "
                f"missing {missing}, extra {extra}"
            )
    for code in codes:
        for key, value in flat[code].items():
            if value is None:
                continue
            if not isinstance(value, str) or not value.strip():
                raise BuildError(f"{code}.json: '{key}' must be a non-empty string")

    validate_ids(shared, texts)
    fill_form_texts(shared, texts)
    return shared, texts


# ---------------------------------------------------------------- helpers

def page_url(shared, lang, page_id):
    for page in shared["pages"]:
        if page["id"] == page_id:
            if page["file"] == "index.html":
                return f"/{lang}/"
            return f"/{lang}/{page['file']}"
    raise BuildError(f"Unknown page id: {page_id}")


def absolute(shared, path):
    """Prefix a root-relative path with the site URL when one is configured."""
    return shared.get("site_url", "").rstrip("/") + path


# Decorative card icons (drawn for this site). Always aria-hidden.
ICON_PATHS = {
    "education": '<path d="M3,9 l9,-4 l9,4 l-9,4 z"/><path d="M7,11 v4 c0,1.6 2.4,3 5,3 s5,-1.4 5,-3 v-4"/><path d="M21,9 v5"/>',
    "projects": '<path d="M8,7 l-5,5 l5,5"/><path d="M16,7 l5,5 l-5,5"/><path d="M13.5,5 l-3,14"/>',
    "activities": '<path d="M12,3 l2.2,5.6 L20,11 l-5.8,2.4 L12,19 l-2.2,-5.6 L4,11 l5.8,-2.4 z"/>',
    "contact": '<path d="M4,5 h16 v11 H9 l-5,4 z"/><path d="M8,9 h8"/><path d="M8,12 h5"/>',
    "interests": '<circle cx="12" cy="12" r="9"/><path d="M15.5,8.5 l-2,5 l-5,2 l2,-5 z"/>',
    "achievements": '<circle cx="12" cy="14" r="5"/><path d="M9,3 l3,6 l3,-6"/>',
    "extracurricular": '<path d="M12,20 c-4,-2.6 -7,-5.6 -7,-9.4 c0,-3.6 4.6,-4.8 7,-1.6 c2.4,-3.2 7,-2 7,1.6 c0,3.8 -3,6.8 -7,9.4 z"/>',
    "plans": '<path d="M5,21 V4"/><path d="M5,4 h11 l-2,4 l2,4 H5"/>',
    "jobfinder": '<path d="M12,3 v3"/><rect x="4" y="6" width="16" height="12" rx="3"/><path d="M9,11 v2"/><path d="M15,11 v2"/>',
    "smartcampus": '<path d="M4,21 V6 l8,-3 l8,3 v15"/><path d="M9,21 v-5 h6 v5"/><path d="M8,10 h2"/><path d="M14,10 h2"/>',
    "shag": '<path d="M4,20 h4 v-4 h4 v-4 h4 V8 h4"/>',
}


def icon_tile(name):
    return (
        f'<span class="tile tile-{e(name)}" aria-hidden="true">'
        '<svg class="tile-icon" aria-hidden="true" focusable="false" viewBox="0 0 24 24" width="24" height="24" '
        'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f'{ICON_PATHS[name]}</svg></span>'
    )


def external_link(t, url, label):
    return (
        f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer">'
        f'{e(label)}{ICON_EXTERNAL}'
        f'<span class="visually-hidden"> {e(t["a11y"]["new_tab"])}</span></a>'
    )


def head(lang, title, description, extra=""):
    return f"""<!DOCTYPE html>
<html lang="{e(lang)}"{extra}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta name="color-scheme" content="light dark">
"""


def head_assets():
    return f"""<link rel="icon" href="{FAVICON_URL}" type="image/svg+xml">
<link rel="stylesheet" href="{CSS_URL}">
<script src="{JS_URL}"></script>
</head>
"""


# ---------------------------------------------------------------- layout

def layout(shared, texts, lang, page_id, body):
    """Wrap page content in the shared head, header and footer."""
    t = texts[lang]
    meta = t["pages"][page_id]

    alternates = "".join(
        f'<link rel="alternate" hreflang="{e(l["code"])}" '
        f'href="{e(absolute(shared, page_url(shared, l["code"], page_id)))}">\n'
        for l in shared["languages"]
    )
    default_href = (
        absolute(shared, "/") if page_id == "home"
        else absolute(shared, page_url(shared, shared["default_lang"], page_id))
    )
    alternates += f'<link rel="alternate" hreflang="x-default" href="{e(default_href)}">\n'

    nav_items = ""
    for page in shared["pages"]:
        current = ' aria-current="page"' if page["id"] == page_id else ""
        nav_items += (
            f'<li><a href="{e(page_url(shared, lang, page["id"]))}"{current}>'
            f'{e(t["pages"][page["id"]]["nav"])}</a></li>\n'
        )

    lang_items = ""
    for l in shared["languages"]:
        current = ' aria-current="true"' if l["code"] == lang else ""
        lang_items += (
            f'<li><a href="{e(page_url(shared, l["code"], page_id))}" lang="{e(l["code"])}" '
            f'hreflang="{e(l["code"])}" data-lang="{e(l["code"])}"{current}>'
            f'{e(l["label"])}<span class="visually-hidden"> {e(l["name"])}</span></a></li>\n'
        )

    main_class = "landing" if page_id == "home" else "container"

    return (
        head(lang, meta["title"], meta["description"])
        + alternates
        + head_assets()
        + f"""<body>
<a class="skip-link" href="#main">{e(t["a11y"]["skip"])}</a>
<header class="site-header">
<div class="container header-inner">
<a class="brand" href="{e(page_url(shared, lang, "home"))}">{e(t["site"]["name"])}</a>
<button type="button" class="menu-toggle" aria-expanded="false" aria-controls="site-nav" hidden>
{ICON_MENU}<span>{e(t["a11y"]["menu"])}</span>
</button>
<nav id="site-nav" class="site-nav" aria-label="{e(t["a11y"]["nav_primary"])}">
<ul>
{nav_items}</ul>
</nav>
<nav class="lang-switch" aria-label="{e(t["a11y"]["nav_language"])}">
<ul>
{lang_items}</ul>
</nav>
</div>
</header>
<main id="main" class="{main_class}" tabindex="-1">
{body}</main>
<footer class="site-footer">
<div class="container footer-inner">
<p>{e(t["footer"]["copyright"])}</p>
<ul>
<li>{external_link(t, shared["links"]["github"], t["footer"]["github"])}</li>
<li><a href="{e(page_url(shared, lang, "contact"))}#privacy">{e(t["footer"]["privacy"])}</a></li>
</ul>
</div>
</footer>
</body>
</html>
"""
    )


# ---------------------------------------------------------------- pages

def campus_photo(shared, t):
    """Photograph of the university building with its licence credit (CC BY-SA requires both)."""
    return f"""<figure class="photo">
<img src="{PHOTO_URL}" width="320" height="180" loading="lazy" alt="{e(t["photo"]["alt"])}">
<figcaption>{external_link(t, shared["links"]["photo_source"], t["photo"]["credit"])}</figcaption>
</figure>
"""


def education_timeline(t, level):
    """University and school cards, newest first. Shared by the landing and education pages."""
    ed = t["education"]
    uni, school = ed["university"], ed["school"]
    return f"""<div class="cards timeline">
<section class="card" aria-labelledby="university-heading">
<h{level} id="university-heading">{e(uni["heading"])}</h{level}>
<p class="card-name">{e(uni["name"])}</p>
<dl class="facts">
<div><dt>{e(uni["city_label"])}</dt><dd>{e(uni["city"])}</dd></div>
<div><dt>{e(uni["major_label"])}</dt><dd>{e(uni["major"])}</dd></div>
<div><dt>{e(uni["year_label"])}</dt><dd>{e(uni["year"])}</dd></div>
</dl>
</section>
<section class="card" aria-labelledby="school-heading">
<h{level} id="school-heading">{e(school["heading"])}</h{level}>
<p class="card-name">{e(school["name"])}</p>
<dl class="facts">
<div><dt>{e(school["city_label"])}</dt><dd>{e(school["city"])}</dd></div>
<div><dt>{e(school["graduation_label"])}</dt><dd>{e(school["graduation"])}</dd></div>
</dl>
</section>
</div>
"""


def project_cards(shared, t, level):
    """One article per project. Shared by the landing and projects pages."""
    pr = t["projects"]
    items = ""
    for project in shared["projects"]:
        text = pr["items"][project["id"]]
        featured = bool(project.get("featured"))
        badge = f'<p class="badge">{e(pr["featured"])}</p>\n' if featured else ""
        features = ""
        if text["features"]:
            features = (
                "<ul>\n"
                + "".join(f"<li>{e(item)}</li>\n" for item in text["features"])
                + "</ul>\n"
            )
        items += f"""<article class="card project{' project-featured' if featured else ''}" aria-labelledby="project-{e(project["id"])}">
{badge}{icon_tile(project["id"])}<h{level} id="project-{e(project["id"])}">{e(text["name"])}</h{level}>
<p>{e(text["text"])}</p>
{features}<p>{external_link(t, project["url"], text["link"])}</p>
</article>
"""
    return f'<div class="projects">\n{items}</div>\n'


def activity_cards(t, level, grid):
    ac = t["activities"]
    sections = ""
    for key in ("interests", "achievements", "extracurricular", "plans"):
        sections += f"""<section class="card" aria-labelledby="{key}-heading">
{icon_tile(key)}<h{level} id="{key}-heading">{e(ac[key]["heading"])}</h{level}>
<p>{e(ac[key]["text"])}</p>
</section>
"""
    return f'<div class="cards {grid}">\n{sections}</div>\n'


def band(band_id, heading, lead, body, more="", tint=False):
    """One full-width section of the landing page."""
    return f"""<section class="band{' band-tint' if tint else ''}" aria-labelledby="{band_id}-band">
<div class="container" data-reveal>
<h2 id="{band_id}-band">{e(heading)}</h2>
<p class="lead">{e(lead)}</p>
{body}{more}</div>
</section>
"""


def render_home(shared, t, lang):
    """Landing page: hero with a sample bot card, figures, one band per section, questions, call to action."""
    h = t["home"]
    uni = t["education"]["university"]
    facts = "".join(f"<li>{e(uni[key])}</li>\n" for key in ("major", "city", "year"))

    def more(page_id):
        return (
            f'<p class="band-more"><a class="button button-secondary" '
            f'href="{e(page_url(shared, lang, page_id))}">{e(h["cards"][page_id]["title"])}'
            f'{ICON_ARROW}</a></p>\n'
        )

    demo = h["demo"]
    match = int(shared["demo_match"])
    segments = "".join(
        f'<span{" class=\"on\"" if index < round(match / 10) else ""}></span>' for index in range(10)
    )
    hero = f"""<section class="band band-hero">
<span class="hero-glow hero-glow-a" aria-hidden="true"></span>
<span class="hero-glow hero-glow-b" aria-hidden="true"></span>
<div class="container hero-grid">
<div class="hero-copy">
<div class="eyebrow">
<img class="avatar" src="{AVATAR_URL}" width="56" height="56" alt="{e(t["site"]["monogram_alt"])}">
<p class="role">{e(h["role"])}</p>
</div>
<h1>{e(t["site"]["name"])}</h1>
<p class="lead">{e(h["intro"])}</p>
<p class="actions">
<a class="button" href="{e(page_url(shared, lang, "projects"))}">{e(h["cta_projects"])}{ICON_ARROW}</a>
<a class="button button-secondary" href="{e(page_url(shared, lang, "contact"))}">{e(h["cta_contact"])}</a>
</p>
<ul class="hero-facts">
{facts}</ul>
</div>
<figure class="demo">
<div class="demo-card">
<p class="demo-title">{e(demo["title"])}</p>
<p class="demo-place">{e(demo["place"])}</p>
<p class="demo-match"><span>{e(demo["match"])}</span> <strong>{match}%</strong></p>
<div class="meter" aria-hidden="true">{segments}</div>
<dl class="demo-skills">
<div><dt>{e(demo["have_label"])}</dt><dd>{e(demo["have"])}</dd></div>
<div><dt>{e(demo["learn_label"])}</dt><dd>{e(demo["learn"])}</dd></div>
</dl>
</div>
<figcaption>{e(demo["caption"])}</figcaption>
</figure>
</div>
</section>
"""
    counts = (
        ("languages", len(shared["languages"])),
        ("projects", len(shared["projects"])),
        ("subjects", len(shared["subjects"])),
    )
    stats = "".join(
        f'<li><strong>{count}</strong> <span>{e(h["stats"][key])}</span></li>\n' for key, count in counts
    )
    figures = f"""<div class="stats-band">
<ul class="container stats">
{stats}</ul>
</div>
"""
    questions = "".join(
        f"<details>\n<summary>{e(item['q'])}</summary>\n<p>{e(item['a'])}</p>\n</details>\n"
        for item in h["faq"]["items"]
    )
    contact = t["contact"]
    cta = f"""<section class="band band-cta" aria-labelledby="contact-band">
<span class="hero-glow hero-glow-a" aria-hidden="true"></span>
<div class="container" data-reveal>
<h2 id="contact-band">{e(contact["form"]["heading"])}</h2>
<p class="lead">{e(h["cards"]["contact"]["text"])}</p>
<p class="actions">
<a class="button" href="{e(page_url(shared, lang, "contact"))}">{e(h["cta_contact"])}{ICON_ARROW}</a>
<a class="button button-secondary" href="{e(shared["links"]["github"])}" target="_blank" rel="noopener noreferrer">{e(t["footer"]["github"])}{ICON_EXTERNAL}<span class="visually-hidden"> {e(t["a11y"]["new_tab"])}</span></a>
</p>
</div>
</section>
"""
    return (
        hero
        + figures
        + band("projects", t["projects"]["heading"], h["cards"]["projects"]["text"],
               project_cards(shared, t, 3), more("projects"))
        + band("education", t["education"]["heading"], h["cards"]["education"]["text"],
               '<div class="edu-split">\n' + campus_photo(shared, t) + education_timeline(t, 3) + "</div>\n",
               more("education"), tint=True)
        + band("activities", t["activities"]["heading"], h["cards"]["activities"]["text"],
               activity_cards(t, 3, "cards-two"), more("activities"))
        + band("faq", h["faq"]["heading"], h["faq"]["lead"],
               f'<div class="faq">\n{questions}</div>\n', tint=True)
        + cta
    )


def render_education(shared, t):
    ed = t["education"]
    portfolio = ed["portfolio"]
    subjects = ""
    for subject in shared["subjects"]:
        text = portfolio["subjects"][subject["id"]]
        subjects += f"""<li class="subject">
<div>
<h3>{e(text["name"])}</h3>
<p>{e(text["text"])}</p>
</div>
<p class="status"><span class="visually-hidden">{e(portfolio["status_label"])} </span>{e(portfolio["status"][subject["status"]])}</p>
</li>
"""
    return f"""<h1>{e(ed["heading"])}</h1>
<p class="lead">{e(ed["lead"])}</p>
<div class="edu-split">
{campus_photo(shared, t)}{education_timeline(t, 2)}</div>
<section aria-labelledby="portfolio-heading">
<h2 id="portfolio-heading">{e(portfolio["heading"])}</h2>
<p>{e(portfolio["intro"])}</p>
<ul class="subjects">
{subjects}</ul>
</section>
"""


def render_projects(shared, t):
    pr = t["projects"]
    tools = "".join(f"<li>{e(item)}</li>\n" for item in pr["tools"]["items"])
    return f"""<h1>{e(pr["heading"])}</h1>
<p class="lead">{e(pr["lead"])}</p>
{project_cards(shared, t, 2)}<section aria-labelledby="tools-heading">
<h2 id="tools-heading">{e(pr["tools"]["heading"])}</h2>
<p>{e(pr["tools"]["intro"])}</p>
<ul class="tags">
{tools}</ul>
</section>
"""


def render_activities(t):
    ac = t["activities"]
    return f"""<h1>{e(ac["heading"])}</h1>
<p class="lead">{e(ac["lead"])}</p>
{activity_cards(t, 2, "cards-two")}"""


def render_contact(shared, t, lang):
    c = t["contact"]
    f, links, limits = c["form"], c["links"], shared["form"]
    privacy = "".join(f"<li>{e(item)}</li>\n" for item in c["privacy"]["items"])
    star = f'<span class="required" aria-hidden="true">{e(limits["required_marker"])}</span>'
    return f"""<h1>{e(c["heading"])}</h1>
<p class="lead">{e(c["lead"])}</p>
<section aria-labelledby="links-heading">
<h2 id="links-heading">{e(links["heading"])}</h2>
<ul class="link-list">
<li>{external_link(t, shared["links"]["github"], links["github_label"])}<span class="link-note">{e(links["github_text"])}</span></li>
<li>{external_link(t, shared["links"]["bot"], links["bot_label"])}<span class="link-note">{e(links["bot_text"])}</span></li>
</ul>
</section>
<section aria-labelledby="form-heading">
<h2 id="form-heading">{e(f["heading"])}</h2>
<form class="contact-form" action="{e(limits["action"])}" method="post" accept-charset="utf-8" data-contact
 data-msg-sending="{e(f["sending"])}"
 data-msg-success="{e(f["success"])}"
 data-msg-error="{e(f["error"])}"
 data-msg-rate="{e(f["error_rate"])}"
 data-msg-field="{e(f["error_field"])}"
 data-alt-url="{e(shared["links"]["github"])}"
 data-alt-label="{e(links["github_label"])}"
 data-alt-note="{e(t["a11y"]["new_tab"])}">
<p class="form-note">{e(f["required_note"])}</p>
<input type="hidden" name="lang" value="{e(lang)}">
<div class="hp" aria-hidden="true">
<label for="hp_field">{e(f["honeypot_label"])}</label>
<input type="text" id="hp_field" name="hp_field" tabindex="-1" autocomplete="off">
</div>
<div class="field">
<label for="name">{e(f["name_label"])} {star}</label>
<input type="text" id="name" name="name" required minlength="{e(limits["name_min"])}" maxlength="{e(limits["name_max"])}" autocomplete="name"
 aria-describedby="name-hint name-error" data-validate
 data-msg-required="{e(f["name_required"])}" data-msg-short="{e(f["name_short"])}" data-msg-long="{e(f["name_long"])}">
<p class="hint" id="name-hint">{e(f["name_hint"])}</p>
<p class="field-error" id="name-error" hidden></p>
</div>
<div class="field">
<label for="contact">{e(f["contact_label"])}</label>
<input type="text" id="contact" name="contact" maxlength="{e(limits["contact_max"])}" autocomplete="off"
 aria-describedby="contact-hint contact-error" data-validate
 data-msg-long="{e(f["contact_long"])}">
<p class="hint" id="contact-hint">{e(f["contact_hint"])}</p>
<p class="field-error" id="contact-error" hidden></p>
</div>
<div class="field">
<label for="message">{e(f["message_label"])} {star}</label>
<textarea id="message" name="message" rows="7" required minlength="{e(limits["message_min"])}" maxlength="{e(limits["message_max"])}"
 aria-describedby="message-hint message-error" data-validate
 data-msg-required="{e(f["message_required"])}" data-msg-short="{e(f["message_short"])}" data-msg-long="{e(f["message_long"])}"></textarea>
<p class="hint" id="message-hint">{e(f["message_hint"])}</p>
<p class="field-error" id="message-error" hidden></p>
</div>
<button type="submit" class="button">{e(f["submit"])}</button>
<div class="form-status" id="form-status" role="status" aria-live="polite"></div>
</form>
</section>
<section id="privacy" class="card privacy" aria-labelledby="privacy-heading">
<h2 id="privacy-heading">{e(c["privacy"]["heading"])}</h2>
<ul>
{privacy}</ul>
</section>
"""


def render_page(page_id, shared, t, lang):
    """Body of one language page. PAGE_IDS lists the ids handled here."""
    if page_id == "home":
        return render_home(shared, t, lang)
    if page_id == "education":
        return render_education(shared, t)
    if page_id == "projects":
        return render_projects(shared, t)
    if page_id == "activities":
        return render_activities(t)
    if page_id == "contact":
        return render_contact(shared, t, lang)
    raise BuildError(f"Unknown page id: {page_id}")


def render_gateway(shared, texts):
    """Root page: main.js redirects; the links work without JavaScript."""
    default = shared["default_lang"]
    t = texts[default]
    codes = ",".join(l["code"] for l in shared["languages"])
    choices = ""
    noscript = ""
    for l in shared["languages"]:
        code = l["code"]
        choices += (
            f'<li lang="{e(code)}"><span class="choice-label">{e(texts[code]["gateway"]["choose"])}</span> '
            f'<a class="button button-secondary" href="{e(page_url(shared, code, "home"))}" '
            f'hreflang="{e(code)}" data-lang="{e(code)}">{e(l["name"])}</a></li>\n'
        )
        noscript += f'<p lang="{e(code)}">{e(texts[code]["gateway"]["noscript"])}</p>\n'
    alternates = "".join(
        f'<link rel="alternate" hreflang="{e(l["code"])}" '
        f'href="{e(absolute(shared, page_url(shared, l["code"], "home")))}">\n'
        for l in shared["languages"]
    )
    return (
        head(default, t["gateway"]["title"], t["gateway"]["description"],
             f' data-gateway data-langs="{e(codes)}" data-default="{e(default)}"')
        + alternates
        + head_assets()
        + f"""<body class="plain-page">
<main id="main" class="container">
<img class="avatar" src="{AVATAR_URL}" width="96" height="96" alt="{e(t["site"]["monogram_alt"])}">
<h1>{e(t["site"]["name"])}</h1>
<ul class="choices">
{choices}</ul>
<noscript>
{noscript}</noscript>
</main>
</body>
</html>
"""
    )


def render_404(shared, texts):
    """One error page for all languages; every URL is root-relative."""
    default = shared["default_lang"]
    t = texts[default]
    blocks = ""
    for l in shared["languages"]:
        code = l["code"]
        nf = texts[code]["notfound"]
        blocks += f"""<section class="card" lang="{e(code)}">
<h2>{e(nf["heading"])}</h2>
<p>{e(nf["text"])}</p>
<p><a href="{e(page_url(shared, code, "home"))}" hreflang="{e(code)}" data-lang="{e(code)}">{e(nf["home"])}</a></p>
</section>
"""
    return (
        head(default, t["notfound"]["title"], t["notfound"]["text"])
        + '<meta name="robots" content="noindex">\n'
        + head_assets()
        + f"""<body class="plain-page">
<main id="main" class="container">
<h1>{e(t["notfound"]["code"])}</h1>
<div class="cards cards-three">
{blocks}</div>
</main>
</body>
</html>
"""
    )


# ---------------------------------------------------------------- form config

def php_string(value):
    """A PHP single-quoted string literal: only backslash and quote are special."""
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def php_value(value, depth=1):
    """PHP source for a nested structure of dicts, lists, strings and whole numbers."""
    if isinstance(value, dict):
        pad = "    " * depth
        rows = "".join(
            f"{pad}{php_string(key)} => {php_value(item, depth + 1)},\n" for key, item in value.items()
        )
        return "[\n" + rows + "    " * (depth - 1) + "]"
    if isinstance(value, list):
        return "[" + ", ".join(php_value(item, depth) for item in value) + "]"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return php_string(value)
    raise BuildError(f"Cannot write {type(value).__name__} to {CONFIG_FILE}")


def render_form_config(shared, texts):
    """contact.config.php: everything contact.php needs from the content files."""
    result_texts = {}
    for l in shared["languages"]:
        t = texts[l["code"]]
        form = t["contact"]["form"]
        result_texts[l["code"]] = {
            **t["result"],
            "ok": form["success"],
            "rate": form["error_rate"],
            "server": form["error"],
            "new_tab": t["a11y"]["new_tab"],
        }
    config = {
        "langs": [l["code"] for l in shared["languages"]],
        "default_lang": shared["default_lang"],
        "github_url": shared["links"]["github"],
        "limits": {name: shared["form"][name] for name in FORM_LIMITS},
        "texts": result_texts,
    }
    return (
        "<?php\n"
        "// Generated by build.py from content/*.json. Do not edit: change the content files and rebuild.\n"
        "\n"
        f"return {php_value(config)};\n"
    )


# ---------------------------------------------------------------- build

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def copy_file(source, target):
    if not source.is_file():
        raise BuildError(f"Missing source file: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def build_into(out, shared, texts):
    """Write the complete site into the empty directory out. Returns the page count."""
    count = 0
    for l in shared["languages"]:
        lang = l["code"]
        for page in shared["pages"]:
            body = render_page(page["id"], shared, texts[lang], lang)
            write(out / lang / page["file"], layout(shared, texts, lang, page["id"], body))
            count += 1

    write(out / "index.html", render_gateway(shared, texts))
    write(out / "404.html", render_404(shared, texts))

    assets = SRC / "assets"
    if not assets.is_dir():
        raise BuildError(f"Missing directory: {assets}")
    shutil.copytree(assets, out / "assets", ignore=shutil.ignore_patterns(".DS_Store"))
    copy_file(SRC / "contact.php", out / "contact.php")
    write(out / CONFIG_FILE, render_form_config(shared, texts))
    copy_file(SRC / "htaccess" / "root.htaccess", out / ".htaccess")
    copy_file(SRC / "htaccess" / "data.htaccess", out / "data" / ".htaccess")
    return count


def build():
    shared, texts = load_content()

    # Build next to dist/ (same file system), then swap: a failed build leaves
    # the previous dist/ untouched.
    staging = Path(tempfile.mkdtemp(prefix=".dist-new-", dir=ROOT))
    previous = ROOT / (staging.name + ".old")
    try:
        count = build_into(staging, shared, texts)
        os.chmod(staging, 0o755)
        if DIST.exists():
            DIST.rename(previous)
        try:
            staging.rename(DIST)
        except OSError:
            if previous.exists():
                previous.rename(DIST)
            raise
    except OSError as error:
        raise BuildError(f"Cannot write the site: {error}") from error
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(previous, ignore_errors=True)

    print(f"Built {count} language pages, index.html and 404.html in {DIST}")


if __name__ == "__main__":
    try:
        build()
    except BuildError as error:
        print(f"Build failed: {error}", file=sys.stderr)
        sys.exit(1)
