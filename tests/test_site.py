"""Automated checks on the built site (dist/).

Run from the repository root:

    python3 -m unittest discover tests -v

Standard library only, no browser, no network. setUpModule builds the site
once; every test then reads the files in dist/. Each test names the acceptance
criterion (AC-xx) or non-functional requirement (NFR-xx) from
docs/01-requirements.md that it verifies.
"""

import json
import re
import subprocess
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
CONTENT = ROOT / "content"
SRC = ROOT / "src"

PAGE_BUDGET_BYTES = 150_000  # NFR-06: under 150 KB per page
MAX_FIXED_WIDTH_PX = 320     # NFR-01: narrowest supported viewport
KAZAKH_LETTERS = set("әғқңөұүіӘҒҚҢӨҰҮІ")
MOJIBAKE_MARKERS = ("�", "Ð", "Ñ", "Ò", "Ó", "Ã", "â€")

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
}

# Filled by setUpModule.
SHARED = {}
TEXTS = {}
LANGS = []
PAGES = []        # (lang, page_id, file_name, path)
DOCS = {}         # path -> Document


# --------------------------------------------------------------- tiny DOM

class Node:
    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.parent = parent
        self.children = []   # Node or str

    def iter(self):
        """This node and all descendant element nodes, in document order."""
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.iter()

    def find_all(self, tag=None, **attrs):
        wanted = {key.rstrip("_").replace("_", "-"): value for key, value in attrs.items()}
        out = []
        for node in self.iter():
            if node is self:
                continue
            if tag is not None and node.tag != tag:
                continue
            if all(
                (key in node.attrs) if value is True else (node.attrs.get(key) == value)
                for key, value in wanted.items()
            ):
                out.append(node)
        return out

    def find(self, tag=None, **attrs):
        found = self.find_all(tag, **attrs)
        return found[0] if found else None

    def classes(self):
        return (self.attrs.get("class") or "").split()

    def by_class(self, name):
        return [node for node in self.iter() if node is not self and name in node.classes()]

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def text(self):
        """Visible text with collapsed whitespace (script and style skipped)."""
        parts = []

        def walk(node):
            for child in node.children:
                if isinstance(child, str):
                    parts.append(child)
                elif child.tag not in ("script", "style"):
                    walk(child)

        walk(self)
        return " ".join("".join(parts).split())


class Document(HTMLParser):
    """Parses one HTML file into a Node tree and records structural errors."""

    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.root = Node("#document")
        self.stack = [self.root]
        self.errors = []
        self.feed(source)
        self.close()
        for node in self.stack[1:]:
            self.errors.append(f"<{node.tag}> is never closed")

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if self.stack[-1].tag == tag:
            self.stack.pop()
            return
        line = self.getpos()[0]
        if any(node.tag == tag for node in self.stack[1:]):
            self.errors.append(f"line {line}: </{tag}> closes an open <{self.stack[-1].tag}>")
            while self.stack[-1].tag != tag:
                self.stack.pop()
            self.stack.pop()
        else:
            self.errors.append(f"line {line}: stray </{tag}>")

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    # Shortcuts used by the tests.
    def find_all(self, tag=None, **attrs):
        return self.root.find_all(tag, **attrs)

    def find(self, tag=None, **attrs):
        return self.root.find(tag, **attrs)

    def ids(self):
        return [node.attrs["id"] for node in self.root.iter() if "id" in node.attrs]

    def by_id(self, value):
        return self.find(id=value)


# --------------------------------------------------------------- helpers

def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def flatten(node, prefix=""):
    """{dotted.key: leaf} for nested dicts and lists (independent of build.py)."""
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}.{key}" if prefix else key))
    elif isinstance(node, list):
        out[prefix + "[]"] = len(node)
        for index, value in enumerate(node):
            out.update(flatten(value, f"{prefix}[{index}]"))
    else:
        out[prefix] = node
    return out


def own_origin():
    return (SHARED.get("site_url") or "").rstrip("/")


def strip_origin(url):
    origin = own_origin()
    if origin and url.startswith(origin):
        return url[len(origin):] or "/"
    return url


def is_external(url):
    """True for any URL that leaves this site (has a scheme or is protocol-relative)."""
    url = strip_origin(url)
    return url.startswith("//") or re.match(r"[A-Za-z][A-Za-z0-9+.\-]*:", url) is not None


def resolve(url, page_path):
    """Map an internal URL to (file path in dist, fragment or None)."""
    url = strip_origin(url)
    url, _, fragment = url.partition("#")
    url = url.partition("?")[0]
    if not url:
        target = page_path
    elif url.startswith("/"):
        target = DIST / url.lstrip("/")
    else:
        target = page_path.parent / url
    if url.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target, (fragment or None)


def url_refs(doc):
    """Every (node, attribute, value) that carries a URL."""
    out = []
    for node in doc.root.iter():
        for attr in ("href", "src", "action", "poster", "data"):
            if attr in node.attrs and node.tag != "#document":
                out.append((node, attr, node.attrs[attr] or ""))
    return out


def rel_path(path):
    return path.relative_to(DIST).as_posix()


def dist_files():
    return sorted(path for path in DIST.rglob("*") if path.is_file())


def all_html_paths():
    return [path for _, _, _, path in PAGES] + [DIST / "index.html", DIST / "404.html"]


def strip_css_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def media_blocks(css, condition_pattern):
    """Bodies of the @media blocks whose prelude matches condition_pattern."""
    bodies = []
    for match in re.finditer(r"@media([^{]*)\{", css):
        if not re.search(condition_pattern, match.group(1)):
            continue
        depth, index = 1, match.end()
        while depth and index < len(css):
            depth += {"{": 1, "}": -1}.get(css[index], 0)
            index += 1
        bodies.append(css[match.end():index - 1])
    return bodies


def php_int_constants(source):
    return {name: int(value) for name, value in re.findall(r"^const (\w+) = (\d+);", source, re.M)}


def php_texts(source):
    """The TEXT table of contact.php as {lang: {key: string}}."""
    out = {}
    for lang, block in re.findall(r"^    '(\w+)' => \[\n(.*?)^    \],", source, re.S | re.M):
        entries = re.findall(r"^\s*'(\w+)' => '((?:[^'\\]|\\.)*)',", block, re.M)
        out[lang] = {key: value.replace("\\'", "'").replace("\\\\", "\\") for key, value in entries}
    return out


def php_function(source, name):
    """Source text of one top-level function of contact.php."""
    match = re.search(r"^function " + re.escape(name) + r"\(.*?^\}", source, re.S | re.M)
    return match.group(0) if match else ""


def php_request_code(source):
    """The part of contact.php that runs for each request (after the function definitions)."""
    return source.partition("request */")[2]


def css_rules(css):
    """(selector, body) for every innermost rule of a stylesheet without comments."""
    return [(selector.strip(), body) for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]


def setUpModule():
    result = subprocess.run(
        [sys.executable, "build.py"], cwd=ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"python3 build.py failed ({result.returncode}):\n{result.stdout}\n{result.stderr}"
        )
    SHARED.clear()
    SHARED.update(read_json(CONTENT / "shared.json"))
    LANGS[:] = [lang["code"] for lang in SHARED["languages"]]
    TEXTS.clear()
    TEXTS.update({lang: read_json(CONTENT / f"{lang}.json") for lang in LANGS})
    PAGES[:] = [
        (lang, page["id"], page["file"], DIST / lang / page["file"])
        for lang in LANGS
        for page in SHARED["pages"]
    ]
    DOCS.clear()
    for path in all_html_paths():
        if path.is_file():
            DOCS[path] = Document(path.read_text(encoding="utf-8"))


class PageItem(tuple):
    """A tuple of page data that also carries the label used for its subTest."""

    def __new__(cls, label, values):
        item = super().__new__(cls, values)
        item.label = label
        return item


class SiteTestCase(unittest.TestCase):
    maxDiff = None

    def doc(self, path):
        self.assertIn(path, DOCS, f"{path} was not built")
        return DOCS[path]

    def each_page(self, page_id=None):
        """(lang, page_id, file_name, path, doc) for the language pages; .label names the subTest."""
        return [
            PageItem(f"{lang}/{file_name}", (lang, pid, file_name, path, self.doc(path)))
            for lang, pid, file_name, path in PAGES
            if page_id is None or pid == page_id
        ]

    def each_html(self):
        """(path, doc) for the 15 pages plus the gateway and the 404 page; .label names the subTest."""
        return [PageItem(rel_path(path), (path, self.doc(path))) for path in all_html_paths()]

    def home_links(self, doc, page_path):
        """Languages whose home page the document links to."""
        found = set()
        for link in doc.find_all("a", href=True):
            href = link.attrs["href"]
            if is_external(href):
                continue
            target, _ = resolve(href, page_path)
            for lang in LANGS:
                if target == DIST / lang / "index.html":
                    found.add(lang)
        return found


# --------------------------------------------------------------- build output

