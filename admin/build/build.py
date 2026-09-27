#!/usr/bin/env python3
"""Builds diniscruz.ai. Run from anywhere: python3 admin/build/build.py

Two kinds of page live in this tree, and the build treats them differently:

  1. Hand-written pages (index.html, about/, building/, admin/ ...). The HTML is
     authoritative and stays editable by hand. The build only rewrites their nav
     and footer (from site_config.py), fills the <!-- build:* --> blocks, and
     derives their markdown twin from the HTML.

  2. Pages generated from content/ — the essays and research hubs migrated from
     docs.diniscruz.ai. The markdown under content/ is authoritative; each file
     becomes an HTML page at THE SAME PATH it had on docs.diniscruz.ai
     (content/2025/06/07/x.md -> /2025/06/07/x.html), so the old host can redirect
     path-for-path. Its twin is the cleaned source markdown.

Then it writes the surfaces that index the whole site: writing/index.html,
feed.xml (plus the two feed names the old MkDocs site used), sitemap.xml,
robots.txt, llms.txt and llms-full.txt.

Dependencies: python-markdown and PyYAML (see requirements.txt). Output is
deterministic, so CI rebuilds and fails if anything committed is stale.
"""
import datetime as dt
import html
import json
import re
import sys
from email.utils import format_datetime
from pathlib import Path

import markdown
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import html_to_md  # noqa: E402
from site_config import (AUTHOR, BASE, GITHUB, HOST, LICENCE, LINKEDIN, OG_IMAGE, ROBOTS,  # noqa: E402
                         ROOT, SAME_AS, SITE_UPDATED, TAGLINE, VERSION, footer_html, nav_html)

CONTENT = ROOT / "content"
GENERATED_MARK = '<meta name="x-generated-from" content="'
SKIP_DIRS = {".git", ".github", "content", "node_modules"}
FILES_HOST = "https://files.diniscruz.ai"
PERSON_ID = BASE + "about/index.html#person"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def esc(s):
    return html.escape(s, quote=True)


def up_for(rel):
    return "../" * rel.count("/")


def write_if_changed(path, text, changed):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != text:
        path.write_text(text)
        changed.append(path.relative_to(ROOT).as_posix())


