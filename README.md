# KAIBOOOM（広告解剖）自動化パイプライン

毎週月曜の朝7時に、次の流れが全自動で動きます。

1. **集める** `scripts/collect.py`：AdverTimes.・電通報・Cannes Lions・Adweek から、広告・デザイン関連の記事を拾います
2. **学ぶ** `scripts/learn.py`：髙橋が手直しした記事があれば、「AIの文 → 髙橋の文」を記録します
3. **書く** `scripts/draft.py`：髙橋俊臣の文章エンジンが記事を書きます（作品でないニュースは自動でスキップ）
4. **写真・動画** `scripts/images.py`：出典ページから画像と動画（YouTube / Vimeo）を探します
5. **公開** `scripts/build.py`：サイト `docs/index.html` を作り、GitHub Pagesに公開します

## 髙橋俊臣の文章エンジン

`scripts/engine.py` が、1本の記事を2段階でつくります。

**フラットに書く → 髙橋らしさをスパイスとして少し効かせる**

1段階目は、落ち着いた解説文を書きます（`prompts/write.md`）。
2段階目で、作り手の目を1か所だけ入れ、評論家の席から書かれた文とAI臭のある言い回しを直します（`prompts/spice.md`）。
癖が強くなりすぎないよう、一歩引いた言い方の回数などを数えて、多すぎたらやり直します。

記事は「なんの広告なのか」「アイデア、ポイント」の2部構成です。
考え方と書き方は、次の3つのファイルに書いてあります。ここを直すと、次の記事から書き方が変わります。

- `prompts/voice/kangaekata.md`：考え方の型（作り手の席から書く、広告の見方、判断のものさし）
- `prompts/voice/buntai.md`：文体のルール（良い例・悪い例つき）
- `prompts/voice/ai-shu.md`：AI臭の禁止リスト

## 手で動かせるもの（GitHubの「Actions」タブ）

- **KAIBO test**：記事3本を「スパイスなし」と「スパイスあり」の2通りで、読みくらべページ（`/test.html`）に並べます。公開中の記事は変わりません
- **KAIBO rewrite**：古い型の記事を、新しいエンジンで書き直します。書き直す前の文章は `data/legacy.json` に残ります
- **KAIBO weekly**：毎週の自動更新を、いますぐ動かします
- **KAIBO learn**：これまでの手直しから、髙橋の直し方の法則をまとめ直します（`prompts/voice/learned.md`）

## 手直しから学ぶ流れ

1. 髙橋がサイト上で記事を直す
2. 毎週の自動更新で、「AIの文 → 髙橋の文」を記録する（`data/edits.json`）
3. 新しい手直しが3件たまるたびに、Claudeが直し方の法則をまとめ直す（`prompts/voice/learned.md`）
4. 次に書く記事から、エンジンがその法則を必ず読む。実際に直した文も手本として渡す

## 調整できるところ
- `config.json`：拾うサイト、キーワード、1回に書く本数、使うモデル
- `site/template.html`：サイトのデザイン
- 管理ページ（`/admin.html`）：記事の手直し、写真・動画の追加、公開・非公開

## 記録されるデータ
- `data/originals.json`：AIが書いたままの文
- `data/edits.json`：髙橋が直したところ（次の執筆で手本として使われます）
