# KAIBO（広告解剖）自動化パイプライン 試作版

毎週月曜の朝7時に、次の流れが全自動で動きます。

1. **集める** `scripts/collect.py`：AdverTimes.のRSSから、広告・デザイン関連の記事を拾います
2. **下書き** `scripts/draft.py`：Claude APIが記事を読み、解剖記事を書きます（作品でないニュースは自動でスキップ）
3. **チェック**：試作版ではオフです（`config.json` の `auto_publish` を `false` にするとオンになります）
4. **公開** `scripts/build.py`：サイト `docs/index.html` を作り、GitHub Pagesに公開します

## 調整できるところ
- `config.json`：拾うサイト（feeds）、キーワード、1回に書く本数、使うモデル
- `prompts/kaibo.md`：記事の書き方（文体や型）
- `site/template.html`：サイトのデザイン

## 動かし方（はじめての人向け）
GitHub Pagesへの公開手順は、別途チャットで1ステップずつ案内します。
必要なもの：GitHubアカウント、Anthropic APIキー（console.anthropic.com で発行）
