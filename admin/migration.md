<!-- generated from admin/migration.html by admin/build/build.py — do not edit by hand -->

*[diniscruz.ai](/index.md) · site v0.1.0 · canonical: https://diniscruz.ai/admin/migration.html*

> Why the essays moved from docs.diniscruz.ai to diniscruz.ai, how every old URL maps to a new one at the same path, and the steps that retire the old host without losing search ranking.

---

# Moving from docs.diniscruz.ai

The research and essays used to live at **docs.diniscruz.ai**, an MkDocs Material site. It never ranked well. The content sat on a subdomain rather than the name people search for, the pages carried little structured data, and many had no description. So the content has moved here, to the domain that carries the name.

## Every URL keeps its path

The old site used `use_directory_urls: false`, so every page was a plain `.html` file, and this site keeps exactly those paths. **Moving the host is the only change**:

| Old | New |
|---|---|
| `docs.diniscruz.ai/2025/06/07/<slug>.html` | `diniscruz.ai/2025/06/07/<slug>.html` |
| `docs.diniscruz.ai/research/<topic>.html` | `diniscruz.ai/research/<topic>.html` |
| `docs.diniscruz.ai/resources/presentations.html` | `diniscruz.ai/resources/presentations.html` |
| `docs.diniscruz.ai/about.html` | `diniscruz.ai/about/index.html` (a redirect page stays at `/about.html`) |
| `docs.diniscruz.ai/feed_rss_created.xml` | Same path, plus `diniscruz.ai/feed.xml` |

The PDFs, audio and slides stay where they were, on `files.diniscruz.ai`. The markdown sources are copied under `content/` in this repository, with front matter unchanged.

## What changed for search

- Every essay now has a meta description. Where the front matter had none (most of them), the build takes the first real paragraph.
- Structured data: `BlogPosting` with author, date and licence on every essay, and a `Person` record that ties the site to LinkedIn, GitHub and the sgit.ai author pages.
- A sitemap with publication dates, an RSS feed, canonical URLs on the apex domain, and a single chronological [writing index](../writing/index.md) that links to every piece.
- Lighter pages: one small stylesheet and no framework JavaScript.

## Retiring the old host

1. **Best option, if the DNS is on Cloudflare:** a bulk redirect rule `docs.diniscruz.ai/*` → `https://diniscruz.ai/${1}` with status 301. That is a real permanent redirect, and all ranking signals pass through.
2. **Otherwise (GitHub Pages only):** run `python3 admin/migration/make_redirect_stubs.py <dir>` and publish its output as the docs.diniscruz.ai site. Every old URL becomes a page with a canonical link to its new URL, an instant meta refresh and a JS redirect, which Google treats as a permanent move. A `404.html` catch-all covers anything else.
3. In Google Search Console, verify `diniscruz.ai` and submit `https://diniscruz.ai/sitemap.xml`. With 301s in place, also file a change of address from the old property.
4. Update the links that point at the old host: LinkedIn profile and posts, the [sgit.ai](https://sgit.ai/about/index.html) and [open-source.sgit.ai](https://open-source.sgit.ai/about/index.html) author pages, and the GitHub profile.

**Order matters:** switch docs.diniscruz.ai to redirects only after this site is live on diniscruz.ai and the new URLs return 200.

[← How this site is built](index.md)[Release history →](versions.md)

---

*This page is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).*
