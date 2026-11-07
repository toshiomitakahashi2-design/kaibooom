"""① 集める：各サイトから広告・デザイン関連の記事を拾い、data/candidates.json に保存する。
RSSがあるサイトはRSSから、ないサイトはニュース一覧ページのリンクから拾う。"""
import html
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
POSTS = json.loads((ROOT / "data/posts.json").read_text(encoding="utf-8"))
SEEN_PATH = ROOT / "data/seen.json"
SEEN = set(json.loads(SEEN_PATH.read_text(encoding="utf-8"))) if SEEN_PATH.exists() else set()
USED = {p["source_url"] for p in POSTS} | SEEN


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (KAIBO-bot/0.1)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def from_rss(src):
    root = ET.fromstring(fetch(src["url"]))
    for it in root.iter("item"):
        yield {
            "title": (it.findtext("title") or "").strip(),
            "link": (it.findtext("link") or "").strip(),
            "summary": re.sub(r"<[^>]+>", " ", it.findtext("description") or "").strip()[:500],
        }


def from_page(src):
    page = fetch(src["url"]).decode("utf-8", errors="ignore")
    seen = set()
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page, re.S | re.I):
        href, inner = m.group(1), m.group(2)
        if not re.search(src["link_pattern"] + r"/?$", href.split("?")[0]):
            continue
        link = urllib.parse.urljoin(src["url"], href.split("#")[0])
        title = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner))).strip()
        if link in seen or len(title) < 6:
            continue
        seen.add(link)
        yield {"title": title[:200], "link": link, "summary": ""}


def score(item, src):
    text = item["title"] + " " + item["summary"]
    if any(k.lower() in text.lower() for k in CONFIG["exclude_keywords"]):
        return 0
    if not src.get("filter"):
        return 1
    return sum(1 for k in CONFIG["keywords"] if k.lower() in text.lower())


def main():
    per_source = []
    for src in CONFIG["sources"]:
        try:
            got = list(from_rss(src) if src["type"] == "rss" else from_page(src))
        except Exception as e:  # 1つのサイトが落ちても止めない
            print(f"skip source {src['name']}: {e}")
            continue
        got = [dict(i, source=src["name"]) for i in got if i["link"] not in USED and score(i, src) > 0]
        if src.get("filter"):
            got.sort(key=lambda i: score(i, src), reverse=True)
        per_source.append(got[: CONFIG["candidates_per_source"]])
        print(f"{src['name']}: {len(got)} found")
    # 各サイトから順番に1本ずつ並べる（偏らないように）
    out = []
    for i in range(CONFIG["candidates_per_source"]):
        out += [lst[i] for lst in per_source if i < len(lst)]
    (ROOT / "data/candidates.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"candidates: {len(out)}")


if __name__ == "__main__":
    main()
