#!/bin/bash
# SessionStart hook: CLAUDE.local.md の読み込みと staging log の通知

# カレントディレクトリの CLAUDE.local.md を読む
# /mnt/c/ 配下のパスは Windows パスに変換して確認
LOCAL_MD=""
if [ -f "$PWD/CLAUDE.local.md" ]; then
  LOCAL_MD="$PWD/CLAUDE.local.md"
fi

if [ -n "$LOCAL_MD" ]; then
  cat "$LOCAL_MD"
fi

# known-failures-staging.log にエントリがあれば通知
STAGING="$HOME/.claude/known-failures-staging.log"
if [ -s "$STAGING" ]; then
  ENTRY_COUNT=$(grep -c '^---$' "$STAGING" 2>/dev/null || echo "?")
  echo ""
  echo "⚠️  known-failures-staging.log に ${ENTRY_COUNT} 件の失敗ログがあります。"
  echo "   内容を確認して known-failures.md への昇格を検討してください: ~/.claude/known-failures-staging.log"
fi

exit 0