class TestBuildOutput(SiteTestCase):
    def test_nfr07_build_produces_expected_files(self):
        """NFR-07: one build command produces 3 languages x 5 pages plus the root files."""
        self.assertEqual(sorted(LANGS), ["en", "kk", "ru"])
        self.assertEqual(len(SHARED["pages"]), 5)
        self.assertEqual(len(PAGES), 15)
        expected = [path for _, _, _, path in PAGES] + [
            DIST / "index.html", DIST / "404.html", DIST / "contact.php",
            DIST / ".htaccess", DIST / "data" / ".htaccess",
            DIST / "assets" / "css" / "style.css", DIST / "assets" / "js" / "main.js",
        ]
        for path in expected:
            with self.subTest(file=rel_path(path)):
                self.assertTrue(path.is_file(), f"missing {path}")
                self.assertGreater(path.stat().st_size, 0)

    def test_ac13_html_is_well_formed(self):
        """AC-13 / NFR-03: every tag is closed in order and ids are unique on each page."""
        for item in self.each_html():
            with self.subTest(page=item.label):
                path, doc = item
                self.assertTrue(doc.source.lstrip().lower().startswith("<!doctype html>"))
                self.assertEqual(doc.errors, [])
                ids = doc.ids()
                duplicates = sorted({value for value in ids if ids.count(value) > 1})
                self.assertEqual(duplicates, [], "duplicate id values")


# --------------------------------------------------------------- AC-01

class TestHome(SiteTestCase):
    def test_ac01_gateway_links_to_all_language_homes(self):
        """AC-01 (FR-11): the root page shows the name and links to /kk/, /ru/ and /en/."""
        path = DIST / "index.html"
        doc = self.doc(path)
        self.assertEqual(self.home_links(doc, path), set(LANGS))
        headings = doc.find_all("h1")
        self.assertEqual(len(headings), 1)
        self.assertEqual(headings[0].text(), TEXTS[SHARED["default_lang"]]["site"]["name"])
        html = doc.find("html")
        self.assertIn("data-gateway", html.attrs)
        self.assertEqual(html.attrs.get("data-langs", "").split(","), LANGS)
        self.assertEqual(html.attrs.get("data-default"), SHARED["default_lang"])
        self.assertIsNotNone(doc.find("noscript"), "manual hint for visitors without JavaScript")

    def test_ac01_home_has_name_role_intro_and_language_switch(self):
        """AC-01: each home page has the author's name in h1, a role line, an intro and a language switch."""
        for item in self.each_page("home"):
            with self.subTest(page=item.label):
                lang, _, _, _, doc = item
                t = TEXTS[lang]
                headings = doc.find_all("h1")
                self.assertEqual(len(headings), 1)
                self.assertEqual(headings[0].text(), t["site"]["name"])
                roles = doc.root.by_class("role")
                self.assertEqual(len(roles), 1, "one role line")
                self.assertEqual(roles[0].text(), t["home"]["role"])
                main_text = doc.find("main").text()
                self.assertIn(" ".join(t["home"]["intro"].split()), main_text)
                switches = [nav for nav in doc.find_all("nav") if "lang-switch" in nav.classes()]
                self.assertEqual(len(switches), 1, "one language switch")
                self.assertEqual(len(switches[0].find_all("a", href=True)), len(LANGS))


# --------------------------------------------------------------- AC-02, NFR-02

class TestNavigation(SiteTestCase):
    def test_ac02_language_switch_points_to_same_page_in_each_language(self):
        """AC-02 (FR-09): three links to the same file in /kk/, /ru/, /en/, current language marked."""
        for item in self.each_page():
            with self.subTest(page=item.label):
                lang, _, file_name, path, doc = item
                switches = [nav for nav in doc.find_all("nav") if "lang-switch" in nav.classes()]
                self.assertEqual(len(switches), 1)
                self.assertTrue(switches[0].attrs.get("aria-label"), "language nav needs a name")
                links = switches[0].find_all("a")
                self.assertEqual(len(links), 3)
                targets = {}
                for link in links:
                    target, _ = resolve(link.attrs.get("href", ""), path)
                    code = link.attrs.get("hreflang")
                    targets[code] = target
                    self.assertEqual(link.attrs.get("lang"), code, "link text language")
                    self.assertEqual(link.attrs.get("data-lang"), code, "main.js stores data-lang")
                    self.assertTrue(link.text(), "link needs text")
                self.assertEqual(targets, {code: DIST / code / file_name for code in LANGS})
                current = [link for link in links if "aria-current" in link.attrs]
                self.assertEqual(len(current), 1, "exactly one current language")
                self.assertEqual(current[0].attrs.get("hreflang"), lang)
                self.assertIn(current[0].attrs["aria-current"], ("true", "page"))

    def test_ac02_nfr02_internal_links_resolve(self):
        """AC-02 / NFR-02: every internal href, src and action resolves to a file (and id) in dist/."""
        for item in self.each_html():
            with self.subTest(page=item.label):
                path, doc = item
                for node, attr, value in url_refs(doc):
                    if is_external(value):
                        continue
                    target, fragment = resolve(value, path)
                    where = f"<{node.tag} {attr}=\"{value}\">"
                    self.assertTrue(target.is_file(), f"{where} -> missing {target}")
                    self.assertIn(DIST, target.resolve().parents, f"{where} leaves dist/")
                    if fragment and target in DOCS:
                        self.assertIn(fragment, DOCS[target].ids(), f"{where}: no element with that id")

    def test_nfr02_primary_nav_links_all_pages_and_marks_current(self):
        """NFR-02 (FR-10): primary nav links all five pages of the language; one aria-current="page"."""
        for item in self.each_page():
            with self.subTest(page=item.label):
                lang, _, _, path, doc = item
                nav = doc.by_id("site-nav")
                self.assertIsNotNone(nav, "primary navigation #site-nav")
                self.assertEqual(nav.tag, "nav")
                self.assertTrue(nav.attrs.get("aria-label"))
                links = nav.find_all("a", href=True)
                targets = [resolve(link.attrs["href"], path)[0] for link in links]
                expected = [DIST / lang / page["file"] for page in SHARED["pages"]]
                self.assertEqual(sorted(targets), sorted(expected))
                for link in links:
                    self.assertTrue(link.text(), "navigation link needs text")
                current = [link for link in links if link.attrs.get("aria-current") == "page"]
                self.assertEqual(len(current), 1, 'exactly one aria-current="page"')
                self.assertEqual(resolve(current[0].attrs["href"], path)[0], path)
                others = [link for link in links if "aria-current" in link.attrs and link not in current]
                self.assertEqual(others, [])


# --------------------------------------------------------------- AC-03, NFR-08

class TestInternationalisation(SiteTestCase):
    def test_nfr08_content_files_have_identical_keys_and_no_empty_strings(self):
        """NFR-08 (R-01): kk.json, ru.json and en.json have the same key sets and no empty strings."""
        flat = {lang: flatten(TEXTS[lang]) for lang in LANGS}
        reference = set(flat["en"])
        for lang in LANGS:
            with self.subTest(lang=lang):
                self.assertEqual(sorted(reference - set(flat[lang])), [], "keys missing")
                self.assertEqual(sorted(set(flat[lang]) - reference), [], "extra keys")
                for key, value in flat[lang].items():
                    if key.endswith("[]"):
                        self.assertEqual(value, flat["en"][key], f"list length of {key}")
                        continue
                    self.assertIsInstance(value, str, key)
                    self.assertTrue(value.strip(), f"empty string at {key}")

    def test_nfr08_russian_name_stays_in_the_nominative(self):
        """NFR-08 (R-01, D-11): in ru.json the undeclined name never follows a word that governs another case."""
        name = TEXTS["ru"]["site"]["name"]
        allowed = re.compile(r"(?:^|· |© \d{4} )" + re.escape(name))
        for key, value in flatten(TEXTS["ru"]).items():
            if not isinstance(value, str) or name not in value:
                continue
            with self.subTest(key=key):
                self.assertEqual(len(allowed.findall(value)), value.count(name),
                                 f"name is not at the start of the phrase: {value!r}")

    def test_nfr08_reviewed_wording_is_not_reintroduced(self):
        """NFR-08 (R-01, R-03, D-12): overstated or awkward phrases removed after the review stay out."""
        banned = {
            "en": ("I build backend services", "subject olympiad"),
            "ru": ("Пишу бэкенд", "инструменты с помощью ИИ", "предметн"),
            "kk": ("бэкенд, Telegram-боттар және ЖИ көмегімен құралдар жасаймын",
                   "деңгей бағасынсыз", "пәндік", "Атыңыз", "Ат "),
        }
        for lang, phrases in banned.items():
            flat = flatten(TEXTS[lang])
            for key, value in flat.items():
                if not isinstance(value, str):
                    continue
                for phrase in phrases:
                    with self.subTest(lang=lang, key=key, phrase=phrase):
                        self.assertNotIn(phrase, value)
        form = TEXTS["kk"]["contact"]["form"]
        self.assertEqual(form["name_label"], "Есіміңіз")
        for key in ("name_required", "name_short", "name_long"):
            with self.subTest(key=key):
                self.assertRegex(form[key], r"^Есім")

    def test_nfr08_files_are_utf8_without_bom_or_mojibake(self):
        """NFR-08 / AC-03: every text file in dist/ and content/ decodes as UTF-8, with no mojibake."""
        files = [p for p in dist_files() if p.suffix in (".html", ".css", ".js", ".php", ".svg", "")]
        files += sorted(CONTENT.glob("*.json"))
        for path in files:
            with self.subTest(file=str(path.relative_to(ROOT))):
                raw = path.read_bytes()
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM")
                text = raw.decode("utf-8")  # raises on invalid bytes
                for marker in MOJIBAKE_MARKERS:
                    self.assertNotIn(marker, text, "double-encoded text")

    def test_ac03_lang_attribute_and_charset(self):
        """AC-03 / NFR-08: <html lang> matches the directory and <meta charset="utf-8"> comes first."""
        for item in self.each_page():
            with self.subTest(page=item.label):
                lang, _, _, path, doc = item
                self.assertEqual(doc.find("html").attrs.get("lang"), lang)
                metas = doc.find("head").find_all("meta")
                self.assertEqual((metas[0].attrs.get("charset") or "").lower(), "utf-8")
                self.assertLess(path.read_bytes().lower().find(b'<meta charset="utf-8">'), 1024)
        for name in ("index.html", "404.html"):
            with self.subTest(page=name):
                doc = self.doc(DIST / name)
                self.assertEqual(doc.find("html").attrs.get("lang"), SHARED["default_lang"])
                self.assertEqual(
                    (doc.find("head").find_all("meta")[0].attrs.get("charset") or "").lower(), "utf-8"
                )

    def test_ac03_title_and_description_are_localised(self):
        """AC-03 / NFR-08: non-empty title and description from the content file, different per language."""
        seen = {}
        for item in self.each_page():
            with self.subTest(page=item.label):
                lang, page_id, _, _, doc = item
                titles = doc.find_all("title")
                self.assertEqual(len(titles), 1)
                title = titles[0].text()
                descriptions = doc.find_all("meta", name="description")
                self.assertEqual(len(descriptions), 1)
                description = (descriptions[0].attrs.get("content") or "").strip()
                self.assertTrue(title)
                self.assertTrue(description)
                meta = TEXTS[lang]["pages"][page_id]
                self.assertEqual(title, " ".join(meta["title"].split()))
                self.assertEqual(description, meta["description"].strip())
                seen.setdefault(page_id, {})[lang] = (title, description)
        for page_id, by_lang in seen.items():
            with self.subTest(page=page_id):
                self.assertEqual(len({value[0] for value in by_lang.values()}), len(LANGS),
                                 "titles must differ between languages")
                self.assertEqual(len({value[1] for value in by_lang.values()}), len(LANGS),
                                 "descriptions must differ between languages")

    def test_ac03_kazakh_and_russian_pages_use_their_alphabets(self):
        """AC-03: Kazakh pages contain Kazakh-specific letters; Russian pages contain Cyrillic text."""
        for item in self.each_page():
            with self.subTest(page=item.label):
                lang, _, _, _, doc = item
                main_text = doc.find("main").text()
                head_text = doc.find("title").text() + doc.find("meta", name="description").attrs["content"]
                if lang == "kk":
                    self.assertTrue(KAZAKH_LETTERS & set(main_text), "no Kazakh letters in <main>")
                    self.assertTrue(KAZAKH_LETTERS & set(head_text), "no Kazakh letters in title/description")
                elif lang == "ru":
                    self.assertGreater(len(re.findall(r"[а-яё]", main_text)), 100)
                    self.assertTrue(re.search(r"[а-яё]", head_text))
                else:
                    cyrillic = len(re.findall(r"[а-яёәғқңөұүі]", main_text, re.I))
                    self.assertLess(cyrillic, 0.05 * len(main_text), "English page is mostly not English")


