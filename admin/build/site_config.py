"""The single definition of diniscruz.ai's identity, nav and footer.

Every other build script imports from here, so the nav, the footer, the version
badge and the author record cannot drift between the hand-written pages and the
pages generated from content/.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = (ROOT / "admin/build/version.txt").read_text().strip()
HOST = (ROOT / "CNAME").read_text().strip()
BASE = f"https://{HOST}/"
GH = "https://github.com/DinisCruz/DinisCruz-AI__Website"
LICENCE = ("This page is released under the Creative Commons Attribution 4.0 "
           "International licence (CC BY 4.0).")

AUTHOR = "Dinis Cruz"
LINKEDIN = "https://www.linkedin.com/in/diniscruz"
GITHUB = "https://github.com/DinisCruz"
SAME_AS = [
    LINKEDIN,
    GITHUB,
    "https://sgit.ai/about/index.html",
    "https://open-source.sgit.ai/about/index.html",
    "https://docs.diniscruz.ai/",
]
TAGLINE = ("Founder of sgit.ai, sgraph.ai, MyFeeds.ai, The Cyber Boardroom, RiskMandate.ai "
           "and VoiceDebrief.ai; former OWASP Board member; creator of the O2 Platform.")

# The nav, two levels: (label, own page, [(sub-label, href), ...], (path prefixes)).
# A group label is always a link to a real page, so nothing is reachable only by
# opening a dropdown; `prefixes` decides the "here" state.
NAV = [
    ("Writing", "writing/index.html", [
        ("All writing, newest first", "writing/index.html"),
        ("Research document catalogue", "research/research-document.html"),
        ("Talks &amp; presentations", "resources/presentations.html"),
        ("RSS feed", "feed.xml"),
    ], ("writing/", "2024/", "2025/", "2026/", "resources/")),
    ("Research", "research/index.html", [
        ("Research hub", "research/index.html"),
        ("Cyber-security &amp; threat modeling", "research/cyber-security.html"),
        ("AI &amp; development", "research/development-and-genai.html"),
        ("Knowledge graphs", "research/graphs.html"),
        ("The future of news", "research/the-future-of-news.html"),
        ("Europe &amp; learning", "research/europe-and-learning.html"),
        ("Projects &amp; innovation lab", "research/projects.html"),
        ("Organisational transformation", "research/organizational-transformation.html"),
    ], ("research/",)),
    ("Building", "building/index.html", [
        ("Companies", "building/index.html#companies"),
        ("Open source", "building/index.html#open-source"),
        ("The sgit.ai network", "building/index.html#network"),
    ], ("building/",)),
    ("About", "about/index.html", [
        ("About Dinis Cruz", "about/index.html"),
        ("How this site is built", "admin/index.html"),
        ("Moving from docs.diniscruz.ai", "admin/migration.html"),
        ("Release history", "admin/versions.html"),
    ], ("about/", "admin/")),
]

FOOTER = [
    ("Writing", [
        ("All writing", "writing/index.html"),
        ("Research hub", "research/index.html"),
        ("Talks", "resources/presentations.html"),
        ("RSS feed", "feed.xml"),
    ]),
    ("Building", [
        ("Companies", "building/index.html#companies"),
        ("Open source", "building/index.html#open-source"),
        ("↗ sgit.ai", "https://sgit.ai"),
        ("↗ open-source.sgit.ai", "https://open-source.sgit.ai"),
    ]),
    ("About", [
        ("About Dinis Cruz", "about/index.html"),
        ("↗ LinkedIn", LINKEDIN),
        ("↗ GitHub", GITHUB),
        ("How this site is built", "admin/index.html"),
        ("Release history", "admin/versions.html"),
        ("llms.txt", "llms.txt"),
        ("llms-full.txt", "llms-full.txt"),
    ]),
]

BLURB = ("The personal site of Dinis Cruz: essays and research on AI, cyber security, "
         "semantic knowledge graphs and the future of news, and the companies and open-source "
         "projects they feed into. All writing CC BY 4.0.")


def nav_html(rel, up):
    groups = []
    for label, own, subs, prefixes in NAV:
        active = rel == own or any(rel.startswith(pre) for pre in prefixes)
        links = "\n".join(
            f'      <a class="sl{" here" if href == rel else ""}" href="{href if href.startswith("http") else up + href}">{text}</a>'
            for text, href in subs)
        groups.append(
            f'    <div class="ni ni-has">\n'
            f'      <a class="nl{" here" if active else ""}" href="{up}{own}">{label}'
            f'<span class="caret">&#9662;</span></a>\n'
            f'      <div class="sub">\n{links}\n      </div>\n'
            f'    </div>')
    rows = "\n".join(groups)
    return (f'<nav class="site"><div class="row">\n'
            f'  <a class="brand" href="{up}index.html">diniscruz<span>.ai</span></a>\n'
            f'  <a class="parent" href="https://sgit.ai" title="sgit.ai — encrypted git for humans and AI agents, the project Dinis Cruz is building now">↗ building <b>sgit.ai</b></a>\n'
            f'  <a class="ver" href="{up}admin/versions.html" title="Site release history">{VERSION}</a>\n'
            f'  <button class="nav-toggle" type="button" aria-expanded="false" aria-label="Menu">Menu</button>\n'
            f'  <div class="nav-items">\n{rows}\n  </div>\n'
            f'  <a class="gh" href="{GH}">★ GitHub</a>\n'
            f'  <script src="{up}assets/nav.js" defer></script>\n'
            f'</div></nav>')


def footer_html(rel, up):
    md = rel[:-len("html")] + "md"
    cols = "\n".join(
        "  <div>\n"
        f"    <h4>{head}</h4>\n"
        + "\n".join(f'    <a href="{l if l.startswith("http") else up + l}">{t}</a>' for t, l in links)
        + "\n  </div>"
        for head, links in FOOTER)
    return (f'<footer class="site"><div class="cols">\n'
            f'  <div>\n'
            f'    <div class="brandline">diniscruz<span>.ai</span></div>\n'
            f'    <p>{BLURB}</p>\n'
            f'    <p class="netline"><a href="https://sgit.ai"><b>↗ sgit.ai</b></a> — encrypted git for humans and AI agents · '
            f'<a href="https://open-source.sgit.ai">↗ open-source.sgit.ai</a> — open source as a strategy · '
            f'<a href="https://sgit.ai/network/index.html">↗ the sgit.ai network</a></p>\n'
            f'    <p class="verline">site <a href="{up}admin/versions.html">{VERSION}</a> · '
            f'<a href="{up}admin/index.html">engineering</a> · '
            f'<a href="{up}{md}">this page as markdown</a></p>\n'
            f'  </div>\n{cols}\n</div></footer>')

# The date the hand-written pages last changed. It is the sitemap <lastmod> for pages
# that have no publication date of their own. Bump it with version.txt.
SITE_UPDATED = "2026-09-27"
OG_IMAGE = BASE + "og/default.png"
# Allow full snippets and large image previews, in classic results and in AI features
ROBOTS = "index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"
