"""② 下書き：候補記事の本文を読み、Claude APIで解剖記事を書いて data/posts.json に追加する。
環境変数 ANTHROPIC_API_KEY が必要。"""
import datetime
import html
import json
import os
import pathlib
import re
import urllib.request

import anthropic

from web import article_text, fetch_html

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
PROMPT = (ROOT / "prompts/kaibo.md").read_text(encoding="utf-8")
POSTS_PATH = ROOT / "data/posts.json"


def page_text(url):
    return article_text(fetch_html(url))


def slugify(url):
    return "p" + re.sub(r"[^0-9a-z]+", "-", url.lower())[-40:].strip("-")


def ask(client, cand, body):
    prompt = (PROMPT.replace("{categories}", " / ".join(CONFIG["categories"]))
              .replace("{title}", cand["title"]).replace("{url}", cand["link"]).replace("{body}", body))
    msg = client.messages.create(model=CONFIG["model"], max_tokens=3000,
                                 messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in msg.content if b.type == "text")
    return json.loads(text[text.find("{"): text.rfind("}") + 1])


def main():
    cands = json.loads((ROOT / "data/candidates.json").read_text(encoding="utf-8"))
    posts = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    client = anthropic.Anthropic()
    seen_path = ROOT / "data/seen.json"
    seen = json.loads(seen_path.read_text(encoding="utf-8")) if seen_path.exists() else []
    next_no = max((p["no"] for p in posts), default=0) + 1
    added = 0
    for cand in cands:
        if added >= CONFIG["posts_per_run"]:
            break
        try:
            data = ask(client, cand, page_text(cand["link"]))
        except Exception as e:
            print(f"skip {cand['link']}: {e}")
            continue
        seen.append(cand["link"])  # 一度読んだ記事は、次回から候補に入れない
        if data.get("skip"):
            print(f"not a work: {cand['title']}")
            continue
        data.update({
            "slug": slugify(cand["link"]),
            "no": next_no,
            "date": datetime.date.today().isoformat(),
            "source_name": cand.get("source") or cand["link"].split("/")[2],
            "source_url": cand["link"],
            "status": "published" if CONFIG["auto_publish"] else "draft",
        })
        posts.append(data)
        next_no += 1
        added += 1
        print(f"added No.{data['no']}: {data['title']}")
    POSTS_PATH.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    seen_path.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
