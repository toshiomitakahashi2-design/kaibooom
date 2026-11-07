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

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
PROMPT = (ROOT / "prompts/kaibo.md").read_text(encoding="utf-8")
POSTS_PATH = ROOT / "data/posts.json"


def page_text(url, limit=12000):
    req = urllib.request.Request(url, headers={"User-Agent": "KAIBO-bot/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", errors="ignore")
    raw = re.sub(r"(?is)<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>", " ", raw)
    text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def slugify(url):
    return "p" + re.sub(r"[^0-9a-z]+", "-", url.lower())[-40:].strip("-")


def ask(client, cand, body):
    prompt = (PROMPT.replace("{categories}", " / ".join(CONFIG["categories"]))
              .replace("{title}", cand["title"]).replace("{url}", cand["link"]).replace("{body}", body))
    msg = client.messages.create(model=CONFIG["model"], max_tokens=2000,
                                 messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in msg.content if b.type == "text")
    return json.loads(text[text.find("{"): text.rfind("}") + 1])


def main():
    cands = json.loads((ROOT / "data/candidates.json").read_text(encoding="utf-8"))
    posts = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    client = anthropic.Anthropic()
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
        if data.get("skip"):
            print(f"not a work: {cand['title']}")
            continue
        data.update({
            "slug": slugify(cand["link"]),
            "no": next_no,
            "date": datetime.date.today().isoformat(),
            "source_name": "AdverTimes." if "advertimes" in cand["link"] else cand["link"].split("/")[2],
            "source_url": cand["link"],
            "status": "published" if CONFIG["auto_publish"] else "draft",
        })
        posts.append(data)
        next_no += 1
        added += 1
        print(f"added No.{data['no']}: {data['title']}")
    POSTS_PATH.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
