---
name: ship
description: Validate, commit, and deploy the Naamani Real Estate static site to GitHub Pages. Runs pre-ship checks (assets, JSON-LD, FAQ parity, listing data, sitemap), refreshes modified dates, audits with Lighthouse, pushes to main, and verifies the live site. Use when the user says ship, deploy, publish, release, or go live for this repo.
disable-model-invocation: true
---

# Ship naamanirealestate.com

Static site, no build step. GitHub Pages deploys `main` from the repo root to https://naamanirealestate.com/. Push only to `origin`; ignore the `heroku` remote.

```
Ship progress:
- [ ] 1. Review changes
- [ ] 2. Refresh dates
- [ ] 3. Run checks
- [ ] 4. Preview and audit
- [ ] 5. Commit and push
- [ ] 6. Verify live
```

## 1. Review changes

```bash
git status --short && git diff --stat
```

Summarize what is shipping. Stop and ask if unrelated or unexpected files appear (`.env`, `.DS_Store`, large originals, stray screenshots).

If the featured listing, FAQ, or facts about Adam changed, confirm every copy is updated:

| Change | Update |
|---|---|
| Listing price, facts, photo, or status | Listing card, `RealEstateListing` JSON-LD, sitemap image entries |
| Listing sold or removed | Remove card and `RealEstateListing` JSON-LD together |
| FAQ wording | Visible `<details>` and `FAQPage` JSON-LD, identical text |
| Stats, credentials, areas, contact | Page copy, JSON-LD, and `llms.txt` |
| New or replaced photo | AVIF and WebP variants per README `Images` section |

## 2. Refresh dates

Set today's date (YYYY-MM-DD) in both places:
- `<lastmod>` in `sitemap.xml`
- `"dateModified"` in the `WebPage` JSON-LD node in `index.html`

## 3. Run checks

```bash
python3 .cursor/skills/ship/scripts/check.py
```

Fix every `FAIL` and rerun until it prints `OK`. Treat `WARN` lines as judgment calls and mention them to the user.

## 4. Preview and audit

```bash
python3 -m http.server 8765
```

Open http://localhost:8765/ in the browser, check desktop and a 375px mobile viewport (hero, listing card, FAQ, CTA, footer). Then:

```bash
npx -y lighthouse@12 http://localhost:8765/ --quiet --chrome-flags="--headless=new" \
  --only-categories=performance,accessibility,best-practices,seo \
  --output=json --output-path=/tmp/lh.json
python3 -c "import json;d=json.load(open('/tmp/lh.json'));print({k:round(v['score']*100) for k,v in d['categories'].items()})"
```

Targets: performance 90+, others 100. Rerun once before investigating a low performance score; cold starts produce noise. Cache-policy and compression findings are GitHub Pages limits and can be ignored locally. Stop the server when done.

## 5. Commit and push

Ask the user to confirm before pushing. Then:

```bash
git add -A
git commit -m "<summary of what changed>"
git push origin main
```

Commit message: imperative, one line, describes the user-visible change (for example `Add FAQ section and structured data`). Never force-push.

## 6. Verify live

GitHub Pages usually publishes within a few minutes. Poll until the new content appears:

```bash
curl -fsS https://naamanirealestate.com/ | grep -c "dateModified\": \"$(date +%F)\""
curl -fsSI https://naamanirealestate.com/llms.txt | head -1
curl -fsSI https://naamanirealestate.com/sitemap.xml | head -1
```

Then report to the user:
- What shipped and the commit hash
- Check and Lighthouse results
- Reminders, when relevant: resubmit the sitemap in Google Search Console and Bing Webmaster Tools after structural or content changes; validate structured data at https://search.google.com/test/rich-results
