"""試験：既存の記事3本を、2通りの書き方で書いて data/trial.json に保存する。
  ・エンジン版：髙橋俊臣の文章エンジン（書く → 赤入れ → 書き直す）
  ・ふつうのAI版：考え方・文体のルールを渡さずに、同じ型で1回だけ書かせたもの
どちらがどちらかは伏せて、テストページ（docs/test.html）にA・Bとして並べる。
公開中の記事は書き換えない。環境変数 ANTHROPIC_API_KEY が必要。"""
import json
import pathlib
import random

import anthropic

from draft import page_text
from engine import CONFIG, PROMPTS, call, fill, make_post

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE = (PROMPTS / "baseline.md").read_text(encoding="utf-8")
PREFER = CONFIG.get("trial_slugs", ["zebra-kaku", "kao-merit"])
HOW_MANY = 3


def main():
    posts = json.loads((ROOT / "data/posts.json").read_text(encoding="utf-8"))
    by_slug = {p["slug"]: p for p in posts}
    order = [by_slug[s] for s in PREFER if s in by_slug]
    order += [p for p in sorted(posts, key=lambda x: -x["no"]) if p["slug"] not in PREFER]
    client = anthropic.Anthropic()
    out = []
    for p in order:
        if len(out) >= HOW_MANY:
            break
        print(f"No.{p['no']}: {p.get('work') or p['title']}")
        try:
            body = page_text(p["source_url"])
            others = [x for x in posts if x is not p]
            engine = make_post(client, p.get("work") or p["title"], p["source_url"], body, others)
            if engine.get("skip") or not engine.get("points"):
                print("  出典から書けなかったので、別の記事にします")
                continue
            plain = call(client, "", fill(BASELINE, title=p.get("work") or p["title"], url=p["source_url"], body=body))
        except Exception as e:
            print(f"  skip: {e}")
            continue
        pick = lambda d: {k: d.get(k, "") for k in ("title", "oneliner", "about", "points")}
        out.append({"slug": p["slug"], "no": p["no"], "work": p.get("work", ""), "client": p.get("client", ""),
                    "image": p.get("image", ""), "source_url": p["source_url"],
                    "engine": pick(engine), "plain": pick(plain), "engine_is": random.choice("AB")})
    (ROOT / "data/trial.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"trial: {len(out)} 本")


if __name__ == "__main__":
    main()
