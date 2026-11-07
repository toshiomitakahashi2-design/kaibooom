"""④ 公開：公開済みの記事をテンプレートに流し込み、docs/index.html を作る。"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    posts = json.loads((ROOT / "data/posts.json").read_text(encoding="utf-8"))
    live = [p for p in posts if p.get("status", "published") == "published"]
    data = json.dumps(live, ensure_ascii=False).replace("</", "<\\/")
    page = (ROOT / "site/template.html").read_text(encoding="utf-8").replace("__POSTS__", data)
    out = ROOT / "docs/index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")
    (ROOT / "docs/admin.html").write_text((ROOT / "site/admin.html").read_text(encoding="utf-8"), encoding="utf-8")
    print(f"built {out} with {len(live)} posts")


if __name__ == "__main__":
    main()
