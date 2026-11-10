#!/usr/bin/env python3
"""Re-publish Anthropic's official changelog feeds with the change list in <description>.

The Claude Code feed only carries its bullet list in <content:encoded>, which many
readers (Slack RSS, Outlook, email digests) ignore. This script fetches each official
feed and writes a copy where every item has:
  - a <description> containing the full HTML change list (or plain text with --plain)
  - the original <content:encoded> kept intact
  - a title prefixed with the product name so items are recognisable in a mixed reader

Usage:
  python rewrite_feeds.py            # writes docs/claude-code.xml and docs/claude-platform.xml
  python rewrite_feeds.py --plain    # description as plain-text bullets instead of HTML (better for Slack)
  python rewrite_feeds.py --out dir  # output directory (default: docs)
"""

import argparse
import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)

FEEDS = [
    {
        "name": "Claude Code",
        "url": "https://code.claude.com/docs/en/changelog/rss.xml",
        "out": "claude-code.xml",
        "title_prefix": "Claude Code ",       # titles are bare version numbers, e.g. "2.1.280"
    },
    {
        "name": "Claude Platform",
        "url": "https://platform.claude.com/docs/en/release-notes/feed.xml",
        "out": "claude-platform.xml",
        "title_prefix": "",                   # titles already say "Claude Platform release notes — <date>"
    },
]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "claude-feeds-rewriter/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def html_to_text(fragment: str) -> str:
    """Turn a <ul><li>…</li></ul> fragment into plain-text bullets, one per line."""
    text = re.sub(r"<li[^>]*>", "\n• ", fragment)
    text = re.sub(r"</?(ul|ol|p|br)[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def item_body(item: ET.Element) -> str:
    """Best available HTML for the change list: content:encoded, else description."""
    enc = item.find("content:encoded", NS)
    if enc is not None and (enc.text or "").strip():
        return enc.text
    desc = item.find("description")
    if desc is not None and (desc.text or "").strip():
        return desc.text
    return ""


def rewrite(feed: dict, plain: bool, self_url: str | None) -> bytes:
    root = ET.fromstring(fetch(feed["url"]))
    channel = root.find("channel")
    if channel is None:
        raise SystemExit(f"{feed['url']}: no <channel> element; not RSS 2.0?")

    # Make the channel title unambiguous in a mixed reader.
    ch_title = channel.find("title")
    if ch_title is not None and feed["name"].lower() not in (ch_title.text or "").lower():
        ch_title.text = f"{feed['name']} changelog"

    # Point the self link at our copy, if we know where it will live.
    if self_url:
        for link in channel.findall("atom:link", NS):
            if link.get("rel") == "self":
                link.set("href", self_url)

    for item in channel.findall("item"):
        body = item_body(item)
        if not body:
            continue

        desc = item.find("description")
        if desc is None:
            desc = ET.SubElement(item, "description")
        desc.text = html_to_text(body) if plain else body

        # Keep content:encoded as the rich version (add it if the source lacked one).
        if item.find("content:encoded", NS) is None:
            enc = ET.SubElement(item, f"{{{NS['content']}}}encoded")
            enc.text = body

        if feed["title_prefix"]:
            title = item.find("title")
            if title is not None and not (title.text or "").startswith(feed["title_prefix"]):
                title.text = feed["title_prefix"] + (title.text or "")

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="docs", help="output directory (default: docs)")
    ap.add_argument("--plain", action="store_true", help="plain-text bullets in <description> instead of HTML")
    ap.add_argument("--base-url", default="", help="public URL the files will be served from, e.g. https://you.github.io/claude-feeds")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for feed in FEEDS:
        self_url = f"{args.base_url.rstrip('/')}/{feed['out']}" if args.base_url else None
        try:
            data = rewrite(feed, args.plain, self_url)
        except Exception as e:  # keep going so one broken source doesn't block the other
            print(f"[fail] {feed['name']}: {e}", file=sys.stderr)
            failures += 1
            continue
        (out_dir / feed["out"]).write_bytes(data)
        print(f"[ok]   {feed['name']} -> {out_dir / feed['out']}")

    return 1 if failures == len(FEEDS) else 0


if __name__ == "__main__":
    sys.exit(main())
