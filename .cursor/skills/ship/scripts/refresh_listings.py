#!/usr/bin/env python3
import html
import json
import os
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INDEX = ROOT / "index.html"
LLMS = ROOT / "llms.txt"
SITEMAP = ROOT / "sitemap.xml"
FEATURED = ROOT / "featured-listing.json"
SPOTLIGHT_URL = os.environ.get("SPOTLIGHT_URL", "https://resider.ca/spotlight.json")
PLACES = "Homes for sale in Vancouver, Burnaby, and Port Coquitlam"
LABELS = {
    "Single Family Residence": "House",
    "Townhouse": "Townhouse",
    "Apartment/Condo": "Condo",
}


def fetch_market():
    try:
        request = urllib.request.Request(
            SPOTLIGHT_URL,
            headers={
                "User-Agent": "NaamaniRealEstateBot/1.0 (+https://naamanirealestate.com)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except Exception as exc:
        print(f"spotlight fetch failed: {exc}", file=sys.stderr)
        return None
    listings = payload.get("listings") if isinstance(payload, dict) else None
    if not isinstance(listings, list):
        print("spotlight response has no listings", file=sys.stderr)
        return None
    return listings


def load_featured():
    if not FEATURED.exists():
        return None
    data = json.loads(FEATURED.read_text(encoding="utf-8"))
    if data is None:
        return None
    if not isinstance(data, dict):
        raise SystemExit("featured-listing.json must be null or an object")
    return data


def label(subtype):
    return LABELS.get(subtype, subtype or "Home")


def money(price):
    return f"${int(price):,}"


def fact_beds(count):
    count = int(count)
    word = "bed" if count == 1 else "beds"
    return f"{count} {word}"


def fact_baths(count):
    count = int(count)
    word = "bath" if count == 1 else "baths"
    return f"{count} {word}"


def fact_area(value):
    return f"{int(value):,} sq ft"


def market_slide(listing):
    subtype = label(listing.get("subtype"))
    address = listing["address"]
    city = listing.get("city") or ""
    area = listing.get("area") or city
    neighbourhood = area.split(",")[0].strip() or city
    return {
        "featured": False,
        "kicker": city or neighbourhood,
        "price": int(listing["price"]),
        "title": address,
        "place": neighbourhood,
        "city": city,
        "facts": [
            fact_beds(listing.get("beds") or 0),
            fact_baths(listing.get("baths") or 0),
            fact_area(listing.get("living_area") or 0),
        ],
        "copy": "",
        "url": listing["url"],
        "showing": "",
        "photo": listing["photo_url"],
        "alt": f"{subtype} at {address}, {area}".rstrip(", "),
        "beds": int(listing.get("beds") or 0),
        "baths": int(listing.get("baths") or 0),
        "living_area": int(listing.get("living_area") or 0),
        "subtype": subtype,
    }


def featured_slide(featured):
    image = featured.get("image") or {}
    city = featured.get("city") or ""
    subtype = featured.get("subtype") or ""
    return {
        "featured": True,
        "kicker": featured.get("kicker") or "Featured listing",
        "price": int(featured["price"]),
        "title": featured["title"],
        "place": featured.get("place") or city,
        "city": city,
        "facts": [fact for fact in featured.get("facts") or [] if fact != subtype],
        "copy": featured.get("copy") or "",
        "url": featured["url"],
        "showing": featured.get("showing") or "",
        "photo": image,
        "alt": image.get("alt") or featured["title"],
        "beds": int(featured.get("beds") or 0),
        "baths": int(featured.get("baths") or 0),
        "living_area": int(featured.get("living_area") or 0),
        "subtype": subtype,
        "description": featured.get("copy") or "",
    }


def attr(value):
    return html.escape(str(value), quote=True)


def photo_html(slide):
    photo = slide["photo"]
    if isinstance(photo, dict):
        sources = ""
        if photo.get("avif"):
            sources += f'\n            <source type="image/avif" srcset="{attr(photo["avif"])}" sizes="(max-width: 900px) 100vw, 600px">'
        if photo.get("webp"):
            sources += f'\n            <source type="image/webp" srcset="{attr(photo["webp"])}" sizes="(max-width: 900px) 100vw, 600px">'
        width = f' width="{int(photo["width"])}"' if photo.get("width") else ""
        height = f' height="{int(photo["height"])}"' if photo.get("height") else ""
        return f"""<picture>{sources}
            <img src="{attr(photo.get("jpg") or "")}" alt="{attr(slide["alt"])}"{width}{height} decoding="async">
          </picture>"""
    loading = ' fetchpriority="high"' if slide.get("first") else ' loading="lazy"'
    return f'<img src="{attr(photo)}" alt="{attr(slide["alt"])}" decoding="async"{loading}>'


CHEVRON_LEFT = '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><path d="M12.5 4.5 7 10l5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
CHEVRON_RIGHT = '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><path d="M7.5 4.5 13 10l-5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ARROW_RIGHT = '<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><path d="M4 10h11m-4.5-4.5L15 10l-4.5 4.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def fact_html(fact):
    value, _, unit = fact.partition(" ")
    if not unit:
        return f"<li><strong>{html.escape(fact)}</strong></li>"
    return f"<li><strong>{html.escape(value)}</strong> <span>{html.escape(unit)}</span></li>"


def short_price(price):
    if price >= 1_000_000:
        return "$" + f"{price / 1_000_000:.2f}".rstrip("0").rstrip(".") + "M"
    return f"${round(price / 1000):,}K"


def thumb_src(slide):
    photo = slide["photo"]
    if isinstance(photo, dict):
        return photo.get("jpg") or ""
    return photo


def slide_html(slide, index, total):
    hidden = "" if index == 0 else " hidden"
    active = " is-active" if index == 0 else ""
    facts = "".join(fact_html(fact) for fact in slide["facts"])
    copy = f'\n            <p class="listing-copy">{html.escape(slide["copy"])}</p>' if slide["copy"] else ""
    tag = f'\n            <span class="listing-tag">{html.escape(slide["subtype"])}</span>' if slide["subtype"] else ""
    showing = ""
    if slide["showing"]:
        showing = f'\n              <a class="btn btn-ghost" href="{attr(slide["showing"])}">Book a showing</a>'
    return f"""        <article class="listing-card{active}" data-slide data-price="{int(slide["price"])}" data-address="{attr(slide["title"])}" data-url="{attr(slide["url"])}"{hidden}>
          <div class="listing-media">
            <a class="listing-photo" href="{attr(slide["url"])}" tabindex="-1" aria-hidden="true">
              {photo_html(slide)}
            </a>{tag}
          </div>
          <div class="listing-body">
            <p class="kicker">{html.escape(slide["kicker"])}</p>
            <p class="price">{money(slide["price"])}</p>
            <h2>{html.escape(slide["title"])}</h2>
            <p class="place">{html.escape(slide["place"])}</p>
            <ul class="facts">{facts}</ul>{copy}
            <div class="actions">
              <a class="btn" href="{attr(slide["url"])}">View listing<span class="sr-only"> at {html.escape(slide["title"])}</span> {ARROW_RIGHT}</a>{showing}
            </div>
          </div>
        </article>"""


def thumbs_html(slides):
    buttons = []
    for index, slide in enumerate(slides):
        current = ' aria-current="true"' if index == 0 else ""
        active = " is-active" if index == 0 else ""
        place = slide["place"].split(",")[0].strip() or slide["city"]
        buttons.append(
            f"""<button type="button" class="listing-thumb{active}" data-dot aria-label="Show {attr(slide["title"])}"{current}>
          <img src="{attr(thumb_src(slide))}" alt="" width="96" height="72" loading="lazy" decoding="async">
          <span class="listing-thumb-text" aria-hidden="true"><span class="listing-thumb-price">{short_price(slide["price"])}</span><span class="listing-thumb-place">{html.escape(place)}</span></span>
        </button>"""
        )
    return "\n        ".join(buttons)


def section_html(slides):
    articles = "\n".join(slide_html(slide, index, len(slides)) for index, slide in enumerate(slides))
    toolbar = ""
    rail = ""
    if len(slides) > 1:
        toolbar = f"""
        <div class="listing-toolbar" data-listing-toolbar>
          <p class="listing-count" data-listing-count aria-live="polite">1 / {len(slides)}</p>
          <button type="button" class="listing-arrow" data-prev aria-label="Previous listing">{CHEVRON_LEFT}</button>
          <button type="button" class="listing-arrow" data-next aria-label="Next listing">{CHEVRON_RIGHT}</button>
        </div>"""
        rail = f"""
      <div class="listing-rail" data-listing-nav data-listing-rail>
        {thumbs_html(slides)}
      </div>"""
    return f"""  <section class="listing" id="listing-carousel" data-listing-carousel tabindex="0" aria-roledescription="carousel" aria-labelledby="listings-heading">
    <div class="listing-panel wrap">
      <div class="listing-head">
        <div>
          <p class="kicker">On the market</p>
          <h2 id="listings-heading" class="listing-intro">{PLACES}</h2>
        </div>{toolbar}
      </div>
      <div class="listing-stage" id="listing-slides">
{articles}
      </div>{rail}
    </div>
  </section>"""


def listing_node(slide):
    image = slide["photo"]
    if isinstance(image, dict):
        image = image.get("jpg") or ""
        if image.startswith("/"):
            image = "https://naamanirealestate.com" + image
    node = {
        "@type": "RealEstateListing",
        "name": f'{slide["title"]}, {slide["place"]}'.strip(", "),
        "url": slide["url"],
        "image": image,
        "offers": {
            "@type": "Offer",
            "price": slide["price"],
            "priceCurrency": "CAD",
            "availability": "https://schema.org/InStock",
        },
        "about": {
            "@type": "Residence",
            "name": slide["subtype"] or "Home",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": slide["title"],
                "addressLocality": slide["city"],
                "addressRegion": "BC",
                "addressCountry": "CA",
            },
            "numberOfBedrooms": slide["beds"],
            "numberOfBathroomsTotal": slide["baths"],
            "floorSize": {
                "@type": "QuantitativeValue",
                "value": slide["living_area"],
                "unitCode": "FTK",
            },
        },
    }
    if slide.get("description"):
        node["description"] = slide["description"]
    return node


def item_list(slides):
    return {
        "@type": "ItemList",
        "@id": "https://naamanirealestate.com/#listings",
        "name": PLACES,
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "numberOfItems": len(slides),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index + 1,
                "item": listing_node(slide),
            }
            for index, slide in enumerate(slides)
        ],
    }