# --------------------------------------------------------------- AC-04, AC-05

class TestEducation(SiteTestCase):
    def test_ac04_education_shows_university_major_year_and_school(self):
        """AC-04 (FR-02): the education page shows KBTU, the major, the year and the previous school."""
        for item in self.each_page("education"):
            with self.subTest(page=item.label):
                lang, _, _, _, doc = item
                text = doc.find("main").text()
                ed = TEXTS[lang]["education"]
                for group, key in (
                    ("university", "name"), ("university", "major"), ("university", "year"),
                    ("school", "name"), ("school", "graduation"),
                ):
                    value = " ".join(ed[group][key].split())
                    self.assertIn(value, text, f"education.{group}.{key}")
    
    def test_ac05_education_lists_every_subject_with_status(self):
        """AC-05 (FR-03): one entry per subject in shared.json with name, description and status."""
        for item in self.each_page("education"):
            with self.subTest(page=item.label):
                lang, _, _, _, doc = item
                portfolio = TEXTS[lang]["education"]["portfolio"]
                entries = doc.find("main").by_class("subject")
                self.assertEqual(len(entries), len(SHARED["subjects"]))
                for entry, subject in zip(entries, SHARED["subjects"]):
                    expected = portfolio["subjects"][subject["id"]]
                    heading = entry.find("h3")
                    self.assertIsNotNone(heading, subject["id"])
                    self.assertEqual(heading.text(), " ".join(expected["name"].split()))
                    self.assertIn(" ".join(expected["text"].split()), entry.text())
                    statuses = entry.by_class("status")
                    self.assertEqual(len(statuses), 1, f"status of {subject['id']}")
                    self.assertIn(subject["status"], portfolio["status"], "unknown status code")
                    self.assertTrue(
                        statuses[0].text().endswith(portfolio["status"][subject["status"]]),
                        f"status text of {subject['id']}: {statuses[0].text()!r}",
                    )


# --------------------------------------------------------------- AC-06

class TestExternalLinks(SiteTestCase):
    def test_ac06_external_links_are_https_and_open_safely_in_new_tab(self):
        """AC-06: every external link is https, target="_blank" and rel contains noopener."""
        total = 0
        for item in self.each_html():
            with self.subTest(page=item.label):
                path, doc = item
                for link in doc.find_all("a", href=True):
                    href = link.attrs["href"]
                    if not is_external(href):
                        continue
                    total += 1
                    self.assertTrue(href.startswith("https://"), f"not https: {href}")
                    self.assertEqual(link.attrs.get("target"), "_blank", href)
                    self.assertIn("noopener", (link.attrs.get("rel") or "").split(), href)
                    self.assertTrue(link.text(), f"link without text: {href}")
        self.assertGreater(total, 0, "no external links were found at all")

    def test_ac06_every_project_is_on_each_projects_page(self):
        """AC-06 (FR-05): every project in shared.json appears with its name and link."""
        for item in self.each_page("projects"):
            with self.subTest(page=item.label):
                lang, _, _, _, doc = item
                main = doc.find("main")
                items = TEXTS[lang]["projects"]["items"]
                articles = main.find_all("article")
                self.assertEqual(len(articles), len(SHARED["projects"]))
                for article, project in zip(articles, SHARED["projects"]):
                    text = items[project["id"]]
                    self.assertTrue(project["url"].startswith("https://"))
                    heading = article.find("h2")
                    self.assertIsNotNone(heading)
                    self.assertEqual(heading.text(), " ".join(text["name"].split()))
                    links = article.find_all("a", href=project["url"])
                    self.assertEqual(len(links), 1, f"link to {project['url']}")
                    self.assertIn(TEXTS[lang]["a11y"]["new_tab"], links[0].text(),
                                  "new-tab warning for screen readers")
                    for feature in text["features"]:
                        self.assertIn(" ".join(feature.split()), article.text())

    def test_ac06_shared_links_are_https(self):
        """AC-06: all URLs configured in shared.json use https."""
        urls = list(SHARED["links"].values()) + [p["url"] for p in SHARED["projects"]]
        for url in urls:
            with self.subTest(url=url):
                self.assertRegex(url, r"^https://[a-z0-9.-]+\.[a-z]{2,}(/|$)")


# --------------------------------------------------------------- AC-07, AC-08, NFR-01

