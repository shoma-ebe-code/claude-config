#!/bin/bash
# PreToolUse hook: Bashコマンドの実行前バリデーション

# stdinからコマンドを取得（jqがあれば使う、なければ grep で fallback）
if command -v jq &> /dev/null; then
  INPUT=$(cat)
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
else
  INPUT=$(cat)
  # jqなしでも動くよう簡易パース
  COMMAND=$(echo "$INPUT" | grep -o '"command":"[^"]*"' | head -1 | sed 's/"command":"//;s/"//')
fi

if [ -z "$COMMAND" ]; then
  exit 0
fi

# --- compound command 内の危険コマンド検出 ---
# &&, ||, ;, | で分割して各サブコマンドをチェック
DANGEROUS_PATTERNS='(^|\s)(rm\s+-rf|rm\s+-fr|git\s+push\s+--force|git\s+push\s+-f\b|dd\s+.*of=/dev/|mkfs|fdisk|shutdown|reboot|halt|poweroff|crontab\s+-r)'
if echo "$COMMAND" | tr ';&|' '\n' | grep -qE "$DANGEROUS_PATTERNS"; then
  echo "Blocked: dangerous command detected in compound expression." >&2
  exit 2
fi

# 本番環境への直接アクセスをブロック（ファイル名・スラグは対象外）
if echo "$COMMAND" | grep -qiE '(--profile[= ](prod|production)|--context[= ](prod|production)|workspace\s+select\s+(prod|production)|ssh\s+(prod|production)|kubectl.*--context.*(prod|production))'; then
  echo "Blocked: production environment access is not allowed directly. Use a dedicated deployment pipeline." >&2
  exit 2
fi

# 秘密情報の漏洩につながるコマンドをブロック
if echo "$COMMAND" | grep -qE '(cat|less|more|head|tail)\s+.*\.(pem|key|p12|pfx)'; then
  echo "Blocked: reading certificate/key files is not allowed." >&2
  exit 2
fi

# AWS認証情報の表示をブロック
if echo "$COMMAND" | grep -qE 'aws\s+.*--query.*SecretAccessKey|printenv.*AWS_SECRET'; then
  echo "Blocked: exposing AWS secret credentials is not allowed." >&2
  exit 2
fi

# git config のグローバル/システム変更をブロック
if echo "$COMMAND" | grep -qE 'git\s+config\s+(--global|--system)'; then
  echo "Blocked: git config --global/--system changes are not allowed." >&2
  exit 2
fi

# グローバルパッケージインストールをブロック
if echo "$COMMAND" | grep -qE '(npm\s+(install|i)\s+(-g|--global)|gem\s+install\s)'; then
  echo "Blocked: global package installation is not allowed." >&2
  exit 2
fi

# Fork bomb 検出
if echo "$COMMAND" | grep -qF ':(){ :|:&'; then
  echo "Blocked: fork bomb pattern detected." >&2
  exit 2
fi

# ディスク/ファイルシステム破壊コマンド
if echo "$COMMAND" | grep -qE '\bdd\s+.*of=/dev/|\bmkfs\b|\bfdisk\b|\bparted\b'; then
  echo "Blocked: disk/filesystem destructive command is not allowed." >&2
  exit 2
fi

# システムシャットダウン/再起動
if echo "$COMMAND" | grep -qE '\b(shutdown|reboot|halt|poweroff)\b'; then
  echo "Blocked: system shutdown/reboot commands are not allowed." >&2
  exit 2
fi

# crontab全削除
if echo "$COMMAND" | grep -qE 'crontab\s+-r\b'; then
  echo "Blocked: crontab -r is not allowed." >&2
  exit 2
fi

# GitHub CLI 破壊的操作
if echo "$COMMAND" | grep -qE 'gh\s+(repo|release|pr|issue)\s+delete'; then
  echo "Blocked: gh destructive operations are not allowed." >&2
  exit 2
fi

# setuid/setgid付与（chmod +s）
if echo "$COMMAND" | grep -qE 'chmod\s+.*\+s'; then
  echo "Blocked: chmod +s (setuid/setgid) is not allowed." >&2
  exit 2
fi

# シェル履歴の消去
if echo "$COMMAND" | grep -qE 'history\s+-[cw]|>\s*~?\/?(\.bash_history|\.zsh_history)'; then
  echo "Blocked: clearing shell history is not allowed." >&2
  exit 2
fi

exit 0