def parse_date(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value if isinstance(value, dt.date) else value.date()
    m = re.match(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", str(value or ""))
    return dt.date(int(m[1]), int(m[2]), int(m[3])) if m else None


def plain(md_text):
    """Markdown -> plain text, good enough for descriptions and word counts."""
    t = re.sub(r"```.*?```", " ", md_text, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[*_`#>|]", "", t)
    return " ".join(t.split())


def clip(text, n=190):
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0].rstrip(",;:—-")
    return cut + "…"


# ---------------------------------------------------------------------------
# content/ -> pages
# ---------------------------------------------------------------------------
class Doc:
    def __init__(self, src):
        self.src = src
        self.rel_md = src.relative_to(CONTENT).as_posix()
        self.rel = self.rel_md[:-3] + ".html"
        raw = src.read_text()
        self.meta, self.body = {}, raw
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.S)
        if m:
            self.meta = yaml.safe_load(m[1]) or {}
            self.body = raw[m.end():]
        self.date = parse_date(self.meta.get("date"))
        if not self.date:
            dm = re.match(r"(\d{4})/(\d{2})/(\d{2})/", self.rel)
            self.date = dt.date(int(dm[1]), int(dm[2]), int(dm[3])) if dm else None
        self.is_post = bool(re.match(r"\d{4}/\d{2}/\d{2}/", self.rel))
        self.authors = self.meta.get("authors") or [AUTHOR]
        if isinstance(self.authors, str):
            self.authors = [self.authors]
        self.tags = [str(t) for t in (self.meta.get("tags") or [])]
        self.hub = str(self.meta.get("back_link") or "").strip("/")
        self.title = str(self.meta.get("title") or "").strip()
        body = self.expand_macros(self.body)
        # the docs site put a "_by X, date_" line under every post; the page header
        # carries that now, so drop it from the body
        body = re.sub(r"^[ \t]*_by [^\n]*_[ \t]*\n", "", body, count=1, flags=re.M)
        h1 = re.search(r"^#\s+(.+?)\s*$", body, re.M)
        if not self.title and h1:
            self.title = h1[1].strip()
        # drop a leading H1 that repeats the title; the template renders the H1
        if h1 and plain(h1[1]).strip() == plain(self.title).strip() and not body[:h1.start()].strip(" \n"):
            body = body[:h1.start()] + body[h1.end():]
        elif h1 and not body[:h1.start()].strip(" \n"):
            body = body[:h1.start()] + body[h1.end():]
        # links the deep-research tooling left behind, pointing at local files that
        # never existed on the web: keep the text, drop the link
        body = re.sub(r"\[((?:\\.|\[[^\]]*\]|[^\]\[])*)\]\(file://[^)]*\)", r"\1", body)
        self.md = body.strip() + "\n"
        desc = str(self.meta.get("description") or "").strip()
        if not desc:
            desc = self.first_paragraph()
        self.description = clip(desc or self.title, 200)
        self.words = len(plain(self.md).split())

    # -- macros used by the old MkDocs site (see docs.diniscruz.ai main.py) ------
    def expand_macros(self, text):
        meta = self.meta

        def val(tok):
            tok = tok.strip()
            if not tok:
                return None
            if tok[0] in "'\"":
                return tok[1:-1]
            if re.fullmatch(r"-?\d+", tok):
                return int(tok)
            v = meta.get(tok)
            if tok == "date" and v is not None:
                d = parse_date(v)
                return d.strftime("%Y/%m/%d") if d else str(v)
            return v

        def button(label, url, kind):
            return f'<a class="dbtn dbtn-{kind}" href="{esc(url)}">{label}</a>'

        def call(name, args):
            a = [val(x) for x in re.split(r",(?=(?:[^'\"]|'[^']*'|\"[^\"]*\")*$)", args)] if args.strip() else []
            if name == "download_pdf" and len(a) >= 2 and a[1]:
                return button("PDF", f"{FILES_HOST}/github/pdf/{a[0]}/{a[1]}", "pdf")
            if name == "download_wav" and len(a) >= 2 and a[1]:
                return button("Audio", f"{FILES_HOST}/s3/wav/{a[0]}/{a[1]}", "audio")
            if name == "linkedin_post" and a and a[0]:
                return button("LinkedIn post", f"https://www.linkedin.com/posts/{a[0]}", "linkedin")
            if name == "linkedin_article" and a and a[0]:
                return button("LinkedIn article", a[0], "linkedin")
            if name == "google_slides" and a and a[0]:
                return button("Slides", f"https://docs.google.com/presentation/d/{a[0]}", "slides")
            if name == "back_button":
                return ""  # the breadcrumb does this job now
            if name == "show_youtube" and a and a[0]:
                start = a[1] if len(a) > 1 else 0
                return ("\n\n## Video\n\n<div class=\"embed\"><iframe src=\"https://www.youtube-nocookie.com/embed/"
                        f"{esc(str(a[0]))}?start={start}\" title=\"Video\" loading=\"lazy\" allowfullscreen></iframe></div>\n\n")
            if name == "show_spotify_ui" and a and a[0]:
                return ("\n\n## Podcast\n\n<div class=\"embed embed-audio\"><iframe src=\"https://open.spotify.com/embed/episode/"
                        f"{esc(str(a[0]))}\" title=\"Podcast\" loading=\"lazy\"></iframe></div>\n\n")
            if name in ("show_slides", "view_pdf", "show_infographic") and len(a) >= 2 and a[1]:
                if name == "view_pdf":
                    url, head = f"{FILES_HOST}/github/pdf/{a[0]}/{a[1]}", "PDF"
                elif name == "show_slides":
                    url, head = f"{FILES_HOST}/s3/pdf/{a[0]}/{a[1]}", "Slides"
                else:
                    url, head = f"{FILES_HOST}/s3/pdf/{a[0]}/infographic__{a[1]}", "Infographic"
                return (f"\n\n## {head}\n\n<div class=\"embed embed-pdf\"><iframe src=\"{esc(url)}\" title=\"{head}\" "
                        f"loading=\"lazy\"></iframe></div>\n<p class=\"small\"><a href=\"{esc(url)}\">Open the {head.lower()} in a new tab →</a></p>\n\n")
            return ""

        def sub(m):
            expr = m[1].strip()
            if re.fullmatch(r"authors\s*\|\s*join\((['\"])(.*?)\1\)", expr):
                return " and ".join(self_authors())
            fm = re.fullmatch(r"([a-z_]+)\((.*)\)", expr, re.S)
            if fm:
                return call(fm[1], fm[2])
            if re.fullmatch(r"[a-z_]+", expr):
                v = val(expr)
                return "" if v is None else str(v)
            return ""

        def self_authors():
            au = meta.get("authors") or [AUTHOR]
            return [au] if isinstance(au, str) else [str(x) for x in au]

        text = re.sub(r"\{\{(.*?)\}\}", sub, text, flags=re.S)
        # a line made only of buttons becomes one button row
        text = re.sub(r"^[ \t]*((?:<a class=\"dbtn[^\n]*?</a>[ \t]*)+)$",
                      lambda m: '<p class="dbtns">' + m[1].strip() + "</p>", text, flags=re.M)
        return text

    def first_paragraph(self):
        for block in re.split(r"\n\s*\n", self.md):
            b = block.strip()
            if not b or b[0] in "#<|>-*!`" or b.startswith("---") or re.match(r"\d+\.", b):
                continue
            text = plain(b)
            if len(text) > 60:
                return text
        return ""

    @property
    def buttons(self):
        m = re.search(r'<p class="dbtns">(.*?)</p>', self.md, re.S)
        return m[1] if m else ""


MD_EXT = ["extra", "sane_lists", "admonition", "toc"]
MD_CFG = {"toc": {"permalink": False, "toc_depth": "2-3"}}


def render_markdown(doc):
    body = re.sub(r'<p class="dbtns">.*?</p>\s*', "", doc.md, count=1, flags=re.S)
    md = markdown.Markdown(extensions=MD_EXT, extension_configs=MD_CFG)
    out = md.convert(body)
    # the page template owns the only <h1>; any H1 left in a migrated body becomes an H2
    out = re.sub(r"<(/?)h1([ >])", r"<\1h2\2", out)
    toc = md.toc_tokens
    # mermaid fences -> <pre class="mermaid">
    has_mermaid = "language-mermaid" in out
    out = re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>',
                 lambda m: '<pre class="mermaid">' + m[1] + "</pre>", out, flags=re.S)
    out = re.sub(r"<table>", '<div class="tablewrap"><table>', out)
    out = out.replace("</table>", "</table></div>")
    out = rewrite_links(out, doc.rel)
    return out, toc, has_mermaid


def rewrite_links(out, rel):
    up = up_for(rel)
    pages = content_index()

    def fix(m):
        attr, href = m[1], m[2]
        if re.match(r"^([a-z][a-z0-9+.-]*:|//|#)", href):
            return m[0]
        path, _, frag = href.partition("#")
        if path.startswith("/"):
            path = path.lstrip("/")
            if path in ("", "index", "index.html"):
                path = "index.html"
            target = path
        else:
            base = Path(rel).parent
            target = (base / path).as_posix()
            target = norm(target)
        if target.endswith(".md"):
            target = target[:-3] + ".html"
        elif not re.search(r"\.[a-z0-9]{2,5}$", target):
            target = target + ".html"
        target = resolve_fuzzy(target, pages)
        new = up + target + ("#" + frag if frag else "")
        return f'{attr}="{new}"'

    return re.sub(r'(href|src)="([^"]*)"', fix, out)


def norm(p):
    parts = []
    for seg in p.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
        else:
            parts.append(seg)
    return "/".join(parts)


_INDEX = None


def content_index():
    global _INDEX
    if _INDEX is None:
        _INDEX = {p.relative_to(CONTENT).as_posix()[:-3] + ".html" for p in CONTENT.rglob("*.md")}
        _INDEX |= {"index.html", "about.html"}
    return _INDEX


def resolve_fuzzy(target, pages):
    """A handful of old links differ from their target only in dash/underscore
    style (e.g. an em dash where the file has an en dash). Resolve those to the
    real file instead of shipping a broken link."""
    if target in pages or not target.endswith(".html"):
        return target
    key = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    k = key(target)
    for p in pages:
        if key(p) == k:
            return p
    return target


HUBS = {}  # "research/graphs" -> title, filled once the research docs are loaded


def crumb_parts(doc):
    """The breadcrumb trail as (label, rel) pairs. It is rendered visibly AND as
    BreadcrumbList structured data, so the two always match."""
    parts = [("diniscruz.ai", "index.html")]
    if doc.is_post:
        parts.append(("writing", "writing/index.html"))
        if doc.hub in HUBS:
            parts.append((HUBS[doc.hub], doc.hub + ".html"))
    elif doc.rel.startswith("research/") and doc.rel != "research/index.html":
        parts.append(("research", "research/index.html"))
    elif re.match(r"\d{4}/\d{2}/index.html", doc.rel):
        parts.append(("writing", "writing/index.html"))
    return parts


def crumb_html(doc):
    up = up_for(doc.rel)
    return '<div class="crumb">' + " / ".join(
        f'<a href="{up}{r}">{esc(label)}</a>' for label, r in crumb_parts(doc)) + "</div>"


def breadcrumb_ld(doc):
    items = crumb_parts(doc) + [(doc.title, doc.rel)]
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": label if i else "diniscruz.ai",
         "item": BASE if r == "index.html" else BASE + r} for i, (label, r) in enumerate(items)]}


