"""③ 画像：画像がまだない記事について、出典ページのOGP画像（SNS共有用の画像）のURLを取得する。
画像そのものはコピーせず、出典元のURLを参照して表示する。"""
import html
import json
import pathlib
import re
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS_PATH = ROOT / "data/posts.json"

PATTERNS = [
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
]


def og_image(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (KAIBO-bot/0.1)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        head = r.read(300_000).decode("utf-8", errors="ignore")
    for pat in PATTERNS:
        m = re.search(pat, head, re.I)
        if m:
            return urllib.parse.urljoin(url, html.unescape(m.group(1).strip()))
    return None


def main():
    posts = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    for p in posts:
        if p.get("image"):
            continue
        try:
            img = og_image(p["source_url"])
        except Exception as e:
            print(f"skip {p['slug']}: {e}")
            continue
        if img:
            p["image"] = img
            print(f"image {p['slug']}: {img}")
    POSTS_PATH.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
