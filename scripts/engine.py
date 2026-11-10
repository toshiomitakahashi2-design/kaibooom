"""髙橋俊臣の文章エンジン。
1本の記事を「書く → 髙橋の目で赤入れ → 書き直す」の3段階でつくる。
考え方・文体・AI臭のルールは prompts/voice/ の3つのファイルに書いてある。"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
PROMPTS = ROOT / "prompts"

VOICE = "\n\n---\n\n".join(
    (PROMPTS / "voice" / name).read_text(encoding="utf-8")
    for name in ("kangaekata.md", "buntai.md", "ai-shu.md")
)
WRITE = (PROMPTS / "write.md").read_text(encoding="utf-8")
CRITIQUE = (PROMPTS / "critique.md").read_text(encoding="utf-8")
REWRITE = (PROMPTS / "rewrite.md").read_text(encoding="utf-8")

TEXT_FIELDS = ("title", "oneliner", "about", "points")

# なるべく使わない定番ワード（5本につき2回くらいまで）
BUZZ = ["刺さる", "刺さり", "エモい", "世界観", "インサイト", "バズる", "バズっ", "ストーリーテリング", "寄り添", "共感を呼"]
# 機械的に見つけられるAI臭。残っていたら、もう一度だけ書き直させる
LINT = ["見事に", "見事な", "絶妙", "巧みに", "巧みな", "秀逸", "圧巻", "唯一無二", "と言えるでしょう", "といえるでしょう",
        "——", "してみよう", "してみましょう", "マネでき", "真似でき", "盗め", "本文には", "記事からは", "私の読みでは",
        "胸を打"]


def fill(template, **values):
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value))
    return template


def call(client, system, user, max_tokens=3000, model=None):
    args = {"model": model or CONFIG.get("model_write") or CONFIG["model"], "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": user}]}
    if system:
        args["system"] = system
    msg = client.messages.create(**args)
    text = "".join(b.text for b in msg.content if b.type == "text")
    return json.loads(text[text.find("{"): text.rfind("}") + 1])


def post_text(post):
    parts = [post.get(k, "") for k in ("title", "oneliner", "about", "points", "steal")]
    parts += [s.get("body", "") for s in post.get("steps", [])]
    return " ".join(parts)


def buzz_count(text):
    return sum(text.count(w) for w in BUZZ)


def buzz_rule(posts):
    """直近5本で定番ワードを何回使ったかを数え、今回の使い方を決める。"""
    recent = sorted(posts, key=lambda p: p["no"])[-5:]
    used = sum(buzz_count(post_text(p)) for p in recent)
    words = "「刺さる」「エモい」「世界観」「インサイト」「バズる」「ストーリーテリング」「寄り添う」「共感を呼ぶ」"
    if used >= 2:
        return f"{words}は、今回の記事では使いません（最近の記事ですでに使っているため）。"
    return (f"{words}は、基本的に使いません。"
            "この広告が特にその点で優れていて、その言葉でなければ言えないときだけ、記事全体で1回だけ使えます。")


def recent_titles(posts, n=8):
    recent = sorted(posts, key=lambda p: p["no"])[-n:]
    return "\n".join(f"- {p['title']}" for p in recent) or "（まだありません）"


def edit_examples(n=6, limit=400):
    """髙橋が管理ページで実際に直した例を、書き直しの手本として渡す。"""
    path = ROOT / "data/edits.json"
    if not path.exists():
        return ""
    edits = json.loads(path.read_text(encoding="utf-8"))[-n:]
    if not edits:
        return ""
    lines = ["", "# 髙橋が実際に直した例（この直し方にならう）"]
    for e in edits:
        lines.append(f"AIの文：{e['ai'][:limit]}")
        lines.append(f"髙橋の文：{e['human'][:limit]}")
        lines.append("")
    return "\n".join(lines)


def lint(data):
    text = " ".join(str(data.get(k, "")) for k in TEXT_FIELDS)
    return [w for w in LINT if w in text]


def make_post(client, title, url, body, posts, log=print):
    """戻り値: 記事のデータ（dict）。記事にしない場合は {"skip": True}。"""
    draft = call(client, VOICE, fill(
        WRITE, recent_titles=recent_titles(posts), buzz_rule=buzz_rule(posts),
        categories=" / ".join(CONFIG["categories"]), title=title, url=url, body=body))
    if draft.get("skip"):
        return draft

    draft_json = json.dumps(draft, ensure_ascii=False, indent=2)
    review = call(client, VOICE, fill(CRITIQUE, body=body, draft=draft_json), max_tokens=2500,
                  model=CONFIG.get("model_critique"))
    issues, missing = review.get("issues", []), review.get("missing", "")
    log(f"  赤入れ {len(issues)} 件" + ("＋足りない視点あり" if missing else ""))

    final = draft
    for attempt in range(2):
        found = lint(final)
        if attempt == 0 and not issues and not missing and not found:
            break
        if attempt == 1 and not found:
            break
        note = ""
        if found:
            note = "- 次の言葉・言い回しは使いません。別の書き方に直します：" + "、".join(f"「{w}」" for w in found)
            log(f"  禁止の言い回しを検出: {found}")
        final = call(client, VOICE, fill(
            REWRITE, lint_note=note, edit_examples=edit_examples(), body=body,
            draft=json.dumps(final, ensure_ascii=False, indent=2),
            issues=json.dumps(issues, ensure_ascii=False, indent=2) if attempt == 0 else "（前回の赤入れは反映済み）",
            missing=(missing if attempt == 0 else "") or "（なし）"))
    final["points"] = re.sub(r"\n{3,}", "\n\n", str(final.get("points", "")).strip())
    return final


def save_original(slug, data):
    """AIが書いたままの文を残しておく。あとで髙橋の手直しと比べるため。"""
    path = ROOT / "data/originals.json"
    originals = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    originals[slug] = {k: data.get(k, "") for k in TEXT_FIELDS}
    path.write_text(json.dumps(originals, ensure_ascii=False, indent=2), encoding="utf-8")
