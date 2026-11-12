"""学ぶ（その2）：手直しの記録（data/edits.json）から、髙橋の直し方の法則をまとめ直して
prompts/voice/learned.md に書く。次の記事から、エンジンがこの法則を必ず読む。
- 前回まとめてから新しい手直しが MIN_NEW 件以上たまったときだけ動く（料金の節約）
- --force をつけると、件数に関係なくまとめ直す
環境変数 ANTHROPIC_API_KEY が必要。"""
import datetime
import json
import pathlib
import sys

import anthropic

from engine import CONFIG, LEARNED_PATH, PROMPTS, changed_sentences, fill

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "data/learned_state.json"
MIN_NEW = 3
MAX_CHARS = 30000


def main():
    edits_path = ROOT / "data/edits.json"
    edits = json.loads(edits_path.read_text(encoding="utf-8")) if edits_path.exists() else []
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"count": 0}
    new = len(edits) - state.get("count", 0)
    if not edits or (new < MIN_NEW and "--force" not in sys.argv):
        print(f"手直し {len(edits)} 件（前回から {new} 件）。{MIN_NEW} 件たまったら法則をまとめ直します")
        return
    blocks = []
    for e in edits[::-1]:  # 新しい手直しから順に
        pairs = changed_sentences(e["ai"], e["human"])
        if not pairs:
            continue
        lines = [f"## No.{e['no']}（{ {'title': '見出し', 'oneliner': 'ひとこと', 'about': 'なんの広告？', 'points': 'アイデア、ポイント'}.get(e['field'], e['field']) }）"]
        for ai, human in pairs:
            lines.append(f"- {ai or '（なし）'}")
            lines.append(f"+ {human or '（削除）'}")
        blocks.append("\n".join(lines))
    text = ""
    for b in blocks:
        if len(text) + len(b) > MAX_CHARS:
            break
        text += b + "\n\n"
    prompt = fill((PROMPTS / "distill.md").read_text(encoding="utf-8"),
                  count=len(edits), date=datetime.date.today().isoformat(),
                  current=LEARNED_PATH.read_text(encoding="utf-8") if LEARNED_PATH.exists() else "（まだありません）",
                  edits=text)
    msg = anthropic.Anthropic().messages.create(
        model=CONFIG.get("model_write") or CONFIG["model"], max_tokens=8000,
        messages=[{"role": "user", "content": prompt}])
    out = "".join(b.text for b in msg.content if b.type == "text").strip()
    if not out.startswith("#"):
        out = out[out.find("#"):] if "#" in out else ""
    if len(out) < 100:
        raise SystemExit("法則をまとめられませんでした。前の learned.md をそのまま残します。")
    LEARNED_PATH.write_text(out + "\n", encoding="utf-8")
    STATE.write_text(json.dumps({"count": len(edits), "date": datetime.date.today().isoformat()}, ensure_ascii=False), encoding="utf-8")
    print(f"法則をまとめ直しました（手直し {len(edits)} 件から）")


if __name__ == "__main__":
    main()