def replace_jsonld(page, slides, today):
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    if not match:
        raise SystemExit("index.html has no JSON-LD block")
    data = json.loads(match.group(1))
    graph = [node for node in data.get("@graph", []) if node.get("@type") not in ("RealEstateListing", "ItemList")]
    for node in graph:
        if node.get("@type") == "WebPage":
            node["dateModified"] = today
    faq = next(index for index, node in enumerate(graph) if node.get("@type") == "FAQPage")
    graph.insert(faq, item_list(slides))
    data["@graph"] = graph
    dumped = json.dumps(data, indent=2, ensure_ascii=False)
    indented = "\n".join(("  " + line) if line else line for line in dumped.splitlines())
    block = f'\n  <script type="application/ld+json">\n{indented}\n  </script>'
    return page[:match.start()] + block + page[match.end():]


def replace_section(page, slides):
    pattern = re.compile(r'  <section class="listing"[\s\S]*?</section>\n')
    replacement = section_html(slides) + "\n"
    if not pattern.search(page):
        raise SystemExit("index.html has no listing section")
    return pattern.sub(replacement, page, count=1)


def llms_section(slides):
    lines = ["## Homepage listings", ""]
    for slide in slides:
        lines.append(
            f'- {slide["title"]}, {slide["city"]}: {money(slide["price"])} {slide["subtype"]}. {slide["url"]}'
        )
    lines.append("")
    return "\n".join(lines)


