"""Gensparkなど、外で書いた記事を取り込む。

使い方：  python scripts/import_inbox.py data/inbox/2026-11-21.json

入れるファイルは記事の配列（JSON）。1本ずつ、次のどちらかとして取り込む。
- 新しい記事 …… 「承認待ち（下書き）」として data/posts.json に足す。公開はしない
- 既存の記事の修正案 …… "slug" が既存の記事と同じなら、本文は変えずに「修正案」として置く

どちらも管理ページ（/admin.html）の「承認待ち」に並ぶ。
AIが書いたままの文は data/originals.json に残し、髙橋の手直しとの差分から学べるようにする。
Claudeは呼ばないので料金はかからない。"""
import datetime
import json
import pathlib
import re
import sys

from engine import BUZZ, LINT, TEXT_FIELDS, save_original

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS_PATH = ROOT / "data/posts.json"
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
META = ("category", "work", "client", "agency", "production", "award", "country", "source_name", "source_url", "image", "date_released")
REQUIRED = ("title", "oneliner", "about", "points", "work", "client", "source_url")


def slugify(url):
    """出典URLの末尾から、英数字だけのslugをつくる（日本語の作品名からは作らない）。"""
    s = re.sub(r"[^0-9a-z]+", "-", norm_url(url).split("//")[-1])[-40:].strip("-")
    return "g-" + (s or "post")


def norm_url(u):
    return re.sub(r"[?#].*$", "", (u or "").strip()).rstrip("/").lower()


def check(item):
    """文体ルールのうち、機械的に見つけられるものだけ報告する（取り込みは止めない）。"""
    text = "\n".join(str(item.get(k, "")) for k in TEXT_FIELDS)
    notes = [w for w in LINT if w in text]
    notes += [f"定番ワード:{w}" for w in BUZZ if w in text]
    return notes


def main(path):
    items = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if isinstance(items, dict):
        items = items.get("articles") or items.get("posts") or [items]
    posts = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    by_slug = {p["slug"]: p for p in posts}
    by_url = {norm_url(p.get("source_url")): p for p in posts if p.get("source_url")}
    next_no = max((p["no"] for p in posts), default=0) + 1
    today = datetime.date.today().isoformat()
    added = proposed = skipped = 0
    for it in items:
        it = {k: (v.strip() if isinstance(v, str) else v) for k, v in it.items()}
        if it.get("points"):
            it["points"] = re.sub(r"\n{3,}", "\n\n", it["points"])
        target = by_slug.get(it.get("slug", ""))
        if target:  # 既存の記事への修正案
            prop = {k: it[k] for k in TEXT_FIELDS if it.get(k) and it[k] != target.get(k)}
            if not prop:
                print(f"No.{target['no']}: 変更なし")
                continue
            prop.update({"by": it.get("by", "Genspark"), "date": today})
            if it.get("note"):
                prop["note"] = it["note"]
            target["proposal"] = prop
            proposed += 1
            notes = check(it)
            print(f"No.{target['no']}: 修正案を置きました" + (f"　要確認: {', '.join(notes)}" if notes else ""))
            continue
        missing = [k for k in REQUIRED if not it.get(k)]
        if missing:
            print(f"skip（足りない項目: {', '.join(missing)}）: {it.get('title', '?')}")
            skipped += 1
            continue
        if norm_url(it["source_url"]) in by_url:
            print(f"skip（同じ出典の記事がすでにあります No.{by_url[norm_url(it['source_url'])]['no']}）: {it['title']}")
            skipped += 1
            continue
        slug = it.get("slug") or slugify(it["source_url"])
        base, n = slug, 2
        while slug in by_slug:
            slug, n = f"{base}-{n}", n + 1
        cat = it.get("category") if it.get("category") in CONFIG["categories"] else "広告"
        post = {"slug": slug, "no": next_no, "date": today, "category": cat}
        post.update({k: it[k] for k in TEXT_FIELDS})
        post.update({k: it[k] for k in META if it.get(k) and k != "category"})
        post.setdefault("source_name", it["source_url"].split("/")[2])
        post.setdefault("award", "—")
        post.setdefault("agency", "—")
        post.setdefault("production", "—")
        if it.get("videos"):
            post["videos"] = it["videos"]
        post.update({"status": "draft", "engine": it.get("by", "Genspark")})
        save_original(slug, post)
        posts.append(post)
        by_slug[slug] = post
        by_url[norm_url(post["source_url"])] = post
        next_no += 1
        added += 1
        notes = check(post)
        print(f"No.{post['no']}: 下書きに追加 {post['title']}" + (f"　要確認: {', '.join(notes)}" if notes else ""))
    POSTS_PATH.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"done: 新しい下書き {added} 本／修正案 {proposed} 本／スキップ {skipped} 本")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("使い方: python scripts/import_inbox.py data/inbox/ファイル名.json")
    main(sys.argv[1])
