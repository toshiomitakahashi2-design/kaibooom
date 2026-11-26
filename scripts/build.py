"""④ 公開：公開済みの記事をテンプレートに流し込み、docs/index.html を作る。"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    posts = json.loads((ROOT / "data/posts.json").read_text(encoding="utf-8"))
    live = [p for p in posts if p.get("status", "published") == "published"]
    # 公開番号（pub_no）がまだない公開記事には、公開した順に続きの番号をつける（表示用。データには書き戻さない）
    nxt = max([p.get("pub_no") or 0 for p in posts] + [0]) + 1
    for p in sorted([p for p in live if not p.get("pub_no")], key=lambda p: (p.get("approved") or "", p["no"])):
        p["pub_no"] = nxt
        nxt += 1
    data = json.dumps(live, ensure_ascii=False).replace("</", "<\\/")
    page = (ROOT / "site/template.html").read_text(encoding="utf-8").replace("__POSTS__", data)
    out = ROOT / "docs/index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")
    # 管理ページ：サイトと同じテンプレートに、管理のしくみ（site/admin.js）を差し込む。記事は開いたあとGitHubから読む
    tpl = (ROOT / "site/template.html").read_text(encoding="utf-8")
    admin_js = (ROOT / "site/admin.js").read_text(encoding="utf-8").replace("</", "<\\/")
    admin = (tpl.replace("__POSTS__", "[]")
                .replace("<head>", '<head>\n<meta name="robots" content="noindex, nofollow">', 1)
                .replace('<script id="data"', "<script>" + admin_js + "</script>\n<script id=\"data\"", 1))
    admin = admin.replace("<title>", "<title>管理｜", 1)
    (ROOT / "docs/admin.html").write_text(admin, encoding="utf-8")
    (ROOT / "docs/admin-classic.html").write_text((ROOT / "site/admin-classic.html").read_text(encoding="utf-8"), encoding="utf-8")
    # 読みくらべ（ブラインドテスト）のページ。試験データがなければ空のページになる
    trial_path = ROOT / "data/trial.json"
    trial = json.loads(trial_path.read_text(encoding="utf-8")) if trial_path.exists() else []
    test = (ROOT / "site/test.html").read_text(encoding="utf-8")
    test = test.replace("__TRIAL__", json.dumps(trial, ensure_ascii=False).replace("</", "<\\/"))
    (ROOT / "docs/test.html").write_text(test, encoding="utf-8")
    print(f"built {out} with {len(live)} posts")


if __name__ == "__main__":
    main()