class TestResponsive(SiteTestCase):
    def css(self):
        return strip_css_comments((DIST / "assets" / "css" / "style.css").read_text(encoding="utf-8"))

    def test_nfr01_viewport_meta_on_every_page(self):
        """AC-07 / NFR-01: every page has a device-width viewport meta that does not block zoom."""
        for item in self.each_html():
            with self.subTest(page=item.label):
                _, doc = item
                metas = doc.find_all("meta", name="viewport")
                self.assertEqual(len(metas), 1)
                content = metas[0].attrs.get("content", "").replace(" ", "")
                self.assertIn("width=device-width", content)
                self.assertIn("initial-scale=1", content)
                self.assertNotIn("user-scalable=no", content)
                self.assertNotRegex(content, r"maximum-scale=1(\.0)?(,|$)")

    def test_ac08_stylesheet_has_min_width_breakpoint_with_inline_nav(self):
        """AC-07 / AC-08: mobile-first CSS; a min-width media query hides the menu button and shows the nav."""
        css = self.css()
        blocks = media_blocks(css, r"min-width\s*:\s*\d+(px|em|rem)")
        self.assertTrue(blocks, "no @media (min-width: ...) rule")
        self.assertEqual(media_blocks(css, r"max-width\s*:"), [], "max-width queries are not mobile-first")
        wide = "\n".join(blocks)
        self.assertRegex(wide, r"\.menu-toggle[^{]*\{[^}]*display\s*:\s*none",
                         "menu button must be hidden on wide screens")
        self.assertRegex(wide, r"\.site-nav[^{]*\{[^}]*display\s*:\s*block",
                         "navigation must be shown inline on wide screens")
        # Outside the breakpoints the menu only collapses when JavaScript can reopen it.
        screen = css
        for body in media_blocks(css, r"\bprint\b"):
            screen = screen.replace(body, "")
        for rule in re.findall(r"([^{}]*\.site-nav[^{}]*)\{[^}]*display\s*:\s*none", screen):
            self.assertIn(".js ", rule, "nav hidden without the .js guard")

    def test_nfr01_privacy_box_is_separated_from_the_form(self):
        """NFR-01 (D-10): the privacy card keeps a top margin, set after .card resets it to 0."""
        css = self.css()
        selectors = [selector for selector, _ in css_rules(css)]
        spaced = [
            (index, body) for index, (selector, body) in enumerate(css_rules(css))
            if selector == ".privacy" and re.search(r"margin-top\s*:\s*var\(--space-[5-9]\)", body)
        ]
        self.assertTrue(spaced, "no .privacy { margin-top: var(--space-5 or more) } rule")
        self.assertIn(".card", selectors)
        self.assertGreater(spaced[0][0], selectors.index(".card"),
                           ".privacy must come after .card, which sets margin-top: 0")

    def test_nfr01_no_fixed_width_above_320px(self):
        """AC-07 / NFR-01: no rule fixes a width above 320 px (static check for horizontal scroll)."""
        css = re.sub(r"@media[^{]*", "@media ", self.css())
        pattern = (
            r"(?<![\w-])(width|min-width|inline-size|min-inline-size|flex-basis|grid-template-columns)"
            r"\s*:\s*([^;}]+)"
        )
        checked = 0
        for prop, value in re.findall(pattern, css):
            checked += 1
            if re.search(r"(?<![a-z])(min|clamp)\(", value):
                continue
            for number, unit in re.findall(r"(\d*\.?\d+)(px|rem|em|pt)\b", value):
                pixels = float(number) * {"px": 1, "rem": 16, "em": 16, "pt": 4 / 3}[unit]
                with self.subTest(declaration=f"{prop}: {value.strip()}"):
                    self.assertLessEqual(pixels, MAX_FIXED_WIDTH_PX)
        self.assertGreater(checked, 0)
        self.assertRegex(css, r"(?<![\w.-])img\s*\{[^}]*max-width\s*:\s*100%", "images must shrink")
        self.assertNotRegex(css, r"overflow-x\s*:\s*(scroll|hidden)", "overflow must not be masked")
        for item in self.each_html():
            with self.subTest(page=item.label):
                _, doc = item
                for node in doc.root.iter():
                    width = node.attrs.get("width", "")
                    if width.isdigit():
                        self.assertLessEqual(int(width), MAX_FIXED_WIDTH_PX, f"<{node.tag} width>")


# --------------------------------------------------------------- AC-09 to AC-11

FIELDS = ("name", "contact", "message")


HONEYPOT_NAME = "hp_field"
# Words that browser autofill and password managers match in name, id or autocomplete.
AUTOFILL_WORDS = re.compile(
    r"(?i)web|site|url|mail|phone|tel|name|address|street|city|zip|post|company|org|user|login|pass"
)


class TestContactForm(SiteTestCase):
    def form(self, doc):
        forms = doc.find_all("form")
        self.assertEqual(len(forms), 1, "one form on the contact page")
        return forms[0]

    def honeypot(self, form):
        boxes = form.by_class("hp")
        self.assertEqual(len(boxes), 1, "one honeypot container (.hp)")
        inputs = boxes[0].find_all("input")
        self.assertEqual(len(inputs), 1, "one honeypot field")
        return inputs[0]

    def test_ac09_honeypot_has_a_neutral_name(self):
        """AC-09 (R-05, D-03): the honeypot is not named like a field that autofill tools complete."""
        php = (DIST / "contact.php").read_text(encoding="utf-8")
        for item in self.each_page("contact"):
            with self.subTest(page=item.label):
                _, _, _, _, doc = item
                honeypot = self.honeypot(self.form(doc))
                self.assertEqual(honeypot.attrs.get("name"), HONEYPOT_NAME)
                self.assertEqual(honeypot.attrs.get("id"), HONEYPOT_NAME)
                for attr in ("name", "id"):
                    self.assertNotRegex(honeypot.attrs[attr], AUTOFILL_WORDS, f"honeypot {attr}")
                self.assertEqual(honeypot.attrs.get("autocomplete"), "off")
        self.assertNotIn("$_POST['website']", php)
        self.assertRegex(
            php,
            r"\$_POST\['" + HONEYPOT_NAME + r"'\][^}]*\{\s*respond\(400, 'invalid_request', \$lang\);",
            "a filled honeypot is still answered with 400",
        )

    def test_ac10_ac11_status_region_stays_rendered_while_empty(self):
        """AC-10 / AC-11 (D-01): the live region exists before its text arrives, so the result is announced."""
        css = strip_css_comments((DIST / "assets" / "css" / "style.css").read_text(encoding="utf-8"))
        script = (DIST / "assets" / "js" / "main.js").read_text(encoding="utf-8")
        hide = r"display\s*:\s*none|visibility\s*:\s*hidden"
        for selector, body in css_rules(css):
            if ".form-status" not in selector:
                continue
            with self.subTest(selector=selector):
                self.assertNotIn(":empty", selector, "the empty live region must not get its own rule")
                self.assertNotRegex(body, hide, "the live region must stay in the accessibility tree")
                if selector == ".form-status":
                    self.assertNotRegex(body, r"(?<![\w-])(margin|padding)[\w-]*\s*:",
                                        "spacing belongs to the state classes, the empty region takes no room")
        # Every text the script shows has a state class, and each state class has spacing.
        self.assertNotRegex(script, r"setStatus\(''\s*,\s*messages\.", "status text without a state class")
        kinds = sorted(set(re.findall(r"setStatus\('(\w+)'", script)))
        self.assertTrue({"success", "error"} <= set(kinds), kinds)
        for kind in kinds:
            with self.subTest(state=kind):
                bodies = [body for selector, body in css_rules(css)
                          if f".form-status.is-{kind}" in [part.strip() for part in selector.split(",")]]
                self.assertTrue(any(re.search(r"margin-top\s*:", body) for body in bodies),
                                f".form-status.is-{kind} needs margin-top")
        for item in self.each_page("contact"):
            with self.subTest(page=item.label):
                _, _, _, _, doc = item
                status = self.form(doc).by_class("form-status")
                self.assertEqual(len(status), 1)
                self.assertNotIn("hidden", status[0].attrs)
                self.assertNotEqual(status[0].attrs.get("aria-hidden"), "true")

    def test_ac09_form_structure(self):
        """AC-09 / AC-10 (FR-07): labelled name, contact and message fields, honeypot, POST, live region."""
        for item in self.each_page("contact"):
            with self.subTest(page=item.label):
                lang, _, _, path, doc = item
                form = self.form(doc)
                self.assertEqual(form.attrs.get("method", "").lower(), "post")
                self.assertEqual(form.attrs.get("action"), SHARED["form"]["action"])
                self.assertEqual(resolve(form.attrs["action"], path)[0], DIST / "contact.php")
                self.assertIn("data-contact", form.attrs, "main.js looks for form[data-contact]")

                for name in FIELDS:
                    controls = [n for n in form.iter() if n.attrs.get("name") == name]
                    self.assertEqual(len(controls), 1, f"field {name}")
                    control = controls[0]
                    self.assertIn(control.tag, ("input", "textarea"))
                    labels = form.find_all("label", for_=control.attrs.get("id"))
                    self.assertEqual(len(labels), 1, f"label for {name}")
                    self.assertIn(TEXTS[lang]["contact"]["form"][f"{name}_label"], labels[0].text())
                    for ref in control.attrs.get("aria-describedby", "").split():
                        self.assertIsNotNone(doc.by_id(ref), f"aria-describedby={ref}")
                    error = doc.by_id(f"{control.attrs.get('id')}-error")
                    self.assertIsNotNone(error, f"error box for {name} (main.js: field.id + '-error')")
                    self.assertIn(error.attrs["id"], control.attrs.get("aria-describedby", "").split())
                    self.assertIn("hidden", error.attrs)
                    self.assertEqual(error.text(), "")
                self.assertIn("required", form.find(name="name").attrs)
                self.assertIn("required", form.find(name="message").attrs)
                self.assertNotIn("required", form.find(name="contact").attrs, "reply contact is optional")

                honeypot = self.honeypot(form)
                self.assertEqual(honeypot.attrs.get("tabindex"), "-1")
                self.assertNotIn("required", honeypot.attrs)
                self.assertEqual(honeypot.attrs.get("value", ""), "")
                self.assertTrue(
                    any(a.attrs.get("aria-hidden") == "true" for a in honeypot.ancestors()),
                    "honeypot must be hidden from assistive technology",
                )

                hidden_lang = form.find("input", name="lang")
                self.assertIsNotNone(hidden_lang, "contact.php needs the page language")
                self.assertEqual(hidden_lang.attrs.get("type"), "hidden")
                self.assertEqual(hidden_lang.attrs.get("value"), lang)

                status = [n for n in form.iter() if n.attrs.get("aria-live") in ("polite", "assertive")]
                self.assertEqual(len(status), 1, "one aria-live status region")
                self.assertIn("form-status", status[0].classes(), "main.js looks for .form-status")
                self.assertEqual(status[0].text(), "")
                submits = form.find_all("button", type="submit")
                self.assertEqual(len(submits), 1)
                self.assertEqual(submits[0].text(), TEXTS[lang]["contact"]["form"]["submit"])

    def test_ac09_ac10_ac11_localised_messages_for_every_key_the_script_uses(self):
        """AC-09, AC-10, AC-11: every message key read by main.js exists on the page, localised."""
        script = (DIST / "assets" / "js" / "main.js").read_text(encoding="utf-8")
        to_attr = lambda key: "data-" + re.sub(r"[A-Z]", lambda m: "-" + m.group(0).lower(), key)
        form_keys = sorted(set(re.findall(r"\bmessages\.(\w+)", script)))
        field_keys = sorted(set(re.findall(r"\bfield\.dataset\.(msg\w+)", script)))
        self.assertTrue({"msgSending", "msgSuccess", "msgError", "msgRate", "msgField", "altUrl"}
                        <= set(form_keys), form_keys)
        self.assertEqual(field_keys, ["msgLong", "msgRequired", "msgShort"])

        seen = {}
        for item in self.each_page("contact"):
            with self.subTest(page=item.label):
                lang, _, _, _, doc = item
                form = self.form(doc)
                strings = TEXTS[lang]["contact"]["form"]
                for key in form_keys:
                    value = form.attrs.get(to_attr(key), "")
                    self.assertTrue((value or "").strip(), f"form is missing {to_attr(key)}")
                    seen.setdefault(to_attr(key), {})[lang] = value
                for attr, key in (
                    ("data-msg-sending", "sending"), ("data-msg-success", "success"),
                    ("data-msg-error", "error"), ("data-msg-rate", "error_rate"),
                    ("data-msg-field", "error_field"),
                ):
                    self.assertEqual(form.attrs.get(attr), strings[key], attr)
                # AC-11: the error message points to the alternative contact link.
                self.assertEqual(form.attrs.get("data-alt-url"), SHARED["links"]["github"])
                self.assertEqual(form.attrs.get("data-alt-label"),
                                 TEXTS[lang]["contact"]["links"]["github_label"])

                validated = [n for n in form.iter() if "data-validate" in n.attrs]
                self.assertEqual(sorted(n.attrs.get("name") for n in validated), sorted(FIELDS))
                for control in validated:
                    name = control.attrs["name"]
                    needed = ["long"]
                    if "required" in control.attrs:
                        needed.append("required")
                    if int(control.attrs.get("data-min", "0")) > 0:
                        needed.append("short")
                    for kind in needed:
                        attr = f"data-msg-{kind}"
                        value = control.attrs.get(attr, "")
                        self.assertEqual(value, strings[f"{name}_{kind}"], f"{name} {attr}")
                        seen.setdefault(f"{name} {attr}", {})[lang] = value

        for key, by_lang in seen.items():
            if key in ("data-alt-url", "data-alt-label"):
                continue  # a URL and a profile name: the same in every language
            with self.subTest(message=key):
                self.assertEqual(set(by_lang), set(LANGS))
                self.assertEqual(len(set(by_lang.values())), len(LANGS),
                                 f"{key} is not translated: {by_lang}")

    def test_ac09_length_limits_match_between_page_script_and_server(self):
        """AC-09 / NFR-05: HTML attributes, data-* limits and contact.php use the limits from shared.json."""
        limits = SHARED["form"]
        php = php_int_constants((DIST / "contact.php").read_text(encoding="utf-8"))
        expected_php = {
            "NAME_MIN": limits["name_min"], "NAME_MAX": limits["name_max"],
            "CONTACT_MAX": limits["contact_max"],
            "MESSAGE_MIN": limits["message_min"], "MESSAGE_MAX": limits["message_max"],
        }
        self.assertEqual({key: php.get(key) for key in expected_php}, expected_php)
        self.assertEqual(
            (SRC / "contact.php").read_bytes(), (DIST / "contact.php").read_bytes(),
            "dist/contact.php must be the reviewed source file",
        )

        for item in self.each_page("contact"):
            with self.subTest(page=item.label):
                lang, _, _, _, doc = item
                form = self.form(doc)
                hints = TEXTS[lang]["contact"]["form"]
                for name in FIELDS:
                    control = form.find(name=name)
                    low = limits.get(f"{name}_min", 0)
                    high = limits[f"{name}_max"]
                    self.assertEqual(control.attrs.get("maxlength"), str(high), f"{name} maxlength")
                    self.assertEqual(control.attrs.get("data-max"), str(high), f"{name} data-max")
                    self.assertEqual(control.attrs.get("data-min"), str(low), f"{name} data-min")
                    if low:
                        self.assertEqual(control.attrs.get("minlength"), str(low), f"{name} minlength")
                    numbers = re.findall(r"\d+", hints[f"{name}_hint"])
                    for limit in ([low] if low else []) + [high]:
                        self.assertIn(str(limit), numbers, f"{name}_hint does not mention {limit}")
                    if low:
                        self.assertIn(str(low), re.findall(r"\d+", hints[f"{name}_short"]))
                    self.assertIn(str(high), re.findall(r"\d+", hints[f"{name}_long"]))

    def test_ac10_ac11_server_fallback_texts_match_content(self):
        """AC-10 / AC-11: contact.php (no-JavaScript reply) uses the same languages, link and messages."""
        source = (DIST / "contact.php").read_text(encoding="utf-8")
        langs = re.search(r"^const LANGS = \[(.*?)\];", source, re.M)
        self.assertIsNotNone(langs)
        self.assertEqual(sorted(re.findall(r"'(\w+)'", langs.group(1))), sorted(LANGS))
        self.assertIn(f"const DEFAULT_LANG = '{SHARED['default_lang']}';", source)
        self.assertIn(f"const GITHUB_URL = '{SHARED['links']['github']}';", source)
        texts = php_texts(source)
        self.assertEqual(sorted(texts), sorted(LANGS))
        limits = SHARED["form"]
        for lang in LANGS:
            with self.subTest(lang=lang):
                strings = TEXTS[lang]["contact"]["form"]
                self.assertEqual(texts[lang].get("ok"), strings["success"])
                self.assertEqual(texts[lang].get("rate"), strings["error_rate"])
                self.assertEqual(texts[lang].get("server"), strings["error"])
                numbers = re.findall(r"\d+", texts[lang].get("invalid", ""))
                for key in ("name_min", "name_max", "contact_max", "message_min", "message_max"):
                    self.assertIn(str(limits[key]), numbers, f"'invalid' text does not mention {key}")
                for key in ("title_ok", "title_fail", "method", "back"):
                    self.assertTrue(texts[lang].get(key, "").strip(), key)