def replace_llms(text, slides):
    text = text.replace("Overview, featured listing,", "Overview, listing carousel,")
    block = llms_section(slides).rstrip() + "\n"
    pattern = re.compile(r"## Homepage listings\n.*?(?=\n## |\Z)", re.S)
    if pattern.search(text):
        return pattern.sub(block, text, count=1)
    if not text.endswith("\n"):
        text += "\n"
    return text + "\n" + block


def signature(slides):
    return [(slide["url"], slide["price"], slide["title"]) for slide in slides]


def existing_signature(page):
    return [
        (html.unescape(url), int(price), html.unescape(address))
        for price, address, url in re.findall(
            r'data-price="(\d+)" data-address="([^"]*)" data-url="([^"]*)"',
            page,
        )
    ]


def main():
    page = INDEX.read_text(encoding="utf-8")
    market = fetch_market()
    if market is None:
        if os.environ.get("SPOTLIGHT_REQUIRED"):
            raise SystemExit(1)
        if 'data-slide' in page:
            print("left the current carousel in place")
            return
        raise SystemExit(1)

    featured = load_featured()
    slides = []
    if featured:
        slides.append(featured_slide(featured))
    slides.extend(market_slide(listing) for listing in market)
    if slides:
        slides[0]["first"] = True
    if not slides:
        print("left the current carousel in place")
        return
    if signature(slides) == existing_signature(page) and section_html(slides) in page:
        print("listings unchanged")
        return

    today = date.today().isoformat()
    page = replace_jsonld(page, slides, today)
    page = replace_section(page, slides)
    INDEX.write_text(page, encoding="utf-8")
    LLMS.write_text(replace_llms(LLMS.read_text(encoding="utf-8"), slides), encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")
    sitemap = re.sub(r"<lastmod>.*?</lastmod>", f"<lastmod>{today}</lastmod>", sitemap, count=1)
    sitemap = sitemap.replace(
        "    <image:image>\n      <image:loc>https://naamanirealestate.com/images/10-7428-southwynde.jpg</image:loc>\n    </image:image>\n",
        "",
    )
    SITEMAP.write_text(sitemap, encoding="utf-8")
    print(f"wrote {len(slides)} listings")


if __name__ == "__main__":
    main()
