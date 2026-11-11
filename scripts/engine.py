"""髙橋俊臣の文章エンジン。
1本の記事を「フラットに書く → 髙橋らしさをスパイスとして少し効かせる」の2段階でつくる。
基本はフラットな解説文。髙橋の考え方・文体・AI臭のルール（prompts/voice/ の3つのファイル）は、
2段階目で「作り手の目を1か所入れる」「評論家の席の文を直す」ために使う。"""
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
SPICE = (PROMPTS / "spice.md").read_text(encoding="utf-8")

TEXT_FIELDS = ("title", "oneliner", "about", "points")
# エンジンの書き方を変えたら数字を上げる。古い版で書いた記事は「KAIBO rewrite」で書き直される
ENGINE_VERSION = 4
POINTS_MAX = 480

# なるべく使わない定番ワード（5本につき2回くらいまで）
BUZZ = ["刺さる", "刺さり", "エモい", "世界観", "インサイト", "バズる", "バズっ", "ストーリーテリング", "寄り添", "共感を呼"]
# 機械的に見つけられるAI臭。残っていたら、もう一度だけ書き直させる
LINT = ["見事に", "見事な", "絶妙", "巧みに", "巧みな", "秀逸", "圧巻", "唯一無二", "と言えるでしょう", "といえるでしょう",
        "——", "してみよう", "してみましょう", "マネでき", "真似でき", "盗め", "本文には", "記事からは", "私の読みでは",
        "胸を打", "見逃せません", "学べるのは", "学びがあります", "若手のみなさん", "核だと読め",
        "審査員", "審査委員", "審査で", "講評"]
# 一歩引いた言い方。多すぎると癖が強くなるので数える
HEDGES = ["と考えます", "と思います", "と想像します", "のではないでしょうか", "かもしれません"]
HEDGE_MAX = 3
# 作例の言い回しを毎回なぞらないように、決まり文句は機械的に止める
STOCK = ["難しいのはその先です", "さほど難しくなかったのでは"]


def fill(template, **values):
    for key, value in values.items():
        template = template.replace("{" + key + "}", str(value))
    return template


def parse_json(text):
    """返ってきた文章からJSONの部分だけを取り出して読む。段落の改行がそのまま入っていても読めるようにする。"""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("JSONが見つかりません")
    return json.loads(text[start:end + 1], strict=False)


def call(client, system, user, max_tokens=8000, model=None, label=""):
    """Claudeを1回呼んでJSONを受け取る。文章が途中で切れたら、上限を倍にして1回だけやり直す。"""
    args = {"model": model or CONFIG.get("model_write") or CONFIG["model"], "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": user}]}
    if system:
        args["system"] = system
    for attempt in range(2):
        msg = client.messages.create(**args)
        text = "".join(b.text for b in msg.content if b.type == "text")
        try:
            return parse_json(text)
        except ValueError as e:
            stop = getattr(msg, "stop_reason", "?")
            kinds = [b.type for b in msg.content]
            used = getattr(getattr(msg, "usage", None), "output_tokens", "?")
            detail = f"{label}: {e} / stop_reason={stop} / blocks={kinds} / output_tokens={used} / text={text[:150]!r}"
            if attempt == 0 and stop == "max_tokens":
                print(f"  途中で切れたので、上限を増やしてやり直します（{label}）")
                args["max_tokens"] = max_tokens * 2
                continue
            raise RuntimeError(detail) from None


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
    text = " ".join(str(data.get(k, "")) for k in ("oneliner", "about", "points"))
    return [w for w in LINT + STOCK if w in text]


def sentences(text):
    return [x.strip() for x in re.split(r"(?<=[。？])|\n+", str(text)) if x.strip()]


ENDINGS = re.compile(r"(ました|ません|ます|でした|です)。$")


def ending_run(text):
    """同じ文末がいちばん長く続いた回数と、その文末。"""
    ends = [(ENDINGS.search(s).group(1) if ENDINGS.search(s) else None) for s in sentences(text)]
    best, word, run = 0, "", 0
    for i, e in enumerate(ends):
        run = run + 1 if e and i and e == ends[i - 1] else (1 if e else 0)
        if run > best:
            best, word = run, e
    return best, word


def taigen_count(text):
    """体言止め（ひらがな以外で終わる文）の数。かぎかっこで終わる文は数えない。"""
    return sum(1 for x in sentences(text) if re.search(r"[^ぁ-ん」）)？?!！]。$", x))


POLITE_END = re.compile(r"(ます|です|ました|ません|でした|ますか|ですか|でしょうか)[。？]?[」）)]?$")


def blunt_paragraph_ends(text):
    """段落の最後の文が「です・ます」で終わっていない段落（体言止めや言い切りで終わる段落）の、最後の文。"""
    out = []
    for para in re.split(r"\n{2,}", str(text).strip()):
        ss = sentences(para)
        if ss and not POLITE_END.search(ss[-1]):
            out.append(ss[-1])
    return out


SPICE_ENDS = ["と想像します", "と考えます", "と思います", "はずです", "ように見えます", "かもしれません"]


def hedge_ban(n=4):
    """最近の記事の「作り手の目」で2回以上使われた語尾は、今回は使わせない。"""
    path = ROOT / "data/originals.json"
    if not path.exists():
        return []
    items = [" ".join(v["spice"]) for v in json.loads(path.read_text(encoding="utf-8")).values() if v.get("spice")][-n:]
    return [w for w in SPICE_ENDS if sum(w in x for x in items) >= 2]