# --------------------------------------------------------------- AC-12, AC-13, NFR-03

def is_focusable(node):
    if node.attrs.get("tabindex") == "-1" or "disabled" in node.attrs:
        return False
    if node.tag == "a":
        return "href" in node.attrs
    if node.tag == "input":
        return node.attrs.get("type") != "hidden"
    if node.tag in ("button", "select", "textarea", "summary"):
        return True
    return "tabindex" in node.attrs


class TestAccessibility(SiteTestCase):
    def test_ac12_skip_link_is_first_focusable_and_target_exists(self):
        """AC-12 (FR-10): the skip link is the first focusable element and points to <main>."""
        for item in self.each_page():
            with self.subTest(page=item.label):
                lang, _, _, _, doc = item
                focusable = [node for node in doc.find("body").iter() if is_focusable(node)]
                self.assertTrue(focusable)
                first = focusable[0]
                self.assertEqual(first.tag, "a")
                self.assertIn("skip-link", first.classes())
                self.assertEqual(first.text(), TEXTS[lang]["a11y"]["skip"])
                href = first.attrs.get("href", "")
                self.assertTrue(href.startswith("#") and len(href) > 1, href)
                target = doc.by_id(href[1:])
                self.assertIsNotNone(target, f"skip target {href}")
                self.assertEqual(target.tag, "main")
                self.assertEqual(target.attrs.get("tabindex"), "-1", "target must accept focus")
                positive = [n for n in doc.root.iter() if n.attrs.get("tabindex", "0").lstrip("-").isdigit()
                            and int(n.attrs.get("tabindex", "0")) > 0]
                self.assertEqual(positive, [], "positive tabindex changes the focus order")

    def test_ac12_menu_button_has_state_and_controls_navigation(self):
        """AC-12 / AC-07: the menu button has aria-expanded and aria-controls pointing to the nav."""
        script = (DIST / "assets" / "js" / "main.js").read_text(encoding="utf-8")
        self.assertIn("'Escape'", script, "menu must close with Escape")
        self.assertIn("aria-expanded", script)
        for item in self.each_page():
            with self.subTest(page=item.label):
                lang, _, _, _, doc = item
                buttons = [b for b in doc.find_all("button") if "menu-toggle" in b.classes()]
                self.assertEqual(len(buttons), 1, "one menu button (.menu-toggle)")
                button = buttons[0]
                self.assertEqual(button.attrs.get("type"), "button")
                self.assertEqual(button.attrs.get("aria-expanded"), "false")
                controlled = doc.by_id(button.attrs.get("aria-controls", ""))
                self.assertIsNotNone(controlled, "aria-controls must reference an existing id")
                self.assertEqual(controlled.tag, "nav")
                self.assertEqual(controlled.attrs.get("id"), "site-nav", "main.js opens #site-nav")
                self.assertEqual(button.text(), TEXTS[lang]["a11y"]["menu"], "button needs a text name")
                # Without JavaScript the button cannot work, so it must start hidden (main.js shows it).
                self.assertIn("hidden", button.attrs)

    def test_ac12_submit_button_keeps_focus_while_sending(self):
        """AC-12 (D-09): the submit button is marked aria-disabled, never disabled, while a message is sent."""
        script = (DIST / "assets" / "js" / "main.js").read_text(encoding="utf-8")
        css = strip_css_comments((DIST / "assets" / "css" / "style.css").read_text(encoding="utf-8"))
        self.assertNotRegex(script, r"\.disabled\b", "a disabled button loses keyboard focus")
        self.assertRegex(script, r"submit\.setAttribute\('aria-disabled', 'true'\)")
        self.assertRegex(script, r"submit\.getAttribute\('aria-disabled'\) === 'true'\)\s*\{\s*return;",
                         "a second submit must be ignored while sending")
        self.assertRegex(script, r"finally\s*\{\s*submit\.removeAttribute\('aria-disabled'\)")
        selectors = [part.strip() for selector, _ in css_rules(css) for part in selector.split(",")]
        self.assertIn('.button[aria-disabled="true"]', selectors, "aria-disabled needs the disabled look")
        for item in self.each_page("contact"):
            with self.subTest(page=item.label):
                _, _, _, _, doc = item
                for button in doc.find_all("button", type="submit"):
                    self.assertNotIn("disabled", button.attrs)

    def test_nfr03_language_switch_name_starts_with_visible_label(self):
        """NFR-03 (WCAG 2.5.3, D-02): each language link is named by its visible label, then the language name."""
        for item in self.each_page():
            with self.subTest(page=item.label):
                _, _, _, _, doc = item
                switch = [nav for nav in doc.find_all("nav") if "lang-switch" in nav.classes()][0]
                links = switch.find_all("a")
                self.assertEqual(len(links), len(SHARED["languages"]))
                for link, language in zip(links, SHARED["languages"]):
                    hidden = [n for n in link.iter() if n.attrs.get("aria-hidden") == "true"]
                    self.assertEqual(hidden, [], f"{language['label']}: visible label hidden from assistive technology")
                    self.assertNotIn("aria-label", link.attrs, "the name must come from the link text")
                    self.assertNotIn("aria-labelledby", link.attrs)
                    self.assertEqual(link.text(), f"{language['label']} {language['name']}")
                    visible = [c for c in link.children if isinstance(c, str) and c.strip()]
                    self.assertEqual([c.strip() for c in visible], [language["label"]],
                                     "only the short label is visible")
                    extra = link.by_class("visually-hidden")
                    self.assertEqual(len(extra), 1)
                    self.assertEqual(extra[0].text(), language["name"])

    def test_ac13_exactly_one_h1_and_heading_order(self):
        """AC-13 / NFR-03: exactly one non-empty h1; heading levels are not skipped."""
        for item in self.each_html():
            with self.subTest(page=item.label):
                _, doc = item
                headings = [n for n in doc.find("body").iter() if re.fullmatch(r"h[1-6]", n.tag)]
                h1 = [n for n in headings if n.tag == "h1"]
                self.assertEqual(len(h1), 1)
                self.assertTrue(h1[0].text())
                self.assertEqual(headings[0].tag, "h1", "h1 must be the first heading")
                previous = 1
                for heading in headings:
                    level = int(heading.tag[1])
                    self.assertLessEqual(level, previous + 1, f"<{heading.tag}> {heading.text()!r} skips a level")
                    self.assertTrue(heading.text(), "empty heading")
                    previous = level

    def test_ac13_landmarks(self):
        """AC-13 / NFR-03: header, nav, main and footer landmarks; h1 inside main; navs are named."""
        for item in self.each_page():
            with self.subTest(page=item.label):
                _, _, _, _, doc = item
                body = doc.find("body")
                for tag in ("header", "main", "footer"):
                    self.assertEqual(len(body.find_all(tag)), 1, f"one <{tag}>")
                navs = body.find_all("nav")
                self.assertGreaterEqual(len(navs), 1)
                labels = [nav.attrs.get("aria-label", "").strip() for nav in navs]
                self.assertTrue(all(labels), "every nav needs aria-label")
                self.assertEqual(len(set(labels)), len(labels), "nav labels must be distinct")
                self.assertIsNotNone(body.find("main").find("h1"), "h1 belongs inside <main>")
        for name in ("index.html", "404.html"):
            with self.subTest(page=name):
                self.assertEqual(len(self.doc(DIST / name).find_all("main")), 1)

    def test_ac13_images_have_alt_and_icons_are_hidden(self):
        """AC-13 / NFR-03: every img has alt text; decorative inline SVG is aria-hidden."""
        images = 0
        for item in self.each_html():
            with self.subTest(page=item.label):
                _, doc = item
                for img in doc.find_all("img"):
                    images += 1
                    self.assertIn("alt", img.attrs, img.attrs.get("src"))
                    if img.attrs.get("aria-hidden") != "true" and img.attrs.get("role") != "presentation":
                        self.assertTrue((img.attrs["alt"] or "").strip(), "meaningful image needs alt text")
                for svg in doc.find_all("svg"):
                    named = svg.attrs.get("aria-label") or svg.find("title")
                    self.assertTrue(svg.attrs.get("aria-hidden") == "true" or named, "unnamed inline SVG")
        self.assertGreater(images, 0)
        for item in self.each_page("home"):
            with self.subTest(page=item.label):
                lang, _, _, _, doc = item
                self.assertEqual(doc.find("main").find("img").attrs.get("alt"), TEXTS[lang]["site"]["monogram_alt"])

    def test_ac13_form_controls_have_labels_and_aria_references_resolve(self):
        """AC-13 / NFR-03: every form control has a label; aria id references point to real elements."""
        controls = 0
        for item in self.each_html():
            with self.subTest(page=item.label):
                _, doc = item
                for control in doc.find_all("input") + doc.find_all("textarea") + doc.find_all("select"):
                    if control.attrs.get("type") in ("hidden", "submit", "button", "reset"):
                        continue
                    controls += 1
                    identifier = control.attrs.get("id")
                    self.assertTrue(identifier, f"control {control.attrs.get('name')} has no id")
                    labels = doc.find_all("label", for_=identifier)
                    wrapped = any(a.tag == "label" for a in control.ancestors())
                    self.assertTrue(len(labels) == 1 or wrapped, f"no label for #{identifier}")
                    for label in labels:
                        self.assertTrue(label.text(), f"empty label for #{identifier}")
                for node in doc.root.iter():
                    for attr in ("aria-labelledby", "aria-describedby", "aria-controls"):
                        for ref in node.attrs.get(attr, "").split():
                            self.assertIsNotNone(doc.by_id(ref), f"{attr}={ref} has no target")
                    if node.tag == "label":
                        self.assertIsNotNone(doc.by_id(node.attrs.get("for", "")), "label without control")
                for button in doc.find_all("button"):
                    self.assertTrue(button.text() or button.attrs.get("aria-label"), "button without a name")
        self.assertGreaterEqual(controls, 4 * len(LANGS))

    def test_nfr03_focus_style_and_reduced_motion(self):
        """AC-12 / NFR-03: focus outline is never removed from controls; motion only when allowed."""
        css = strip_css_comments((DIST / "assets" / "css" / "style.css").read_text(encoding="utf-8"))
        self.assertRegex(css, r":focus-visible\s*\{[^}]*outline\s*:\s*\d+px", "visible focus style")
        for selector, body in re.findall(r"([^{}]+)\{([^{}]*outline\s*:\s*(?:none|0)[^{}]*)\}", css):
            self.assertEqual(selector.strip(), "main:focus",
                             f"outline removed on {selector.strip()!r}")
        self.assertNotIn("!important", css)
        outside = css
        for body in media_blocks(css, r"prefers-reduced-motion\s*:\s*no-preference"):
            outside = outside.replace(body, "")
        self.assertNotRegex(outside, r"(?<![\w-])(animation|transition|scroll-behavior)\s*:",
                            "motion outside @media (prefers-reduced-motion: no-preference)")


