#!/bin/bash
# PreToolUse hook: Bashコマンドの実行前バリデーション

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$COMMAND" ] && exit 0

# 各チェックで block() を呼ぶ
block() { echo "Blocked: $1" >&2; exit 2; }

# --- compound command 対応: &&, ||, ;, | で分割してチェック ---
SUBCMDS=$(echo "$COMMAND" | tr ';&|' '\n')

# 破壊的コマンド（rm -rf, dd, mkfs, fdisk, parted, shutdown系, crontab -r）
echo "$SUBCMDS" | grep -qE '(^|\s)(rm\s+-r[f]|rm\s+-fr|dd\s+.*of=/dev/|mkfs|fdisk|parted|shutdown|reboot|halt|poweroff|crontab\s+-r)\b' \
  && block "destructive command detected"

# git: force push, global/system config
echo "$COMMAND" | grep -qE 'git\s+push\s+(--force|-f)\b' && block "git push --force"
echo "$COMMAND" | grep -qE 'git\s+config\s+(--global|--system)' && block "git config --global/--system"

# 本番環境への直接アクセス
echo "$COMMAND" | grep -qiE '(--profile[= ](prod|production)|--context[= ](prod|production)|workspace\s+select\s+(prod|production)|ssh\s+(prod|production)|kubectl.*--context.*(prod|production))' \
  && block "production environment access"

# 秘密情報・認証情報
echo "$COMMAND" | grep -qE '(cat|less|more|head|tail)\s+.*\.(pem|key|p12|pfx)' && block "reading secret files"
echo "$COMMAND" | grep -qE 'aws\s+.*--query.*SecretAccessKey|printenv.*AWS_SECRET' && block "exposing AWS credentials"

# パッケージのグローバルインストール
echo "$COMMAND" | grep -qE '(npm\s+(install|i)\s+(-g|--global)|gem\s+install\s)' && block "global package install"

# GitHub CLI 破壊的操作
echo "$COMMAND" | grep -qE 'gh\s+(repo|release|pr|issue)\s+delete' && block "gh destructive operation"

# その他の危険パターン
echo "$COMMAND" | grep -qF ':(){ :|:&' && block "fork bomb"
echo "$COMMAND" | grep -qE 'chmod\s+.*\+s' && block "chmod +s (setuid/setgid)"
echo "$COMMAND" | grep -qE 'history\s+-[cw]|>\s*~?\/?(\.bash_history|\.zsh_history)' && block "clearing shell history"

exit 0
