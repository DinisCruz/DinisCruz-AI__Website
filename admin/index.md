<!-- generated from admin/index.html by admin/build/build.py — do not edit by hand -->

*[diniscruz.ai](/index.md) · site v0.1.1 · canonical: https://diniscruz.ai/admin/index.html*

> How diniscruz.ai is built and released: hand-written HTML plus pages generated from the markdown migrated from docs.diniscruz.ai, a markdown twin at every URL, llms.txt, and a validate-then-deploy pipeline to GitHub Pages.

---

# How this site is built

This is a static site on GitHub Pages, built the same way as [sgit.ai](https://sgit.ai) and [open-source.sgit.ai](https://open-source.sgit.ai), and sharing their design language. There is no framework and no JavaScript bundle. Every page works without scripts, and every page has a markdown twin.

## Two kinds of page

| Kind | Source of truth | What the build does |
|---|---|---|
| **Hand-written** home, about, building, admin | The `.html` file itself, edited by hand | Rewrites the nav and footer from `admin/build/site_config.py`, fills the `<!-- build:* -->` blocks (such as the latest-writing cards), and derives the `.md` twin from the HTML |
| **Generated** essays, research hubs, talks | The markdown under `content/`, migrated from docs.diniscruz.ai with its front matter intact | Renders each file to HTML **at the same path it had on docs.diniscruz.ai**, expands the old MkDocs macros (PDF, LinkedIn, video and slide embeds), and writes the cleaned markdown as its twin |

## The indexing surfaces

- **[sitemap.xml](../sitemap.xml)** and **[robots.txt](../robots.txt)**. Every indexable page, with the publication date as `lastmod` for essays.
- **[feed.xml](../feed.xml)**, the RSS feed of the writing. It is also published as `feed_rss_created.xml` and `feed_rss_updated.xml`, the names the old MkDocs site used.
- **Structured data.** A `Person` record on the home and about pages, `BlogPosting` on every essay (author, date, licence, word count), and canonical and Open Graph tags everywhere.
- **[llms.txt](../llms.txt)**, which is self-sufficient: who I am and every page with its description. **[llms-full.txt](../llms-full.txt)** holds every page in one file, for agents that cannot follow links.

## Search and AI features

Google's guidance for its AI features (AI Overviews and AI Mode) is that no special optimisation is needed beyond the fundamentals, so this site does the fundamentals and checks them on every build:

- **Crawlable, indexable text.** Every page is static HTML that works without JavaScript. Each has one `<h1>`, a real title and description, and a canonical URL that appears in [sitemap.xml](../sitemap.xml). `validate.js` fails the release if any of that is missing.
- **Snippet-eligible.**`max-snippet:-1, max-image-preview:large` on every page, so search results and AI answers can quote and preview it in full.
- **Structured data that matches the visible page.**`Person`, `WebSite`, `BlogPosting`, `BreadcrumbList` (generated from the same data as the visible breadcrumb) and `CollectionPage`.
- **Internal links.** Every essay links to its topic hub, its neighbours in time, and the five nearest pieces on the same topic.
- **No duplicates in the index.** The markdown twins and `llms-full.txt` repeat the HTML for agents. [robots.txt](../robots.txt) keeps Googlebot and Bingbot off them, so each page is indexed once, as HTML. Other crawlers and agents can still fetch them.

**llms.txt** follows the [llmstxt.org](https://llmstxt.org/) format. Google has said its search does not use llms.txt, so it is here for the other agents and LLM tools that do read it, not for ranking.

## Release process

1. Bump `admin/build/version.txt` and add a row to [the release history](versions.md).
2. `pip install -r admin/build/requirements.txt` (python-markdown and PyYAML, once).
3. `python3 admin/build/build.py` regenerates every derived file.
4. `node admin/build/validate.js` checks the version, internal links, canonicals, twins and licence lines.
5. `git commit -am "site vX.Y.Z: ..." && git push origin dev`

Every push runs `.github/workflows/deploy-pages.yml`. It rebuilds the site and fails if anything committed is stale, then validates, then deploys to GitHub Pages. Pull requests run the checks only.

## Adding an essay

Drop a markdown file at `content/YYYY/MM/DD/slug.md` with the same front matter the old site used (`title`, `authors`, `date`, and optionally `description`, `tags`, `pdf_file`, `linkedin` and `back_link`), then run the build. It appears in the writing index, the feed, the sitemap, llms.txt and, if it is among the newest, on the home page.

[← About](../about/index.md)[Moving from docs.diniscruz.ai →](migration.md)

---

*This page is released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).*
