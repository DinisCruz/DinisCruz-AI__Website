#!/usr/bin/env python3
"""Generate redirect stubs that retire docs.diniscruz.ai in favour of diniscruz.ai.

Usage: python3 admin/migration/make_redirect_stubs.py <output-dir>

Every page on docs.diniscruz.ai moved to THE SAME PATH on diniscruz.ai, except
about.html, which is now about/index.html. GitHub Pages cannot send a 301, so the
next-best signal is written for every old URL: a page whose canonical points at the
new URL, with an instant meta refresh and a JS redirect (Google treats an instant
meta refresh as a permanent redirect), and a plain link for anything that runs
neither. A 404.html catch-all does the same for any path not in the list, and
CNAME is kept so the docs.diniscruz.ai host keeps serving the stubs.

The output directory is meant to REPLACE the published contents of the
DinisCruz/docs.diniscruz.ai site (see admin/migration.html for the steps). If the
DNS for diniscruz.ai sits behind Cloudflare, a single bulk-redirect rule
(docs.diniscruz.ai/* -> https://diniscruz.ai/${1}, 301) is better still, and makes
these stubs unnecessary.
"""
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEW = "https://diniscruz.ai/"
OLD_HOST = "docs.diniscruz.ai"
MOVED = {"about.html": "about/index.html"}


def stub(target):
    t = html.escape(target, quote=True)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Moved to diniscruz.ai</title>
<link rel="canonical" href="{t}">
<meta name="robots" content="noindex, follow">
<meta http-equiv="refresh" content="0; url={t}">
<script>location.replace({target!r} + location.hash)</script>
</head><body><p>This page has moved to <a href="{t}">{t}</a>.</p></body></html>
"""


CATCH_ALL = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Moved to diniscruz.ai</title>
<meta name="robots" content="noindex, follow">
<script>
  var p = location.pathname.replace(/^\\/+/, '');
  if (p === '' || p === 'about.html') p = p ? 'about/index.html' : 'index.html';
  location.replace('{NEW}' + p + location.search + location.hash);
</script>
</head><body><p>docs.diniscruz.ai has moved to <a href="{NEW}">{NEW}</a>.</p></body></html>
"""


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    paths = ["index.html", "about.html"]
    paths += sorted(p.relative_to(ROOT / "content").as_posix()[:-3] + ".html"
                    for p in (ROOT / "content").rglob("*.md"))
    for rel in paths:
        target = NEW + MOVED.get(rel, rel)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(stub(target))
    (out / "404.html").write_text(CATCH_ALL)
    (out / "CNAME").write_text(OLD_HOST + "\n")
    (out / ".nojekyll").write_text("")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {NEW}sitemap.xml\n")
    print(f"wrote {len(paths)} redirect stub(s) + 404.html catch-all to {out}")


if __name__ == "__main__":
    main()
