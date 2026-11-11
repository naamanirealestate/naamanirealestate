# naamanirealestate

Static site for Naamani Real Estate, hosted on GitHub Pages from the repo root.

Site: https://naamanirealestate.com/

Styles live in `styles.css`. There is no build step. Stylesheet and font links carry `?v=` plus a hash of the file. `python3 .cursor/skills/ship/scripts/version.py` rewrites those links, and the ship check fails if they are stale.

## Updating content

The homepage carousel is written by `.cursor/skills/ship/scripts/refresh_listings.py`. It reads `https://resider.ca/spotlight.json` and rewrites the cards, the `ItemList` structured data, and the Homepage listings section in `llms.txt`. A GitHub Action runs that script every day at 12:00pm Pacific (`0 19 * * *` UTC). If the feed is down, the current carousel stays in place.

`featured-listing.json` ships as `null`. When you have your own listing, copy `featured-listing.example.json` over it, add the AVIF, WebP, and JPG files it names, and the next refresh puts that card first with its description and Book a showing link. Leave the file as `null` to show only the market carousel.

FAQ answers appear twice: in the visible FAQ section and in the `FAQPage` JSON-LD. Keep them identical.

`llms.txt` is a plain-text summary for AI search engines and assistants. Update it when facts on the page change.

## Images

Photos ship as AVIF and WebP with a JPG fallback. To regenerate after replacing a source photo:

```bash
cd images
magick vancouver-skyline.jpg -resize 1920x -strip tmp.png
cwebp -q 72 tmp.png -o vancouver-skyline-1920.webp
avifenc -q 55 tmp.png vancouver-skyline-1920.avif
rm tmp.png
```

Repeat for each size referenced in `index.html`.

## Run locally

```bash
python3 -m http.server 8000
```

Open http://localhost:8000

## Deploy

Push to `main`. In the GitHub repo: **Settings → Pages → Build and deployment → Deploy from branch → `main` / `/ (root)`**.

After deploying, submit `https://naamanirealestate.com/sitemap.xml` in Google Search Console and Bing Webmaster Tools.
