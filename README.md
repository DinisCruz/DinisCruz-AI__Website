# diniscruz.ai

The personal site of [Dinis Cruz](https://diniscruz.ai/about/index.html): essays and research on
AI, cyber security, semantic knowledge graphs and the future of news, and the companies and
open-source projects that work feeds into. It replaces
[docs.diniscruz.ai](https://docs.diniscruz.ai), and every essay keeps the path it had there.

Live site: https://diniscruz.ai (GitHub Pages, deployed from `dev`). Same design language and
pipeline as [sgit.ai](https://github.com/SGit-AI/SGit-AI__Website) and
[open-source.sgit.ai](https://github.com/SGit-AI/SGit-AI__Website__Open-Source).

## Structure

- `index.html`, `about/`, `building/`, `admin/`: hand-written pages (the HTML is authoritative)
- `content/`: the markdown migrated from docs.diniscruz.ai, with front matter intact (authoritative for the essays)
- `2024/`, `2025/`, `research/`, `resources/`: **generated** from `content/`, at the old URLs
- `writing/index.html`, `feed.xml`, `sitemap.xml`, `robots.txt`, `llms.txt`, `llms-full.txt`: generated
- every `.html` has a `.md` twin at the same path (generated)
- `about.html`: a redirect page for the old `/about.html` URL
- `admin/build/`: `site_config.py` (nav, footer, identity), `build.py`, `html_to_md.py`, `validate.js`, `version.txt`
- `admin/migration/make_redirect_stubs.py`: generates the redirect site that retires docs.diniscruz.ai

## Release process

1. Bump `admin/build/version.txt` (vX.Y.Z) and add a row to `admin/versions.html`.
2. `pip install -r admin/build/requirements.txt` (once)
3. `python3 admin/build/build.py`
4. `node admin/build/validate.js`
5. `git commit -am "site vX.Y.Z: ..." && git push origin dev`

Every push to `dev` runs `.github/workflows/deploy-pages.yml`: rebuild (and fail if stale) →
validate → auto-tag `vX.Y.Z` (checked against `version.txt` and the commit subject) → deploy
to GitHub Pages. Pull requests run the checks only.

All writing CC BY 4.0 unless noted. Code under the repository licence (Apache-2.0).
