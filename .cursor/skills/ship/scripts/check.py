#!/usr/bin/env python3
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from version import mismatches

ROOT = Path(__file__).resolve().parents[4]
errors = []
warnings = []


def read(name):
    path = ROOT / name
    if not path.exists():
        errors.append(f"missing file: {name}")
        return ""
    return path.read_text(encoding="utf-8")


index = read("index.html")
page404 = read("404.html")
sitemap = read("sitemap.xml")
robots = read("robots.txt")
llms = read("llms.txt")
manifest = read("site.webmanifest")

for name, text in (("index.html", index), ("404.html", page404)):
    errors.extend(mismatches(name, text))

for name, text in (("index.html", index), ("404.html", page404), ("site.webmanifest", manifest)):
    for ref in sorted(set(re.findall(r'["\s,](/(?:images/)?[\w.\-]+\.(?:png|jpe?g|webp|avif|svg|ico|css|webmanifest|txt))', text))):
        if not (ROOT / ref.lstrip("/")).exists():
            errors.append(f"{name} references missing asset {ref}")

graph = {}
match = re.search(r'<script type="application/ld\+json">(.*?)</script>', index, re.S)
if not match:
    errors.append("index.html has no JSON-LD block")
else:
    try:
        data = json.loads(match.group(1))
        graph = {node["@type"]: node for node in data.get("@graph", [])}
    except json.JSONDecodeError as exc:
        errors.append(f"JSON-LD does not parse: {exc}")

for required in ("WebSite", "WebPage", "RealEstateAgent", "Person", "FAQPage"):
    if graph and required not in graph:
        errors.append(f"JSON-LD missing {required}")

if "FAQPage" in graph:
    visible = [
        (html.unescape(q).strip(), html.unescape(a).strip())
        for q, a in re.findall(r"<summary>(.*?)</summary>\s*<p>(.*?)</p>", index, re.S)
    ]
    structured = [(e["name"], e["acceptedAnswer"]["text"]) for e in graph["FAQPage"]["mainEntity"]]
    if visible != structured:
        errors.append("visible FAQ and FAQPage JSON-LD differ")

listing = graph.get("ItemList")
featured_path = ROOT / "featured-listing.json"
featured = None
if featured_path.exists():
    try:
        featured = json.loads(featured_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"featured-listing.json does not parse: {exc}")
if featured is not None and not isinstance(featured, dict):
    errors.append("featured-listing.json must be null or an object")
if isinstance(featured, dict):
    for key in ("price", "url", "title"):
        if not featured.get(key):
            errors.append(f"featured-listing.json missing {key}")
    image = featured.get("image") or {}
    if not isinstance(image, dict) or not image.get("jpg"):
        errors.append("featured-listing.json missing image")

items = (listing or {}).get("itemListElement") or []
cards = re.findall(
    r'data-price="(\d+)" data-address="([^"]*)" data-url="([^"]*)"[\s\S]*?<p class="price">\$([\d,]+)</p>[\s\S]*?<h2>([^<]*)</h2>[\s\S]*?<a class="btn" href="([^"]*)">',
    index,
)
if listing and len(cards) != len(items):
    errors.append(f"listing cards ({len(cards)}) do not match ItemList ({len(items)})")
for index_card, card in enumerate(cards):
    price, address, url, shown_price, heading, href = card
    address = html.unescape(address)
    heading = html.unescape(heading)
    if heading != address:
        errors.append(f"listing heading {heading} does not match {address}")
    if href != url:
        errors.append(f"listing link {href} does not match {url}")
    if int(shown_price.replace(",", "")) != int(price):
        errors.append(f"listing price text does not match {address}")
    if index_card < len(items):
        item = items[index_card].get("item") or {}
        if item.get("offers", {}).get("price") != int(price):
            errors.append(f"ItemList price does not match {address}")
        if item.get("url") != url:
            errors.append(f"ItemList url does not match {address}")
        street = (item.get("about") or {}).get("address", {}).get("streetAddress")
        if street != address:
            errors.append(f"ItemList address does not match {address}")
if isinstance(featured, dict) and cards:
    if cards[0][2] != featured["url"] or int(cards[0][0]) != int(featured["price"]):
        errors.append("first listing card does not match featured-listing.json")
if "Homes for sale in Vancouver, Burnaby, and Port Coquitlam" not in index:
    errors.append("listing heading is missing the three cities")

llms_section = re.search(r"## Homepage listings\n(.*?)(?:\n## |\Z)", llms, re.S)
llms_urls = re.findall(r"https://resider\.ca/\S+", llms_section.group(1)) if llms_section else []
item_urls = [((entry.get("item") or {}).get("url")) for entry in items]
if llms_urls != item_urls:
    errors.append("llms.txt homepage listings do not match the ItemList")

for tag in ('rel="canonical"', 'name="description"', 'property="og:image"', "<title>"):
    if tag not in index:
        errors.append(f"index.html missing {tag}")

if sitemap:
    try:
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        lastmod = ET.fromstring(sitemap).find("s:url/s:lastmod", ns)
        modified = graph.get("WebPage", {}).get("dateModified")
        if lastmod is None:
            warnings.append("sitemap.xml has no <lastmod>")
        elif modified and lastmod.text != modified:
            warnings.append(f"sitemap lastmod {lastmod.text} differs from WebPage dateModified {modified}")
    except ET.ParseError as exc:
        errors.append(f"sitemap.xml does not parse: {exc}")

if manifest:
    try:
        json.loads(manifest)
    except json.JSONDecodeError as exc:
        errors.append(f"site.webmanifest does not parse: {exc}")

if robots and "Sitemap: https://naamanirealestate.com/sitemap.xml" not in robots:
    errors.append("robots.txt missing Sitemap line")

if (ROOT / "CNAME").read_text().strip() != "naamanirealestate.com":
    errors.append("CNAME must be naamanirealestate.com")

for name in ("index.html", "styles.css"):
    text = read(name)
    if re.search(r"<!--(?!\[if)|/\*", text):
        warnings.append(f"{name} contains comments; repo convention is no comments")

for big in ROOT.joinpath("images").glob("*"):
    if big.stat().st_size > 400_000:
        warnings.append(f"large image {big.name} ({big.stat().st_size // 1024} KB)")

for line in warnings:
    print(f"WARN  {line}")
for line in errors:
    print(f"FAIL  {line}")
if errors:
    sys.exit(1)
print("OK    all ship checks passed")