# --------------------------------------------------------------- AC-14, NFR-04

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
# 10 to 15 digits, optionally led by + and separated by single spaces, hyphens or brackets.
PHONE = re.compile(r"(?<![\w.#/-])\+?\(?\d(?:[ () -]{0,2}\d){9,14}(?![\w-])")
STUDENT_ID = re.compile(r"\d{2}[A-Z]\d{6}")
CONTACT_SCHEMES = re.compile(r"\b(mailto|tel|sms|callto):", re.I)
XML_NAMESPACE = re.compile(r"http://www\.w3\.org/[\w/.-]+")


class TestPrivacy(SiteTestCase):
    def test_ac14_no_insecure_or_third_party_resources(self):
        """AC-14 / NFR-04: no http:// or // resources and no script, style, image or form on another origin."""
        for path in dist_files():
            with self.subTest(file=rel_path(path)):
                text = XML_NAMESPACE.sub("", path.read_text(encoding="utf-8", errors="replace"))
                self.assertNotIn("http://", text)
                if path.suffix == ".css":
                    css = strip_css_comments(text)
                    self.assertNotIn("@import", css)
                    self.assertNotIn("@font-face", css, "NFR-06: no web font download")
                    for url in re.findall(r"url\(\s*['\"]?([^'\")]+)", css):
                        self.assertFalse(is_external(url) and not url.startswith("data:"), url)
        for item in self.each_html():
            with self.subTest(page=item.label):
                path, doc = item
                for node, attr, value in url_refs(doc):
                    if node.tag == "a":
                        continue  # ordinary links are covered by AC-06
                    self.assertFalse(is_external(value), f"<{node.tag} {attr}=\"{value}\"> leaves the site")
                for node in doc.root.iter():
                    self.assertNotIn("srcset", node.attrs)
                    if node.tag in ("iframe", "object", "embed", "base"):
                        self.fail(f"<{node.tag}> is not allowed")
                    if node.tag == "meta":
                        self.assertNotEqual(node.attrs.get("http-equiv", "").lower(), "refresh")
                        self.assertNotEqual(node.attrs.get("http-equiv", "").lower(), "set-cookie")

    def test_ac14_no_inline_handlers_scripts_or_styles(self):
        """AC-14 / NFR-05: no inline event handlers, inline scripts or inline styles (CSP default-src 'self')."""
        htaccess = (DIST / ".htaccess").read_text(encoding="utf-8")
        self.assertRegex(htaccess, r"Content-Security-Policy \"default-src 'self'")
        self.assertNotIn("unsafe-inline", htaccess)
        for item in self.each_html():
            with self.subTest(page=item.label):
                _, doc = item
                for node in doc.root.iter():
                    handlers = [attr for attr in node.attrs if attr.lower().startswith("on")]
                    self.assertEqual(handlers, [], f"inline handler on <{node.tag}>")
                    self.assertNotIn("style", node.attrs, f"inline style on <{node.tag}>")
                    for attr in ("href", "src", "action"):
                        self.assertFalse(node.attrs.get(attr, "").strip().lower().startswith("javascript:"))
                self.assertEqual(doc.find_all("style"), [], "inline <style>")
                scripts = doc.find_all("script")
                self.assertEqual([s.attrs.get("src") for s in scripts], ["/assets/js/main.js"])
                for script in scripts:
                    self.assertEqual(script.text(), "")
                    self.assertEqual("".join(c for c in script.children if isinstance(c, str)).strip(), "")

    def test_ac14_no_cookies_analytics_or_remote_calls_in_code(self):
        """AC-14 / NFR-04: the script and the form handler set no cookies and call no other host."""
        script = (DIST / "assets" / "js" / "main.js").read_text(encoding="utf-8")
        self.assertNotIn("document.cookie", script)
        for banned in ("cookieStore", "sendBeacon", "XMLHttpRequest", "WebSocket", "EventSource",
                       "importScripts", "eval(", "innerHTML", "document.write", "gtag", "analytics"):
            self.assertNotIn(banned, script)
        self.assertNotRegex(script, r"https?:|['\"]//", "script must not name another host")
        self.assertRegex(script, r"fetch\(\s*form\.action", "the only request goes to the form action")
        self.assertEqual(
            (SRC / "assets" / "js" / "main.js").read_bytes(), (DIST / "assets" / "js" / "main.js").read_bytes()
        )
        php = (DIST / "contact.php").read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", php, flags=re.S)
        for banned in ("setcookie", "setrawcookie", "session_start", "$_COOKIE", "$_SESSION",
                       "mail(", "curl_", "fsockopen", "file_get_contents("):
            self.assertNotIn(banned, code, f"contact.php uses {banned}")

    def test_ac14_privacy_statement_on_each_contact_page(self):
        """AC-14 (FR-08): each contact page has the privacy section with every statement from the content file."""
        for item in self.each_page("contact"):
            with self.subTest(page=item.label):
                lang, _, _, path, doc = item
                section = doc.by_id("privacy")
                self.assertIsNotNone(section, "#privacy section")
                self.assertTrue(any(a.tag == "main" for a in section.ancestors()))
                privacy = TEXTS[lang]["contact"]["privacy"]
                heading = section.find("h2")
                self.assertIsNotNone(heading)
                self.assertEqual(heading.text(), privacy["heading"])
                items = [item.text() for item in section.find_all("li")]
                self.assertEqual(items, [" ".join(item.split()) for item in privacy["items"]])
                self.assertGreaterEqual(len(items), 3, "what is collected, why, and how long")
        for item in self.each_page():
            with self.subTest(page=item.label):
                lang, _, _, path, doc = item
                footer_targets = [resolve(a.attrs["href"], path)
                                  for a in doc.find("footer").find_all("a", href=True)
                                  if not is_external(a.attrs["href"])]
                self.assertIn((DIST / lang / "contact.html", "privacy"), footer_targets,
                              "footer link to the privacy statement")

    def test_ac14_address_hash_statement_matches_the_handler(self):
        """AC-14 (D-08): expired address hashes are pruned on every request, and the statement says so plainly."""
        php = (DIST / "contact.php").read_text(encoding="utf-8")
        request = php_request_code(php)
        prune = request.find("prune_rate_file($dataDir, $now);")
        method = request.find("$method !== 'POST'")
        self.assertGreaterEqual(prune, 0, "contact.php must prune the rate-limit file on every request")
        self.assertGreater(method, prune, "pruning must run before any request is turned away")
        reader = php_function(php, "rate_read")
        self.assertRegex(reader, r"\$now - \$time < RATE_SECONDS", "expired entries are dropped")
        self.assertRegex(reader, r"if \(\$hits === \[\]\) \{[^}]*random_bytes\(",
                         "a fresh salt when no live entry remains")
        pruner = php_function(php, "prune_rate_file")
        self.assertRegex(pruner, r"(?s)rate_read\(.*rate_write\(", "the pruned list must be written back")
        self.assertIn("hash('sha256'", php)
        seconds = php_int_constants(php)["RATE_SECONDS"]
        vague = {"en": ("short time",), "ru": ("недолго", "короткое время"), "kk": ("қысқа уақыт",)}
        for lang in LANGS:
            with self.subTest(lang=lang):
                item = TEXTS[lang]["contact"]["privacy"]["items"][3]
                self.assertIn(str(seconds), re.findall(r"\d+", item), "the statement must name the real period")
                for phrase in vague[lang]:
                    self.assertNotIn(phrase, item.lower())

    def test_ac14_no_private_identifiers_in_dist(self):
        """AC-14 / NFR-04 (R-02): no e-mail address, phone number or student ID anywhere in dist/."""
        for path in dist_files():
            with self.subTest(file=rel_path(path)):
                text = path.read_text(encoding="utf-8", errors="replace")
                self.assertEqual(EMAIL.findall(text), [], "e-mail address")
                self.assertEqual(STUDENT_ID.findall(text), [], "student ID pattern")
                self.assertEqual([m.group(0) for m in PHONE.finditer(text)], [], "phone-number pattern")
                self.assertEqual(CONTACT_SCHEMES.findall(text), [], "mailto:/tel: link")

    def test_ac14_no_private_identifiers_in_content_sources(self):
        """NFR-04 (R-02): the content files themselves hold no e-mail, phone number or student ID."""
        for path in sorted(CONTENT.glob("*.json")):
            with self.subTest(file=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(EMAIL.findall(text), [])
                self.assertEqual(STUDENT_ID.findall(text), [])
                self.assertEqual([m.group(0) for m in PHONE.finditer(text)], [])


# --------------------------------------------------------------- AC-15

class TestNotFound(SiteTestCase):
    def test_ac15_404_page_links_to_each_language_home(self):
        """AC-15 (FR-12): dist/404.html exists and links to the three language home pages."""
        path = DIST / "404.html"
        self.assertTrue(path.is_file())
        doc = self.doc(path)
        self.assertEqual(self.home_links(doc, path), set(LANGS))
        text = doc.find("main").text()
        for lang in LANGS:
            with self.subTest(lang=lang):
                notfound = TEXTS[lang]["notfound"]
                self.assertIn(notfound["heading"], text)
                self.assertIn(notfound["home"], text)
                blocks = [n for n in doc.find("main").iter() if n.attrs.get("lang") == lang]
                self.assertTrue(blocks, f"text in {lang} must be marked with lang")
        robots = doc.find("meta", name="robots")
        self.assertIsNotNone(robots)
        self.assertIn("noindex", robots.attrs.get("content", ""))

    def test_ac15_404_page_uses_root_relative_urls(self):
        """AC-15: the 404 page is served at any depth, so every URL in it must start with '/'."""
        doc = self.doc(DIST / "404.html")
        refs = url_refs(doc)
        self.assertTrue(refs)
        for node, attr, value in refs:
            with self.subTest(url=value):
                self.assertTrue(value.startswith("/") and not value.startswith("//"),
                                f"<{node.tag} {attr}> is not root-relative")

    def test_ac15_htaccess_declares_404_document(self):
        """AC-15: .htaccess declares /404.html as the 404 document."""
        htaccess = (DIST / ".htaccess").read_text(encoding="utf-8")
        match = re.search(r"^\s*ErrorDocument\s+404\s+(\S+)\s*$", htaccess, re.M)
        self.assertIsNotNone(match, "ErrorDocument 404 is not declared")
        self.assertEqual(match.group(1), "/404.html")
        self.assertTrue((DIST / match.group(1).lstrip("/")).is_file())


# --------------------------------------------------------------- NFR-05

SECRET_PATTERNS = {
    "Telegram bot token": r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b",
    "sk- API key": r"\bsk-[A-Za-z0-9_-]{20,}",
    "GitHub token": r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})",
    "AWS access key": r"\bAKIA[0-9A-Z]{16}\b",
    "Google API key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "Slack token": r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    "private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "password assignment": (
        r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token|bot[_-]?token|auth[_-]?token)"
        r"\b[\"']?\s*(?:=|:|=>)\s*[\"']?[A-Za-z0-9_+/.\-]{6,}"
    ),
}
SECRET_FILE_NAMES = re.compile(r"(^\.env($|\.)|\.pem$|\.key$|\.p12$|\.pfx$|^id_rsa|credentials\.json$)")
SCAN_EXCLUDED_DIRS = {".git", "dist", "__pycache__"}


