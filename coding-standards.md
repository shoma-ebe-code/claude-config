# コーディング規約（全プロジェクト共通）

> Claude Code がコードを生成・修正する際に従うべき規約。
> プロジェクト固有の規約は各 `.clauderules` の STYLE RULES を優先する。
> 最終更新: 2026-04-02

---

## 1. Bash スクリプト

### テンプレート（新規スクリプト作成時に従う）

```bash
#!/bin/bash
# スクリプト名.sh
# 目的を1行で（例: 毎日4時にガイドを1体生成してpush）
#
# cron登録（該当する場合）:
#   0 4 * * 1-6 /path/to/script.sh >> /path/to/cron.log 2>&1

set -euo pipefail

# --- 環境初期化 ---
export NVM_DIR="/home/ojita/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# --- 定数 ---
PROJECT_DIR="/home/ojita/<project-name>"
DATE=$(date +%Y-%m-%d)
LOG_PREFIX="[${DATE} $(date +%H:%M:%S)]"

# --- 共通関数の読み込み ---
source "${PROJECT_DIR}/scripts/lib.sh"

# --- メイン処理 ---
cd "$PROJECT_DIR" || { echo "${LOG_PREFIX} ERROR: ディレクトリが見つかりません"; exit 1; }

echo "${LOG_PREFIX} ===== 処理開始 ====="

# ... 処理 ...

echo "${LOG_PREFIX} ===== 処理完了 ====="
```

### 必須ルール

- `set -euo pipefail` — 未定義変数・パイプエラーの握りつぶし防止
- 変数は `"${VAR}"` でクォート — スペース含みパスでの事故防止
- ログは `${LOG_PREFIX} INFO/WARN/ERROR:` 形式 — cron.log 解析を容易に
- エラー時は `exit 1` — 後続cronジョブの誤実行防止
- cron登録コマンドをヘッダコメントに記載

### 命名規則

| 対象 | 規則 | 例 |
|---|---|---|
| スクリプトファイル | `kebab-case.sh` | `daily-guide.sh` |
| 関数名 | `snake_case` | `run_cmd()`, `run_step()` |
| 定数 | `UPPER_SNAKE_CASE` | `PROJECT_DIR`, `LOG_PREFIX` |
| ローカル変数 | `lower_snake_case` + `local` 宣言 | `local cmd_name="$1"` |
| プロジェクトDIR | `PROJECT_DIR` に統一 | ~~`PIPELINE_DIR`~~ ~~`GUIDE_DIR`~~ |

### 成功判定: exit code だけでなく成果物を検証する

外部プロセス（`claude --print`、API呼び出し等）の結果は exit code 0 でも期待する成果物が生成されていない場合がある。
処理の成功判定は「コマンドが正常終了したか」ではなく「期待する状態になったか」で行う。

```bash
# NG: exit code だけ見る（set -e 環境では $? チェックに届かないことがある）
json=$(run_cmd "research")
if [ $? -ne 0 ] || [ -z "$json" ]; then
    exit 1
fi

# OK: || で失敗を捕捉し、成果物の存在も検証する
json=$(run_cmd "research") || { echo "ERROR: research 失敗"; exit 1; }
if [ -z "$json" ]; then
    echo "ERROR: コマンドは成功したが結果が空"
    exit 1
fi
if [ ! -f "${expected_file}" ]; then
    echo "ERROR: コマンドは成功したが成果物が生成されていない"
    exit 1
fi
```

---

### デバッグ: 最小単位でテストする

問題が発生したら「どの層が壊れているか」を特定し、その層だけを切り出してテストする。全体パイプラインを何度も動かさない。

| 疑われる層 | テスト方法 |
|---|---|
| L1: `dispatch_ops` のパース | `echo` でサンプル JSON を直接渡す（API 不要） |
| L3: モデル出力のフォーマット | API を1回だけ呼んでファイルに保存 → 以降はそのファイルをリプレイ |
| L1: cron 環境・スクリプト全体 | `--dry-run` で確認 |

全体パイプライン実行は「各層が単体で OK であることを確認した後」の最終確認に1回だけ。

---

## 2. lib.sh パターン（拡張性設計）

各リポジトリの `scripts/lib.sh` に `run_cmd()` 関数を実装する。

- コマンド検索順: `${PROJECT_DIR}/.claude/commands/` → `${HOME}/.claude/commands/`
- frontmatter の `model:` を抽出して `claude --print` に渡す
- 参照実装: `content-pipeline/scripts/lib.sh`

---

## 3. Markdown ドキュメント

| ルール | 例 |
|---|---|
| 見出しは `#` から段階的に | `# > ## > ###`（レベルを飛ばさない） |
| 1ファイル1トピック | 長くなったら分割して参照させる |
| 最終更新日を冒頭に書く | `> 最終更新: 2026-04-02` |
| TODOはチェックボックス形式 | `- [ ]` / `- [x]` |

---

## 4. Git コミット

- Conventional Commits（日本語）: `feat:` / `fix:` / `chore:` / `docs:` / `refactor:` / `security:`
- 1コミット1論理変更（複数ファイルでもOK、複数目的はNG）
- WSL側の `git` で直接実行（リモートは HTTPS）

---

## 5. 今後の拡張ルール

プロジェクト固有の規約が必要な場合は、各リポジトリの `.clauderules` の `STYLE RULES` セクションに追記する。
ここには**全リポジトリ共通**のルールのみ記載する。