def canonical_url(rel):
    return BASE if rel == "index.html" else BASE + rel


def toc_html(toc):
    items = [t for t in toc if t["level"] == 2]
    if len(items) < 4:
        return ""
    lis = "".join(f'<li><a href="#{esc(t["id"])}">{t["name"]}</a></li>' for t in items)
    return f'<details class="toc"><summary>Contents · {len(items)} sections</summary><ol>{lis}</ol></details>'


def head_html(rel, title, description, og_type="website", jsonld=None, extra="", generated_from=None,
              published=None):
    up = up_for(rel)
    url = canonical_url(rel)
    blocks = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        f"<title>{esc(title)}</title>",
        f'<meta name="description" content="{esc(description)}">',
        f'<meta name="author" content="{AUTHOR}">',
        f'<meta name="robots" content="{ROBOTS}">',
        f'<link rel="canonical" href="{url}">',
        f'<meta property="og:type" content="{og_type}">',
        '<meta property="og:site_name" content="diniscruz.ai">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        f'<meta property="og:image" content="{OG_IMAGE}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="Dinis Cruz — diniscruz.ai">',
        '<meta property="og:locale" content="en_GB">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:image" content="{OG_IMAGE}">',
    ]
    if published:
        blocks.append(f'<meta property="article:published_time" content="{published.isoformat()}">')
        blocks.append(f'<meta property="article:author" content="{LINKEDIN}">')
    if generated_from:
        blocks.append(f'{GENERATED_MARK}{esc(generated_from)}">')
    blocks += [
        f'<link rel="alternate" type="text/markdown" href="{Path(rel).name[:-5]}.md" title="This page as markdown">',
        f'<link rel="alternate" type="application/rss+xml" title="Dinis Cruz — writing" href="{up}feed.xml">',
        f'<link rel="icon" href="{up}assets/favicon.svg" type="image/svg+xml">',
        f'<link rel="stylesheet" href="{up}assets/site.css">',
    ]
    if isinstance(jsonld, list):
        jsonld = {"@context": "https://schema.org", "@graph": jsonld}
    if jsonld:
        blocks.append('<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False) + "</script>")
    if extra:
        blocks.append(extra)
    blocks.append("</head>")
    return "\n".join(blocks)


def author_ld(names):
    out, extra = [], []
    for n in names:
        if n.strip().lower() == AUTHOR.lower():
            out.append({"@type": "Person", "@id": PERSON_ID, "name": AUTHOR, "url": BASE + "about/index.html",
                        "sameAs": SAME_AS})
        else:
            extra.append({"@type": "Thing", "name": n})
    if not out:
        out.append({"@type": "Person", "@id": PERSON_ID, "name": AUTHOR})
    return out, extra


RELATED = {}  # hub -> posts in that hub, newest first
DOC_DATES = {}  # post rel -> date


def related_html(doc):
    peers = [d for d in RELATED.get(doc.hub, []) if d is not doc]
    if not peers:
        return ""
    # nearest in time first: the reading list a reader of this piece most likely wants
    peers = sorted(peers, key=lambda d: abs((d.date - doc.date).days))[:5]
    up = up_for(doc.rel)
    lis = "".join(f'<li><a href="{up}{d.rel}">{esc(d.title)}</a> <span class="dim small">'
                  f'{d.date.strftime("%b %Y")}</span></li>' for d in peers)
    return (f'<aside class="related"><h2>More on {esc(HUBS[doc.hub])}</h2><ul>{lis}</ul>'
            f'<p class="small"><a href="{up}{doc.hub}.html">The full {esc(HUBS[doc.hub])} reading list →</a></p></aside>')


def render_doc(doc, prev_doc=None, next_doc=None):
    rel, up = doc.rel, up_for(doc.rel)
    body, toc, has_mermaid = render_markdown(doc)
    title = doc.title or "Untitled"
    full_title = f"{title} — Dinis Cruz"
    jsonld = [breadcrumb_ld(doc)]
    meta_line = ""
    if not doc.is_post:
        linked = re.findall(r'href="((?:\.\./)*\d{4}/\d{2}/\d{2}/[^"#]+\.html)"', body)
        seen = []
        for h in linked:
            r = norm((Path(rel).parent / h).as_posix())
            if r not in seen:
                seen.append(r)
        dates = [DOC_DATES[r] for r in seen if r in DOC_DATES]
        doc.linked_newest = max(dates) if dates else None
        jsonld.append({"@type": "CollectionPage", "@id": BASE + rel, "name": title, "url": BASE + rel,
                       "description": doc.description, "author": {"@id": PERSON_ID},
                       "isPartOf": {"@id": BASE + "#website"},
                       "mainEntity": {"@type": "ItemList", "numberOfItems": len(seen), "itemListElement": [
                           {"@type": "ListItem", "position": i + 1, "url": BASE + r} for i, r in enumerate(seen)]}})
    if doc.is_post:
        authors, contributors = author_ld(doc.authors)
        post = {
            "@type": "BlogPosting", "@id": BASE + rel,
            "headline": title[:110], "name": title, "description": doc.description,
            "datePublished": doc.date.isoformat(), "dateModified": doc.date.isoformat(),
            "image": OG_IMAGE, "author": authors,
            "publisher": {"@type": "Person", "@id": PERSON_ID, "name": AUTHOR},
            "url": BASE + rel, "mainEntityOfPage": BASE + rel, "inLanguage": "en",
            "license": "https://creativecommons.org/licenses/by/4.0/", "wordCount": doc.words,
            "isPartOf": {"@id": BASE + "#website"},
        }
        if doc.hub in HUBS:
            post["articleSection"] = HUBS[doc.hub]
        if contributors:
            post["contributor"] = contributors
        if doc.tags:
            post["keywords"] = ", ".join(doc.tags)
        if doc.meta.get("pdf_file"):
            post["encoding"] = {"@type": "MediaObject", "encodingFormat": "application/pdf",
                                "contentUrl": f"{FILES_HOST}/github/pdf/{doc.date.strftime('%Y/%m/%d')}/{doc.meta['pdf_file']}"}
        jsonld.append(post)
        minutes = max(1, round(doc.words / 230))
        by = " and ".join(esc(a) for a in doc.authors)
        meta_line = (f'<p class="docline">By <b>{by}</b> · <time datetime="{doc.date.isoformat()}">'
                     f'{doc.date.strftime("%-d %B %Y")}</time> · {minutes} min read</p>')
    extra = ""
    if has_mermaid:
        extra = ('<script type="module">import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";'
                 'mermaid.initialize({startOnLoad:true,theme:"neutral"});</script>')
    head = head_html(rel, full_title, doc.description, "article" if doc.is_post else "website", jsonld,
                     extra, generated_from="content/" + doc.rel_md, published=doc.date if doc.is_post else None)
    tags = ""
    if doc.tags:
        tags = '<p class="tags">' + "".join(f'<span class="tagpill">{esc(t)}</span>' for t in doc.tags) + "</p>"
    buttons = f'<p class="dbtns">{rewrite_links(doc.buttons, rel)}</p>' if doc.buttons else ""
    pagenav = ""
    if doc.is_post and (prev_doc or next_doc):
        left = (f'<a href="{up}{prev_doc.rel}">← {esc(prev_doc.title)}</a>' if prev_doc else "<span></span>")
        right = (f'<a href="{up}{next_doc.rel}">{esc(next_doc.title)} →</a>' if next_doc else "<span></span>")
        pagenav = f'<div class="pagenav">{left}{right}</div>'
    lead_note = ""
    if doc.is_post:
        lead_note = (f'<p class="small dim licence-note">Released under <a href="https://creativecommons.org/licenses/by/4.0/">'
                     f'CC BY 4.0</a>. First published on docs.diniscruz.ai; '
                     f'<a href="{Path(rel).name[:-5]}.md">this page as markdown</a>.</p>')
    main = "\n".join(x for x in [
        f'<main class="doc essay">',
        crumb_html(doc),
        f"<h1>{esc(title)}</h1>",
        meta_line, buttons, tags, toc_html(toc),
        '<article class="prose">', body, "</article>",
        related_html(doc) if doc.is_post else "", lead_note, pagenav,
        "</main>",
    ] if x)
    page = "\n".join([head, "<body>", "", nav_html(rel, up), "", main, "", footer_html(rel, up), "", "</body>", "</html>", ""])
    return page


def twin_for_doc(doc):
    md = re.sub(r'<p class="dbtns">(.*?)</p>',
                lambda m: " · ".join(f"[{t}]({h})" for h, t in re.findall(r'href="([^"]+)">([^<]+)</a>', m[1])),
                doc.md, flags=re.S)
    md = re.sub(r"\]\(([^)#\s]+)\.md(#[^)]*)?\)", lambda m: f"]({m[1]}.md{m[2] or ''})", md)
    head = [
        f"<!-- generated from content/{doc.rel_md} by admin/build/build.py — do not edit by hand -->",
        f"*[diniscruz.ai](/index.md) · site {VERSION} · canonical: {BASE}{doc.rel}*",
        f"# {doc.title}",
    ]
    if doc.is_post:
        head.append(f"*By {' and '.join(doc.authors)} · {doc.date.isoformat()}*")
    head.append(f"> {doc.description}")
    return "\n\n".join(head) + "\n\n---\n\n" + md.strip() + "\n\n---\n\n*" + LICENCE + "*\n"


# ---------------------------------------------------------------------------
# hand-written pages
# ---------------------------------------------------------------------------
def apply_chrome(text, rel):
    # 404.html is served at whatever path was missing, so its links must be root-absolute
    up = "/" if rel == "404.html" else up_for(rel)
    text, n1 = re.subn(r'<nav class="site">.*?</nav>', lambda _: nav_html(rel, up), text, count=1, flags=re.S)
    text, n2 = re.subn(r'<footer class="site">.*?</footer>', lambda _: footer_html(rel, up), text, count=1, flags=re.S)
    return text, bool(n1 and n2)


SEO_TAGS = re.compile(r'\n<meta (?:name="robots"|property="og:image[^"]*"|property="og:locale"|name="twitter:[^"]*")[^>]*>')


def apply_head_seo(text, rel):
    """The same robots, image and card tags on every hand-written page as on the
    generated ones: strip whatever is there, write the current set after og:description."""
    noindex = 'content="noindex' in text
    text = SEO_TAGS.sub("", text)
    tags = [] if noindex else [f'<meta name="robots" content="{ROBOTS}">']
    tags += [f'<meta property="og:image" content="{OG_IMAGE}">',
             '<meta property="og:image:width" content="1200">',
             '<meta property="og:image:height" content="630">',
             '<meta property="og:image:alt" content="Dinis Cruz — diniscruz.ai">',
             '<meta property="og:locale" content="en_GB">',
             '<meta name="twitter:card" content="summary_large_image">',
             f'<meta name="twitter:image" content="{OG_IMAGE}">']
    if noindex:
        tags.insert(0, '<meta name="robots" content="noindex">')
    return re.sub(r'(<meta property="og:description"[^>]*>)', lambda m: m[1] + "\n" + "\n".join(tags),
                  text, count=1)


def fill_block(text, name, content):
    return re.sub(rf"(<!-- build:{name} -->).*?(<!-- /build:{name} -->)",
                  lambda m: m[1] + "\n" + content + "\n" + m[2], text, flags=re.S)


def post_cards(posts, up, n=6):
    cards = []
    for d in posts[:n]:
        cards.append(f'    <a class="card" href="{up}{d.rel}"><span class="tag">{d.date.strftime("%-d %b %Y")}</span>'
                     f"<h3>{esc(d.title)}</h3><p>{esc(clip(d.description, 170))}</p></a>")
    return '  <div class="cards">\n' + "\n".join(cards) + "\n  </div>"


def writing_index(posts):
    rel = "writing/index.html"
    up = up_for(rel)
    by_month = {}
    for d in posts:
        by_month.setdefault((d.date.year, d.date.month), []).append(d)
    years = sorted({y for y, _ in by_month}, reverse=True)
    sections = []
    jump = " · ".join(f'<a href="#y{y}">{y}</a>' for y in years)
    for (y, m) in sorted(by_month, reverse=True):
        items = by_month[(y, m)]
        month_name = dt.date(y, m, 1).strftime("%B %Y")
        hub = f"{y}/{m:02d}/index.html"
        hub_link = (f' <a class="small" href="{up}{hub}">month overview →</a>'
                    if (CONTENT / f"{y}/{m:02d}/index.md").exists() else "")
        lis = "\n".join(
            f'  <li><time datetime="{d.date.isoformat()}">{d.date.strftime("%d %b")}</time> '
            f'<a href="{up}{d.rel}">{esc(d.title)}</a><span class="ldesc">{esc(clip(d.description, 160))}</span></li>'
            for d in items)
        anchor = f' id="y{y}"' if (y, m) == max(k for k in by_month if k[0] == y) else ""
        sections.append(f'<h2{anchor}>{month_name} <span class="count">{len(items)}</span>{hub_link}</h2>\n'
                        f'<ul class="postlist">\n{lis}\n</ul>')
    desc = (f"Every essay, research brief and project proposal by Dinis Cruz, newest first — {len(posts)} pieces on AI, "
            "cyber security, semantic knowledge graphs, the future of news and Europe.")
    jsonld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Writing — Dinis Cruz",
              "url": BASE + rel, "description": desc, "author": {"@id": PERSON_ID},
              "hasPart": [{"@type": "BlogPosting", "headline": d.title, "url": BASE + d.rel,
                           "datePublished": d.date.isoformat()} for d in posts[:30]]}
    main = f"""<main class="doc wide">
<div class="crumb"><a href="{up}index.html">diniscruz.ai</a> / writing</div>
<h1>Writing</h1>
<p class="lead">{esc(desc)} Browse by topic in the <a href="{up}research/index.html">research hub</a>, see the
<a href="{up}research/research-document.html">catalogue with tags</a>, or subscribe to the <a href="{up}feed.xml">RSS feed</a>.</p>
<p class="small dim">Jump to: {jump}</p>
{chr(10).join(sections)}
</main>"""
    head = head_html(rel, "Writing — Dinis Cruz", desc, "website", jsonld, generated_from="content/ (index)")
    return "\n".join([head, "<body>", "", nav_html(rel, up), "", main, "", footer_html(rel, up), "", "</body>", "</html>", ""])