class TestSecurity(SiteTestCase):
    def test_nfr05_data_directory_is_closed(self):
        """NFR-05 (R-05): dist/data/.htaccess denies all web access to stored messages."""
        path = DIST / "data" / ".htaccess"
        self.assertTrue(path.is_file())
        rules = re.sub(r"^\s*#.*$", "", path.read_text(encoding="utf-8"), flags=re.M)
        self.assertRegex(rules, r"(?mi)^\s*Require all denied\s*$")
        self.assertRegex(rules, r"(?mi)^\s*Deny from all\s*$", "Apache 2.2 fallback")
        self.assertNotRegex(rules, r"(?i)Require all granted|Allow from all")
        others = [rel_path(p) for p in (DIST / "data").iterdir() if p.name != ".htaccess"]
        self.assertEqual(others, [], "no data files may be shipped in the build")
        # Defence in depth: the root file also refuses to serve stored JSON.
        root = (DIST / ".htaccess").read_text(encoding="utf-8")
        self.assertRegex(root, r"<FilesMatch \"[^\"]*jsonl[^\"]*\">")
        self.assertRegex(root, r"(?mi)^\s*Options\s+-Indexes\s*$")
        php = (DIST / "contact.php").read_text(encoding="utf-8")
        self.assertIn("__DIR__ . '/data'", php, "messages must be written inside the protected directory")

    def test_nfr05_root_htaccess_forces_https(self):
        """NFR-05: dist/.htaccess redirects plain HTTP to HTTPS with a permanent redirect."""
        self.assertEqual((SRC / "htaccess" / "root.htaccess").read_bytes(), (DIST / ".htaccess").read_bytes())
        rules = re.sub(r"^\s*#.*$", "", (DIST / ".htaccess").read_text(encoding="utf-8"), flags=re.M)
        self.assertRegex(rules, r"(?mi)^\s*RewriteEngine\s+On\s*$")
        self.assertRegex(rules, r"(?mi)^\s*RewriteCond\s+%\{HTTPS\}\s+(!=on|off)\b")
        self.assertRegex(rules, r"(?mi)^\s*RewriteRule\s+\S+\s+https://%\{HTTP_HOST\}\S*\s+\[[^\]]*R=301[^\]]*\]")
        self.assertRegex(rules, r"(?mi)^\s*AddDefaultCharset\s+UTF-8\s*$", "NFR-08")

    def test_nfr05_form_handler_validates_on_the_server(self):
        """NFR-05 (R-05): contact.php is POST-only, checks the honeypot and every limit, escapes output."""
        php = (DIST / "contact.php").read_text(encoding="utf-8")
        self.assertIn("declare(strict_types=1);", php)
        self.assertRegex(php, r"\$method !== 'POST'")
        self.assertRegex(php, r"\$_POST\['" + HONEYPOT_NAME + r"'\]")
        for check in (
            r"text_length\(\$name\) < NAME_MIN", r"text_length\(\$name\) > NAME_MAX",
            r"text_length\(\$contact\) > CONTACT_MAX",
            r"text_length\(\$message\) < MESSAGE_MIN", r"text_length\(\$message\) > MESSAGE_MAX",
        ):
            self.assertRegex(php, check)
        self.assertIn("htmlspecialchars(", php)
        self.assertRegex(php, r"RATE_SECONDS")
        self.assertNotRegex(php, r"\b(eval|exec|system|shell_exec|passthru|unserialize|include|require)\s*\(")
        self.assertNotRegex(php, r"echo\s+\$_(POST|GET|REQUEST|SERVER)")

    def test_nfr05_rate_hit_is_recorded_only_after_a_successful_store(self):
        """NFR-05 (R-05, D-04): a failed store does not block the retry; the message file is capped at 1 MB."""
        php = (DIST / "contact.php").read_text(encoding="utf-8")
        request = php_request_code(php)
        record = "$state['hits'][$key] = $now;"
        self.assertEqual(php.count(record), 1, "exactly one place records a hit")
        store = re.search(r"if \(!store_message\(\$dataDir, \$record\)\) \{[^}]*respond\(500, 'storage_failed'", request)
        self.assertIsNotNone(store, "a failed store answers 500 storage_failed")
        self.assertGreater(request.find(record), store.end(), "the hit must be recorded after store_message()")
        self.assertNotRegex(php_function(php, "rate_read"), r"\$hits\[\$key\]\s*=")
        self.assertEqual(php_int_constants(php).get("MAX_STORE_BYTES"), 1024 * 1024)
        self.assertRegex(php_function(php, "store_message"),
                         r"\$size > MAX_STORE_BYTES\) \{\s*return false;", "refuse when the file is over 1 MB")

    def test_nfr05_cross_site_posts_are_rejected(self):
        """NFR-05 (D-05): a POST whose Origin host differs from the Host header is answered with 400."""
        php = (DIST / "contact.php").read_text(encoding="utf-8")
        check = php_function(php, "cross_site_request")
        self.assertIn("$_SERVER['HTTP_ORIGIN']", check)
        self.assertIn("$_SERVER['HTTP_HOST']", check)
        self.assertIn("PHP_URL_HOST", check)
        self.assertRegex(check, r"if \(\$origin === ''\) \{\s*return false;", "requests without Origin still work")
        request = php_request_code(php)
        match = re.search(r"if \(cross_site_request\(\)\) \{\s*respond\(400, 'invalid_request', \$lang\);", request)
        self.assertIsNotNone(match, "cross-site posts must get 400")
        self.assertLess(match.start(), request.find("store_message("))

    def test_nfr05_php_errors_are_not_displayed(self):
        """NFR-05 (D-06): contact.php switches display_errors off before anything else runs."""
        php = (DIST / "contact.php").read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", php, flags=re.S)
        self.assertRegex(code, r"declare\(strict_types=1\);\s*ini_set\('display_errors', '0'\);")

    def test_nfr05_format_characters_are_stripped_before_measuring(self):
        """NFR-05 (D-07): clean_field removes Unicode format characters, so invisible text cannot pass the limits."""
        php = (DIST / "contact.php").read_text(encoding="utf-8")
        cleaner = php_function(php, "clean_field")
        self.assertRegex(cleaner, r"preg_replace\('/\\p\{Cf\}\+/u', '', \$value\)")
        request = php_request_code(php)
        for field in FIELDS:
            with self.subTest(field=field):
                cleaned = request.find(f"${field} = clean_field(")
                measured = request.find(f"text_length(${field})")
                self.assertTrue(0 <= cleaned < measured, "length is measured on the cleaned value")

    def test_nfr05_no_secrets_in_repository(self):
        """NFR-05 (R-07): no file in the repository (except .git and dist) matches a secret pattern."""
        scanned = 0
        for path in sorted(ROOT.rglob("*")):
            parts = path.relative_to(ROOT).parts
            if not path.is_file() or SCAN_EXCLUDED_DIRS & set(parts[:-1]):
                continue
            scanned += 1
            name = path.relative_to(ROOT).as_posix()
            with self.subTest(file=name):
                self.assertIsNone(SECRET_FILE_NAMES.search(path.name), "file name suggests a secret")
                text = path.read_bytes().decode("utf-8", errors="replace")
                for label, pattern in SECRET_PATTERNS.items():
                    found = [m.group(0)[:12] + "..." for m in re.finditer(pattern, text)]
                    self.assertEqual(found, [], label)
        self.assertGreater(scanned, 10)


