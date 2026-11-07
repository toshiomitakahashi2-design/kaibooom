"""① 集める：RSSから広告・デザイン関連の記事を拾い、data/candidates.json に保存する。"""
import json
import pathlib
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
POSTS = json.loads((ROOT / "data/posts.json").read_text(encoding="utf-8"))
USED = {p["source_url"] for p in POSTS}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "KAIBO-bot/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def items(feed_url):
    root = ET.fromstring(fetch(feed_url))
    for it in root.iter("item"):
        yield {
            "title": (it.findtext("title") or "").strip(),
            "link": (it.findtext("link") or "").strip(),
            "summary": (it.findtext("description") or "").strip()[:500],
            "date": (it.findtext("pubDate") or "").strip(),
        }


def score(item):
    text = item["title"] + item["summary"]
    if any(k in text for k in CONFIG["exclude_keywords"]):
        return 0
    return sum(1 for k in CONFIG["keywords"] if k in text)


def main():
    found = []
    for url in CONFIG["feeds"]:
        try:
            found += list(items(url))
        except Exception as e:  # 1つのフィードが落ちても止めない
            print(f"skip feed {url}: {e}")
    found = [i for i in found if i["link"] not in USED and score(i) > 0]
    found.sort(key=score, reverse=True)
    out = found[: CONFIG["posts_per_run"] * 3]  # 下書きで不採用もあるので多めに
    (ROOT / "data/candidates.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"candidates: {len(out)}")


if __name__ == "__main__":
    main()
