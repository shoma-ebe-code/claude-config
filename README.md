# claude-config — Claude Code グローバル設定

SREエンジニア16年の実務経験をベースに設計した、Claude Code（`~/.claude/`）のグローバル設定一式。

「場当たりルールの積み上げ」から「設計された憲法」へ移行した記録でもある。

## 設計思想

詳細は Zenn 記事を参照: [Claude Code の設定を「設計」する — 場当たりルールからV2憲法へのリビルド記](https://zenn.dev/ojt/articles/2026-04-01-claude-code-v2-constitution)

- **AI = 高価なCPU** — 検索・計算・パース等のトイルはPython/Shell/MCPに委任。AIには判断と創造だけやらせる
- **コンテキストは負債** — 設定ファイルもセッション状態もトークンを消費する。最小限に保つ
- **5層アーキテクチャ** — L5(Meta) → L4(Validation) → L3(Creative) → L2(Skill) → L1(Infra) の責務分離

## ファイル構成

```
~/.claude/
├── CLAUDE.md                  # V2設計憲法（コア設定）
├── coding-standards.md        # コーディング規約（全プロジェクト共通）
├── known-failures.md          # コマンド失敗パターン集
│
├── commands/                  # スラッシュコマンド
│   ├── confirm.md             #   /confirm — リポジトリ健全性チェック
│   ├── learn.md               #   /learn — ナレッジ保存
│   ├── new-repo.md            #   /new-repo — 新規リポジトリセットアップ
│   ├── optimize-global.md     #   /optimize-global — グローバル設定最適化
│   ├── post-mortem.md         #   /post-mortem — ポストモーテム作成
│   ├── promote.md             #   /promote — ローカル知見のグローバル昇格
│   ├── runbook-template.md    #   /runbook-template — Runbook作成
│   └── weekly-review.md       #   /weekly-review — 週次レビュー
│
├── hooks/                     # イベントフック
│   ├── session-start.sh       #   セッション開始時の引き継ぎ・リマインド
│   ├── stop-hook.sh           #   セッション終了時の音声通知
│   ├── validate-command.sh    #   危険コマンドのブロック
│   ├── auto-approve-bash.sh   #   安全なBashコマンドの自動承認
│   ├── log-bash-approval.sh   #   承認パターンの学習記録
│   ├── log-bash-failure.sh    #   失敗パターンの記録
│   └── post-tool-use.sh       #   .tfファイル編集後のterraform fmt自動実行
│
├── scripts/                   # L1/L4 ツール
│   ├── cost-report.py         #   トークンコスト集計・予算チェック
│   ├── health-check.py        #   リポジトリ健全性チェック
│   └── lint-ai-style.py       #   AI臭い表現のスコアリング
│
├── templates/                 # 新規リポジトリ用テンプレート
│   ├── base/                  #   汎用テンプレート
│   └── sre/                   #   SRE向けテンプレート
│
└── statusline.py              # ステータスライン表示
```

## 特徴

### トークン経済学
設定ファイルはセッション開始時に毎回読み込まれる。肥大化するとそれだけで予算を圧迫する。このリポジトリでは設定の総量を最小限に保ち、詳細はスクリプトやテンプレートに分離している。

### known-failures.md
Bash実行前に過去の失敗パターンを確認する仕組み。WSL2環境特有のハマりポイント（git.exe問題、DNS障害、hookブロック等）を集約している。

### hooks による自動化
- セッション開始時に前回の引き継ぎメモと未完了タスクを自動表示
- 危険なコマンド（`git push --force`、`npm install -g` 等）を自動ブロック
- 安全なBashコマンドパターンを学習して自動承認

### lint-ai-style.py
AI生成テキストにありがちな表現（「〜を確保する」「包括的な」等）をスコアリングし、人間らしい文章に近づける。

## 環境

- WSL2 (Ubuntu) 上で運用
- Git: WSL側の git を使用（HTTPS）
- Node.js: NVM経由

## 関連記事

- [Claude Code × Terraform — 「任せすぎ」を防ぐ3つの考え方](https://zenn.dev/ojt/articles/claude-code-terraform-guardrails)
- [terraform plan をClaudeに解析させる4つのプロンプトパターン](https://zenn.dev/ojt/articles/2026-03-30-terraform-plan-claude-prompt-patterns)
- [Claude Code の設定を「設計」する — V2憲法へのリビルド記](https://zenn.dev/ojt/articles/2026-04-01-claude-code-v2-constitution)