# --------------------------------------------------------------- NFR-06

class TestPerformance(SiteTestCase):
    def page_weight(self, path, doc):
        resources = set()
        for link in doc.find_all("link", href=True):
            rel = (link.attrs.get("rel") or "").lower().split()
            if {"stylesheet", "icon", "preload", "modulepreload"} & set(rel):
                resources.add(link.attrs["href"])
        for tag in ("script", "img", "source", "video", "audio"):
            for node in doc.find_all(tag, src=True):
                resources.add(node.attrs["src"])
        files = {path}
        for url in resources:
            self.assertFalse(is_external(url), f"cannot weigh external resource {url}")
            target, _ = resolve(url, path)
            self.assertTrue(target.is_file(), f"missing resource {url}")
            files.add(target)
            if target.suffix == ".css":
                css = strip_css_comments(target.read_text(encoding="utf-8"))
                for nested in re.findall(r"url\(\s*['\"]?([^'\")]+)", css):
                    if not nested.startswith("data:"):
                        files.add(resolve(nested, target)[0])
        return sum(item.stat().st_size for item in files)

    def test_nfr06_page_weight_under_150_kb(self):
        """NFR-06: HTML + CSS + JS + referenced images of each page total under 150 KB."""
        for item in self.each_html():
            with self.subTest(page=item.label):
                path, doc = item
                weight = self.page_weight(path, doc)
                self.assertLess(weight, PAGE_BUDGET_BYTES, f"{weight} bytes")


if __name__ == "__main__":
    unittest.main(verbosity=2)
