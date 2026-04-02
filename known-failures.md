# known-failures — コマンド失敗パターン集

> 失敗が判明したら追記する。Bash実行前に該当パターンがないか確認する。

---

## Git操作（WSL環境）

| やりたいこと | NG | OK |
|---|---|---|
| global config変更 | `git config --global ...`（hookでブロック） | `git -c key=value` をコマンドに直接渡す |
| リモートへのpush | SSH | リモートをHTTPSに設定: `git remote set-url origin https://...` |

## hookでブロックされるコマンド

| NG | 代替 |
|---|---|
| `curl * \| bash` / `curl * \| sh` | WebFetchツール |
| `npm install -g *` | プロジェクトローカルに`npm install` |
| `git config --global *` / `--system *` | `git -c key=value` でインライン指定 |
| `git push --force *` | ユーザーに依頼 |

## Bash の `&&` チェーンと権限マッチ

allowルールはコマンド文字列の先頭でマッチする。`&&` チェーンすると先頭が変わり、マッチしない。

| やりたいこと | NG | OK |
|---|---|---|
| 別ディレクトリでgit操作 | `cd /path && git status` | `git -C /path status` |
| 複数コマンドの順次実行 | `cmd1 && cmd2`（1つのBash呼び出し） | 個別のBash呼び出しに分割する |

## WSL2: Puppeteer / Chrome起動不可

症状: `libnspr4.so: cannot open shared object file` → Chrome共有ライブラリ不足。
回避: `sharp`（libvips）でSVG→PNG変換。ブラウザ不要。
根本解決: `sudo apt install -y libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2t64 libpango-1.0-0 libcairo2`

## WSL2: 日本語フォント不在（解決済み）

`sudo apt install -y fonts-noto-cjk` + `~/.local/share/fonts/` にNoto Sans CJK JP配置済み（2026-04-02）。
再発した場合は `fc-list :lang=ja` でフォント存在を確認。

## WSL環境: .exe呼び出し不要

`git.exe`/`gh.exe`は不要。全てUbuntu側の`git`/`gh`で完結する。スクリプト生成時に`.exe`を付けない。

## Python heredocのセキュリティ誤検知

症状: `python3 << 'EOF'`内に`r'\b'`等のブレース+クォート文字列があるとClaude Code内部チェックが「expansion obfuscation」として検知。
回避: スクリプトファイルに書き出して`python3 scripts/xxx.py`で実行。ヒアドキュメントは正規表現やブレースを含まない場合のみ。

## cron自律実行（claude --print）の落とし穴

| 問題 | 対処 |
|---|---|
| プロジェクトコマンド使えない | `sed`でコマンドファイルの内容を直接プロンプトに渡す |
| NVM未ロード | スクリプト冒頭で`source "$NVM_DIR/nvm.sh"` |
| ファイル書き込み効かない | `< /dev/null` + `--permission-mode acceptEdits` + allowにWrite/Edit追加 |
| acceptEditsはBash未カバー | Bashコマンドは別途allow追加が必要 |
| WSL→PowerShell | フルパス必須・CRLF必須・日本語引数不可・`\|\| true`で失敗ガード |

## WSLのDNS障害

症状: `github.com` が解決できない → **別ターミナル（WSLセッション）を開けば通ることが多い。**
