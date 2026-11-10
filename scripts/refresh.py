"""古い型の記事（課題・狙い・しかけ／ここを盗め／やってみよう）を、
新しい文章エンジンで「なんの広告なのか／アイデア、ポイント」の型に書き直す。
- 古い型の記事と、エンジンの古い版で書いた記事が対象。いまの版で書いた記事は二度書き直さない
- 髙橋が手直しした記事は書き直さない（手直しを消さないため）
- 写真・動画・番号・日付はそのまま残す
- 書き直す前の文章は data/legacy.json に残す
環境変数 ANTHROPIC_API_KEY が必要。"""
import json
import pathlib

import anthropic

from draft import page_text
from engine import ENGINE_VERSION, TEXT_FIELDS, make_post, save_original

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS_PATH = ROOT / "data/posts.json"
LEGACY_PATH = ROOT / "data/legacy.json"
KEEP = ("category", "title", "work", "client", "agency", "production", "award", "country", "oneliner", "about", "points")
OLD = ("steps", "steal", "challenge")


def main():
    posts = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    legacy = json.loads(LEGACY_PATH.read_text(encoding="utf-8")) if LEGACY_PATH.exists() else {}
    orig_path = ROOT / "data/originals.json"
    originals = json.loads(orig_path.read_text(encoding="utf-8")) if orig_path.exists() else {}
    client = anthropic.Anthropic()
    changed = 0
    for p in sorted(posts, key=lambda x: x["no"]):
        if p.get("points") and p.get("engine", 1) >= ENGINE_VERSION:
            continue
        orig = originals.get(p["slug"])
        if p.get("points") and orig and any((orig.get(k) or "").strip() != (p.get(k) or "").strip() for k in TEXT_FIELDS):
            print(f"No.{p['no']}: 手直しがあるので、そのままにします")
            continue
        print(f"No.{p['no']}: {p['title']}")
        others = [x for x in posts if x is not p]
        try:
            data, flat = make_post(client, p.get("work") or p["title"], p["source_url"], page_text(p["source_url"]), others, with_draft=True)
        except Exception as e:
            print(f"  skip: {e}")
            continue
        if data.get("skip") or not data.get("points"):
            print("  出典から書けなかったので、そのままにします")
            continue
        if p["slug"] not in legacy:  # いちばん最初の文章だけを保管する
            legacy[p["slug"]] = {k: p[k] for k in ("title", "oneliner", "about") + OLD if k in p}
        for k in KEEP:
            if data.get(k) and not (data[k] == "—" and p.get(k)):
                p[k] = data[k]
        for k in OLD:
            p.pop(k, None)
        p["engine"] = ENGINE_VERSION
        save_original(p["slug"], p, flat)
        changed += 1
        print(f"  → {p['title']}")
        # 途中で止まっても、そこまでの分は残るように毎回保存する
        POSTS_PATH.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
        LEGACY_PATH.write_text(json.dumps(legacy, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"done: {changed} posts")


if __name__ == "__main__":
    main()
