#!/usr/bin/env python3
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

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

listing = graph.get("RealEstateListing")
card = re.search(r'<p class="price">\$([\d,]+)</p>', index)
if listing and card:
    if int(card.group(1).replace(",", "")) != listing["offers"]["price"]:
        errors.append("listing card price does not match RealEstateListing JSON-LD")
elif card and not listing:
    errors.append("listing card present but RealEstateListing JSON-LD missing")
elif listing and not card:
    errors.append("RealEstateListing JSON-LD present but no listing card")

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