def writing_twin(posts):
    lines = [
        "<!-- generated by admin/build/build.py — do not edit by hand -->",
        f"*[diniscruz.ai](/index.md) · site {VERSION} · canonical: {BASE}writing/index.html*",
        "# Writing",
        f"> Every essay, research brief and project proposal by Dinis Cruz, newest first — {len(posts)} pieces.",
        "---",
    ]
    cur = None
    for d in posts:
        key = d.date.strftime("%B %Y")
        if key != cur:
            lines.append(f"## {key}")
            cur = key
        lines.append(f"- {d.date.isoformat()} — [{d.title}](../{d.rel[:-5]}.md): {d.description}")
    return "\n\n".join(lines) + "\n\n---\n\n*" + LICENCE + "*\n"


def rss(posts):
    items = []
    for d in posts[:60]:
        when = dt.datetime.combine(d.date, dt.time(9, 0), tzinfo=dt.timezone.utc)
        cats = "".join(f"<category>{esc(t)}</category>" for t in d.tags)
        items.append(f"""  <item>
    <title>{esc(d.title)}</title>
    <link>{BASE}{d.rel}</link>
    <guid isPermaLink="true">{BASE}{d.rel}</guid>
    <pubDate>{format_datetime(when)}</pubDate>
    <author>noreply@{HOST} ({AUTHOR})</author>{cats}
    <description>{esc(d.description)}</description>
  </item>""")
    last = format_datetime(dt.datetime.combine(posts[0].date, dt.time(9, 0), tzinfo=dt.timezone.utc))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>Dinis Cruz — writing</title>
  <link>{BASE}</link>
  <atom:link href="{BASE}feed.xml" rel="self" type="application/rss+xml"/>
  <description>Essays and research by Dinis Cruz on AI, cyber security, semantic knowledge graphs and the future of news.</description>
  <language>en</language>
  <lastBuildDate>{last}</lastBuildDate>
{chr(10).join(items)}
</channel>
</rss>
"""


def sitemap(pages, docs_by_rel, posts):
    newest = posts[0].date.isoformat()
    urls = []
    for rel in pages:
        d = docs_by_rel.get(rel)
        if d and d.is_post:
            when = d.date.isoformat()
        elif d and getattr(d, "linked_newest", None):
            when = d.linked_newest.isoformat()
        elif d and d.date:
            when = d.date.isoformat()
        elif rel in ("writing/index.html", "research/index.html", "research/research-document.html"):
            when = newest
        else:
            when = max(SITE_UPDATED, newest)
        lastmod = f"<lastmod>{when}</lastmod>"
        loc = canonical_url(rel)
        urls.append(f"  <url><loc>{loc}</loc>{lastmod}</url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")


ROBOTS_TXT = f"""# diniscruz.ai — every crawler is welcome, AI agents included.
User-agent: *
Allow: /

