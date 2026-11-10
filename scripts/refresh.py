"""既存の記事に「どんな作品？」（about）を後から足す。
- about がない記事だけを対象にする（一度足した記事は、次からは料金がかからない）
- 「本文には書かれていません」のような説明が混ざっていた記事は、解剖の本文も書き直す
環境変数 ANTHROPIC_API_KEY が必要。"""
import json
import pathlib
import re

import anthropic

from draft import ask, page_text

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS_PATH = ROOT / "data/posts.json"
META_TALK = re.compile(r"本文(には|に|で)?.{0,6}(明記|書かれて|不明|わから)|記事からは|私の読みでは")


def main():
    posts = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    client = anthropic.Anthropic()
    changed = 0
    for p in posts:
        if p.get("about"):
            continue
        try:
            data = ask(client, {"title": p["title"], "link": p["source_url"]}, page_text(p["source_url"]))
        except Exception as e:
            print(f"skip No.{p['no']}: {e}")
            continue
        if data.get("skip") or not data.get("about"):
            print(f"no about: No.{p['no']}")
            continue
        p["about"] = data["about"]
        p["country"] = data.get("country") or p.get("country", "")
        body = " ".join(s["body"] for s in p.get("steps", [])) + p.get("steal", "")
        if META_TALK.search(body) and data.get("steps"):
            p["steps"], p["steal"] = data["steps"], data.get("steal", p["steal"])
            print(f"rewrote steps: No.{p['no']}")
        changed += 1
        print(f"about added: No.{p['no']}")
    POSTS_PATH.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"done: {changed} posts")


if __name__ == "__main__":
    main()
