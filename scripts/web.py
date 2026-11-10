"""出典ページを読むための共通の道具。
- article_text: ページから本文らしい部分だけを取り出す
- find_media: ページから画像・動画（YouTube / Vimeo）を探す
画像や動画そのものはコピーせず、出典元のURLを参照して表示する。"""
import html
import re
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (KAIBO-bot/0.2)"


def fetch_html(url, limit=2_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read(limit).decode("utf-8", errors="ignore")


def _strip(fragment):
    text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", fragment))
    return re.sub(r"\s+", " ", text).strip()


def meta(page, *names):
    for name in names:
        for pat in (rf'<meta[^>]+(?:property|name)=["\']{name}["\'][^>]+content=["\']([^"\']*)',
                    rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']{name}["\']'):
            m = re.search(pat, page, re.I)
            if m and m.group(1).strip():
                return html.unescape(m.group(1).strip())
    return ""


def _main_block(page):
    """<article> か <main> があればそこを、なければページ全体を返す。"""
    clean = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header|aside|form)[^>]*>.*?</\1>", " ", page)
    blocks = re.findall(r"(?is)<article[^>]*>(.*?)</article>", clean) or re.findall(r"(?is)<main[^>]*>(.*?)</main>", clean)
    return max(blocks, key=len) if blocks else clean


def article_text(page, limit=20000):
    """見出し・段落・箇条書きを優先して、本文を読みやすいテキストにする。"""
    block = _main_block(page)
    parts = []
    for m in re.finditer(r"(?is)<(h[1-4]|p|li|blockquote|figcaption)[^>]*>(.*?)</\1>", block):
        t = _strip(m.group(2))
        if len(t) < 2:
            continue
        parts.append(("■ " + t) if m.group(1).lower().startswith("h") else t)
    text = "\n".join(parts)
    if len(text) < 400:  # 段落タグがほとんど無いページ
        text = _strip(block)
    if len(text) < 600:  # <article> が見出しだけ、などで本文を取りこぼしたとき：ページ全体から読む
        whole = _strip(re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", page))
        if len(whole) > len(text):
            text = whole
    desc = meta(page, "og:description", "description")
    head = f"（ページの説明）{desc}\n\n" if desc else ""
    return (head + text)[:limit]


SKIP_IMG = re.compile(r"logo|icon|avatar|sprite|banner|badge|emoji|spacer|pixel|blank|loading|placeholder|profile|author|\.svg|\.gif|ads?[/_.-]|1x1", re.I)


def _img_ok(src):
    if not src or src.startswith("data:") or SKIP_IMG.search(src):
        return False
    # 幅・高さが小さいと分かる画像（サムネイル等）は除く
    m = re.search(r"[?&](?:w|width)=(\d+)", src)
    return not (m and int(m.group(1)) < 300)


def find_media(page, base_url, max_images=6, max_videos=2):
    """戻り値: (メイン画像URL, ギャラリー画像URLのリスト, 動画のリスト)"""
    cover = meta(page, "og:image", "og:image:url", "twitter:image")
    cover = urllib.parse.urljoin(base_url, cover) if cover else ""

    videos, seen_v = [], set()

    def add_video(kind, vid):
        key = (kind, vid)
        if key not in seen_v and len(videos) < max_videos:
            seen_v.add(key)
            videos.append({"type": kind, "id": vid})

    for m in re.finditer(r"(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=|shorts/|v/)|youtu\.be/)([A-Za-z0-9_-]{11})", page):
        add_video("youtube", m.group(1))
    for m in re.finditer(r"(?:player\.vimeo\.com/video/|vimeo\.com/)(\d{6,12})", page):
        add_video("vimeo", m.group(1))

    gallery, seen_i = [], {cover}
    block = _main_block(page)
    for m in re.finditer(r"(?is)<img\b([^>]*)>", block):
        attrs = m.group(1)
        src = ""
        for a in ("data-src", "data-lazy-src", "data-original", "src"):
            mm = re.search(rf'\b{a}=["\']([^"\']+)', attrs, re.I)
            if mm and not mm.group(1).startswith("data:"):
                src = mm.group(1)
                break
        if not src:
            mm = re.search(r'\bsrcset=["\']([^"\']+)', attrs, re.I)
            if mm:  # srcset のいちばん大きいもの
                src = mm.group(1).split(",")[-1].strip().split(" ")[0]
        src = urllib.parse.urljoin(base_url, html.unescape(src))
        w = re.search(r'\bwidth=["\']?(\d+)', attrs)
        if w and int(w.group(1)) < 300:
            continue
        if _img_ok(src) and src not in seen_i:
            seen_i.add(src)
            gallery.append(src)
        if len(gallery) >= max_images:
            break
    return cover, gallery, videos
