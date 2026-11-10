"""学ぶ：髙橋が管理ページやサイト上で記事を手直ししたら、
「AIが書いた元の文 → 髙橋が直した文」の組を data/edits.json に記録する。
記録した組は、次に記事を書くとき「髙橋が実際に直した例」としてエンジンに渡される（engine.py）。
Claudeは呼ばないので料金はかからない。"""
import datetime
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIELDS = ("title", "oneliner", "about", "points")


def load(name, default):
    path = ROOT / "data" / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def main():
    posts = load("posts.json", [])
    originals = load("originals.json", {})
    edits = load("edits.json", [])
    known = {(e["slug"], e["field"]): e for e in edits}
    added = 0
    for p in posts:
        orig = originals.get(p["slug"])
        if not orig:
            continue
        for f in FIELDS:
            ai, human = (orig.get(f) or "").strip(), (p.get(f) or "").strip()
            if not ai or not human or ai == human:
                continue
            old = known.get((p["slug"], f))
            if old:
                if old["human"] != human:  # さらに直したら、新しいほうで上書き
                    old["human"], old["date"] = human, datetime.date.today().isoformat()
                    added += 1
                continue
            entry = {"slug": p["slug"], "no": p["no"], "field": f, "ai": ai, "human": human,
                     "date": datetime.date.today().isoformat()}
            edits.append(entry)
            known[(p["slug"], f)] = entry
            added += 1
    (ROOT / "data/edits.json").write_text(json.dumps(edits, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"edits: {len(edits)} 件（今回 {added} 件を記録）")


if __name__ == "__main__":
    main()
