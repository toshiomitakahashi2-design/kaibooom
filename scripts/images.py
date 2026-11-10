"""③ 画像・動画：出典ページから、メイン画像・記事内の写真・動画（YouTube / Vimeo）を探す。
画像や動画そのものはコピーせず、出典元のURLを参照して表示する（動画は公式の埋め込み）。
まだ探していない記事（media_checked がない記事）だけを対象にする。
管理ページで手で入れた画像・動画は上書きしない。"""
import json
import pathlib

from web import fetch_html, find_media

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS_PATH = ROOT / "data/posts.json"


def main():
    posts = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    for p in posts:
        if p.get("media_checked"):
            continue
        try:
            page = fetch_html(p["source_url"])
        except Exception as e:
            print(f"skip No.{p['no']}: {e}")
            continue
        cover, gallery, videos = find_media(page, p["source_url"])
        if cover and not p.get("image"):
            p["image"] = cover
        if gallery and not p.get("gallery"):
            p["gallery"] = [g for g in gallery if g != p.get("image")]
        if videos and not p.get("videos"):
            p["videos"] = videos
        p["media_checked"] = True
        print(f"No.{p['no']}: image={'○' if p.get('image') else '×'} photos={len(p.get('gallery', []))} videos={len(p.get('videos', []))}")
    POSTS_PATH.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