# Search engines index the HTML pages. The markdown twin of each page (*.md) and
# llms-full.txt repeat that HTML for agents that read markdown, so the search
# crawlers skip them rather than index every page twice. They are still served
# to everyone else, and listed in llms.txt.
User-agent: Googlebot
User-agent: Bingbot
Disallow: /*.md$
Disallow: /llms-full.txt
Allow: /

Sitemap: {BASE}sitemap.xml
"""


def is_stub(text):
    return 'http-equiv="refresh"' in text


# ---------------------------------------------------------------------------
# llms.txt / llms-full.txt
# ---------------------------------------------------------------------------
def llms_txt(entries, posts):
    lines = [
        "# diniscruz.ai",
        "",
        "> The personal site of Dinis Cruz: essays and research on AI, cyber security, semantic",
        "> knowledge graphs, the future of news and Europe, and the companies and open-source",
        "> projects that work feeds into.",
        "",
        f"Site version: {VERSION}",
        f"Canonical host: {BASE}",
        f"Author: {AUTHOR} — {LINKEDIN} — {GITHUB}",
        f"{TAGLINE}",
        "All writing CC BY 4.0 unless noted. Code under the repository licence (Apache-2.0).",
        "",
        "## How to read this site as an agent",
        "",
        "Every page has a markdown twin at the same path with the extension swapped:",
        f"{BASE}about/index.html is also {BASE}about/index.md, and the links inside the",
        "markdown point at markdown. If your fetcher cannot follow links, take",
        f"{BASE}llms-full.txt: every page on this site in one file.",
        "",
        "This site replaces docs.diniscruz.ai. Every essay keeps the path it had there:",
        "https://docs.diniscruz.ai/2025/06/07/x.html is now https://diniscruz.ai/2025/06/07/x.html.",
        "",
        "## Who Dinis Cruz is, stated so you do not have to fetch anything",
        "",
        "- Founder of sgit.ai (encrypted vaults with git semantics, Apache-2.0) and sgraph.ai (its commercial home: SG/Send and hosted SG/Vaults).",
        "- Founder of MyFeeds.ai (role-aware cybersecurity briefings on semantic knowledge graphs), The Cyber Boardroom, RiskMandate.ai (the business risk layer for autonomous systems) and VoiceDebrief.ai (voice to debriefs, entirely in the browser).",
        "- Former OWASP Board member; organiser of the OWASP Summits (Lisbon 2011, Woburn 2017); creator of the OWASP O2 Platform (2010-2012).",
        "- Open-source author of the osbot-* and mgraph-* families, memory_fs, Issues-FS and sgit-ai, all Apache-2.0 on PyPI.",
        "- Based in the UK for thirty years: security practitioner, CISO for UK companies, founder.",
        "",
        "## Pages",
        "",
    ]
    for rel, title, desc in entries:
        if re.match(r"\d{4}/\d{2}/\d{2}/", rel):
            continue
        lines.append(f"- [{title}]({BASE}{rel[:-5]}.md): {desc}")
    lines += ["", "## Start here, by topic", ""]
    for hub, title in sorted(HUBS.items()):
        if hub in RELATED:
            lines.append(f"- [{title}]({BASE}{hub}.md): {len(RELATED[hub])} pieces, newest "
                         f"{RELATED[hub][0].date.isoformat()}.")
    lines += ["", f"## Writing ({len(posts)} pieces, newest first)", ""]
    for d in posts:
        lines.append(f"- [{d.title}]({BASE}{d.rel[:-5]}.md): {d.date.isoformat()}. {d.description}")
    return "\n".join(lines) + "\n"


def llms_full(entries, twins):
    parts = [
        "# diniscruz.ai — every page, one file",
        "",
        f"Site version: {VERSION}. Generated by admin/build/build.py.",
        f"Canonical host: {BASE} — every section below is one page of the site.",
        "All writing CC BY 4.0 unless noted.",
        "",
    ]
    for rel, _, _ in entries:
        parts += ["=" * 78, f"PAGE: /{rel}  (markdown twin: /{rel[:-5]}.md)", "=" * 78, "", twins[rel], ""]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
def main():
    changed = []
    docs = [Doc(p) for p in sorted(CONTENT.rglob("*.md"))]
    for d in docs:
        if d.rel.startswith("research/"):
            HUBS[d.rel[:-5]] = d.title
    posts = sorted([d for d in docs if d.is_post], key=lambda d: (d.date, d.rel), reverse=True)
    for d in posts:
        DOC_DATES[d.rel] = d.date
        if d.hub in HUBS:
            RELATED.setdefault(d.hub, []).append(d)
    docs_by_rel = {d.rel: d for d in docs}

    # 1. content/ -> pages
    twins = {}
    for i, d in enumerate(posts):
        nxt = posts[i - 1] if i > 0 else None
        prv = posts[i + 1] if i + 1 < len(posts) else None
        write_if_changed(ROOT / d.rel, render_doc(d, prv, nxt), changed)
    for d in docs:
        if not d.is_post:
            write_if_changed(ROOT / d.rel, render_doc(d), changed)
    for d in docs:
        twins[d.rel] = twin_for_doc(d)
        write_if_changed(ROOT / (d.rel[:-5] + ".md"), twins[d.rel], changed)

    # 2. generated index pages
    write_if_changed(ROOT / "writing/index.html", writing_index(posts), changed)
    twins["writing/index.html"] = writing_twin(posts)
    write_if_changed(ROOT / "writing/index.md", twins["writing/index.html"], changed)

    # 3. hand-written pages: chrome, build blocks, twins
    all_html = sorted(p for p in ROOT.rglob("*.html") if not (set(p.relative_to(ROOT).parts) & SKIP_DIRS))
    for p in all_html:
        rel = p.relative_to(ROOT).as_posix()
        text = p.read_text()
        if GENERATED_MARK in text:
            continue
        if not is_stub(text):
            new, ok = apply_chrome(apply_head_seo(text, rel), rel)
            if not ok:
                print(f"  ! {rel}: missing nav or footer block", file=sys.stderr)
        else:
            new = text
        up = up_for(rel)
        new = fill_block(new, "latest", post_cards(posts, up))
        new = fill_block(new, "count", str(len(posts)))
        new = fill_block(new, "first-year", str(min(d.date.year for d in posts)))
        write_if_changed(p, new, changed)
        if is_stub(new):
            continue
        tree = html_to_md.Tree()
        tree.feed(new)
        out = []
        html_to_md.render(tree.root, rel, out)
        body = re.sub(r"\n{3,}", "\n\n", "\n\n".join(b for b in out if b.strip()))
        head = [f"<!-- generated from {rel} by admin/build/build.py — do not edit by hand -->",
                f"*[diniscruz.ai](/index.md) · site {VERSION} · canonical: {BASE}{rel}*"]
        desc = html_to_md.page_description(new)
        if desc:
            head.append(f"> {desc}")
        twins[rel] = "\n\n".join(head) + "\n\n---\n\n" + body + "\n\n---\n\n*" + LICENCE + "*\n"
        write_if_changed(p.with_suffix(".md"), twins[rel], changed)

    # 4. the site-wide surfaces
    pages = []
    for p in sorted(ROOT.rglob("*.html")):
        rel = p.relative_to(ROOT).as_posix()
        if set(p.relative_to(ROOT).parts) & SKIP_DIRS or rel == "404.html":
            continue
        if is_stub(p.read_text()):
            continue
        pages.append(rel)
    order = {"index.html": 0, "about/index.html": 1, "building/index.html": 2, "writing/index.html": 3,
             "research/index.html": 4}
    pages.sort(key=lambda r: (order.get(r, 10), 1 if docs_by_rel.get(r) and docs_by_rel[r].is_post else 0,
                              "" if not docs_by_rel.get(r) or not docs_by_rel[r].is_post else
                              str(10**8 - int(docs_by_rel[r].date.strftime("%Y%m%d"))), r))
    entries = []
    for rel in pages:
        src = (ROOT / rel).read_text()
        entries.append((rel, html_to_md.page_title(src), html_to_md.page_description(src)))
    write_if_changed(ROOT / "sitemap.xml", sitemap(pages, docs_by_rel, posts), changed)
    feed = rss(posts)
    for name in ("feed.xml", "feed_rss_created.xml", "feed_rss_updated.xml"):
        write_if_changed(ROOT / name, feed, changed)
    write_if_changed(ROOT / "robots.txt", ROBOTS_TXT, changed)
    write_if_changed(ROOT / "llms.txt", llms_txt(entries, posts), changed)
    write_if_changed(ROOT / "llms-full.txt", llms_full(entries, twins), changed)

    print(f"build: {VERSION} — {len(docs)} content page(s) ({len(posts)} posts), {len(pages)} indexed page(s); "
          f"{len(changed)} file(s) updated")
    for c in changed[:40]:
        print(f"  · {c}")
    if len(changed) > 40:
        print(f"  · … and {len(changed) - 40} more")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.stdout = None
