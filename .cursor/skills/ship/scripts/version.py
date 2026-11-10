#!/usr/bin/env python3
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PAGES = ("index.html", "404.html")
LINK = re.compile(r'(href|src)="(/(?:styles\.css|fonts/[\w.\-]+\.woff2))(?:\?v=[0-9a-f]+)?"')


def digest(url):
    path = ROOT / url.lstrip("/")
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def stamp(text):
    def repl(match):
        url = match.group(2)
        version = digest(url)
        if version is None:
            return match.group(0)
        return f'{match.group(1)}="{url}?v={version}"'

    return LINK.sub(repl, text)


def mismatches(name, text):
    found = []
    for match in LINK.finditer(text):
        url = match.group(2)
        version = digest(url)
        current = match.group(0).split("?v=")[-1].rstrip('"') if "?v=" in match.group(0) else ""
        if version is None:
            found.append(f"{name} links missing file {url}")
        elif current != version:
            found.append(f"{name} serves {url} as ?v={current or 'none'}, file is ?v={version}")
    return found


def main():
    changed = False
    for name in PAGES:
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        updated = stamp(text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed = True
            print(f"stamped {name}")
    if not changed:
        print("versions already match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
