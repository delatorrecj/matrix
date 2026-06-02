#!/usr/bin/env python3
"""MATRIX — scrape the published Iloilo Enhanced LPTRP jeepney routes.

The authoritative LTFRB route geometry would need an FOI (see outreach/), but
the Enhanced LPTRP (MC 2023-036) routes are documented publicly street-by-street.
This pulls those descriptions into raw/transport/ as text + JSON, to seed an
OSM -> partial-GTFS reconstruction (Medium confidence; tag as such).

    python fetch/scrape_lptrp.py     (stdlib only)
"""
import html as ihtml
import json
import re
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "raw" / "transport"
UA = "Mozilla/5.0 (MATRIX/data-fetch; +https://github.com/delatorrecj/matrix)"
INDEX = "https://ilonggoengineer.com/iloilocity-lptrp/"
SECONDARY = "https://shemaegomez.com/iloilo-city-jeepney-routes/"


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
        declared = r.headers.get_content_charset()
    # the source serves cp1252 bytes (en-dash 0x96) — try declared, utf-8, then cp1252
    for enc in (declared, "utf-8", "cp1252"):
        if enc:
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
    return raw.decode("utf-8", "replace")


def to_text(html):
    p = Text()
    p.feed(html)
    return "\n".join(p.parts)


def route_links(html, base="https://ilonggoengineer.com"):
    hrefs = re.findall(r'href="([^"]+)"', html)
    out, seen = [], set()
    for h in hrefs:
        if h.startswith("/"):
            h = base + h
        # the LPTRP detail pages are /iloiloroutes-NN/ — match those exactly,
        # skip share/oembed/abuse/mailto junk
        if re.search(r"ilonggoengineer\.com/iloiloroutes-\d+/?$", h) and h not in seen:
            seen.add(h)
            out.append(h)
    return out


def slug(url):
    return re.sub(r"[^a-z0-9]+", "-", url.rstrip("/").rsplit("/", 1)[-1].lower()).strip("-") or "route"


def main():
    (OUT / "routes").mkdir(parents=True, exist_ok=True)
    routes = []
    try:
        idx_html = fetch(INDEX)
    except Exception as e:
        print(f"FAIL index: {e}")
        return 1
    (OUT / "lptrp_index.txt").write_text(to_text(idx_html), encoding="utf-8")
    links = route_links(idx_html)
    print(f"index OK: {len(links)} candidate route pages")

    for i, url in enumerate(links, 1):
        try:
            html = fetch(url)
            text = to_text(html)
            (OUT / "routes" / f"{slug(url)}.txt").write_text(text, encoding="utf-8")
            m = re.search(r"<title>(.*?)</title>", html, re.S)
            title = ihtml.unescape(m.group(1)) if m else slug(url)
            title = re.sub(r"\s+", " ", title).strip()
            title = title.replace("�", "–")  # defensive: map stray U+FFFD to en-dash
            title = re.sub(r"\s*[–—-]\s*Ilonggo Engineer\s*$", "", title)  # strip site suffix
            routes.append({"n": i, "title": title, "url": url})
            print(f"  OK  {i:>2}. {url}")
            time.sleep(1)  # be polite
        except Exception as e:
            print(f"  FAIL {url}: {e}")

    try:
        (OUT / "shemae_jeepney_routes.txt").write_text(to_text(fetch(SECONDARY)), encoding="utf-8")
        print("secondary OK: shemaegomez")
    except Exception as e:
        print(f"secondary FAIL: {e}")

    (OUT / "routes.json").write_text(json.dumps(routes, indent=2), encoding="utf-8")
    print(f"\nsaved {len(routes)} route pages -> raw/transport/routes/  (routes.json index)")
    print("NOTE: descriptions are street-level (Medium confidence). Next: map to OSM ways -> partial GTFS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