def spice_sentences(draft, final):
    """スパイスで新しく入った文（下書きにはなかった文）。"""
    before = set(sentences(draft.get("points", "")))
    return [x for x in sentences(final.get("points", "")) if x not in before]


def recent_spice(n=5):
    """最近の記事で入れた「作り手の目」。同じ切り口のくり返しを避けるために渡す。"""
    path = ROOT / "data/originals.json"
    if not path.exists():
        return "（まだありません）"
    items = [v["spice"] for v in json.loads(path.read_text(encoding="utf-8")).values() if v.get("spice")][-n:]
    return "\n".join("- " + " ".join(x) for x in items) or "（まだありません）"


def hedge_count(data):
    text = str(data.get("about", "")) + str(data.get("points", ""))
    return sum(text.count(w) for w in HEDGES)


def write_flat(client, title, url, body, posts):
    """1段階目：フラットな解説文を書く。記事にしない場合は {"skip": True}。"""
    return call(client, "", fill(
        WRITE, recent_titles=recent_titles(posts), buzz_rule=buzz_rule(posts),
        categories=" / ".join(CONFIG["categories"]), title=title, url=url, body=body), label="書く")


def add_spice(client, draft, body, log=print):
    """2段階目：髙橋らしさを少しだけ効かせる。癖が強すぎたり、禁止の言い回しが残ったら1回だけやり直す。"""
    final, note = draft, ""
    banned = hedge_ban()
    ban_note = ("\n今回は、最近の記事で続いている次の語尾を使いません：" + "、".join(f"「〜{w}」" for w in banned)) if banned else ""
    for attempt in range(3):
        final = call(client, VOICE, fill(
            SPICE, lint_note=note, edit_examples=edit_examples(), recent_spice=recent_spice(), hedge_ban=ban_note, body=body,
            draft=json.dumps(draft, ensure_ascii=False, indent=2)), label="スパイス")
        found, hedges = lint(final), hedge_count(final)
        before, after = len(str(draft.get("points", ""))), len(str(final.get("points", "")))
        too_long = after > max(before * 1.1, 1) or after > POINTS_MAX
        run, word = ending_run(final.get("points", ""))
        used_ban = [w for w in banned if any(w in s for s in spice_sentences(draft, final))]
        taigen = taigen_count(final.get("points", ""))
        blunt = blunt_paragraph_ends(final.get("points", ""))
        if not found and hedges <= HEDGE_MAX and not too_long and run < 3 and not used_ban and taigen >= 1 and not blunt:
            break
        notes = []
        if blunt:
            notes.append("- 前回は、段落の最後の文が体言止め（または言い切り）でした：" + "、".join(f"「{b}」" for b in blunt)
                         + "。段落の最後は「です・ます」で終えます。体言止めは段落の途中に移します。")
            log(f"  段落の最後が体言止め: {len(blunt)}か所")
        if taigen == 0:
            notes.append("- 前回は体言止めが1回もありませんでした。「大切なのは、体験。」のような一文を2〜3回入れます（続けては使いません）。")
            log("  体言止めがなかった")
        if run >= 3:
            notes.append(f"- 前回は「〜{word}。」で終わる文が{run}文続きました。同じ文末は2文までにします。")
            log(f"  同じ文末が続いた: 〜{word}。×{run}")
        if used_ban:
            notes.append("- 前回は、使わないと決めた語尾を使いました：" + "、".join(f"「〜{w}」" for w in used_ban))
            log(f"  続いている語尾を使った: {used_ban}")
        if too_long:
            notes.append(f"- 前回は points が長すぎました（下書き {before}字 → {after}字）。{min(before, POINTS_MAX - 30)}字以内にします。")
            log(f"  長くなりすぎ: {before}字 → {after}字")
        if found:
            notes.append("- 次の言い回しは使いません。別の書き方に直します：" + "、".join(f"「{w}」" for w in found))
            log(f"  禁止の言い回しを検出: {found}")
        if hedges > HEDGE_MAX:
            notes.append(f"- 前回は一歩引いた言い方（〜と考えます、〜と思います など）が{hedges}回あり、癖が強すぎました。全体で2回までにします。")
            log(f"  一歩引いた言い方が多すぎ: {hedges}回")
        note = "\n# 前回の失敗（今回は必ず直す）\n" + "\n".join(notes) + "\n"
    for k, v in draft.items():  # クレジットなど、スパイスで欠けた項目は下書きから補う
        final.setdefault(k, v)
    final["points"] = re.sub(r"\n{3,}", "\n\n", str(final.get("points", "")).strip())
    return final


def make_post(client, title, url, body, posts, log=print, with_draft=False):
    """戻り値: 記事のデータ（dict）。記事にしない場合は {"skip": True}。
    with_draft=True のときは (記事, スパイス前の下書き) の組を返す。"""
    log(f"  出典の本文 {len(body)} 字")
    draft = write_flat(client, title, url, body, posts)
    if draft.get("skip"):
        return (draft, draft) if with_draft else draft
    draft["points"] = re.sub(r"\n{3,}", "\n\n", str(draft.get("points", "")).strip())
    final = add_spice(client, draft, body, log)
    return (final, draft) if with_draft else final


def save_original(slug, data, draft=None):
    """AIが書いたままの文を残しておく。あとで髙橋の手直しと比べるため。
    draft（スパイス前の下書き）があれば、スパイスで入った文も記録する。"""
    path = ROOT / "data/originals.json"
    originals = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    originals[slug] = {k: data.get(k, "") for k in TEXT_FIELDS}
    if draft:
        originals[slug]["spice"] = spice_sentences(draft, data)
    path.write_text(json.dumps(originals, ensure_ascii=False, indent=2), encoding="utf-8")
