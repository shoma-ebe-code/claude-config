#!/bin/bash
# SessionStart hook: CLAUDE.local.md の読み込みと staging log の通知

# settings.json の JSON 構文チェック
SETTINGS="$HOME/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
  if ! python3 -m json.tool "$SETTINGS" > /dev/null 2>&1; then
    echo "⚠️  settings.json が壊れています。セッション設定がスキップされています。"
    echo "   修正してください: $SETTINGS"
  fi
fi

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

# content-pipeline の日常タスクリマインド
CP_DIR="$HOME/content-pipeline"
if [ -d "$CP_DIR" ]; then
  TODAY=$(date +%Y-%m-%d)
  REMINDERS=""

  # 未確認の朝レポート
  REPORT="$CP_DIR/reports/${TODAY}.md"
  if [ -f "$REPORT" ]; then
    STATUS=$(grep "ステータス:" "$REPORT" 2>/dev/null | head -1 | sed 's/.*: //')
    REMINDERS="${REMINDERS}\n- 朝レポート: ${STATUS} (reports/${TODAY}.md)"
  fi

  # 未投稿のツイート下書き
  TWEETS=$(ls "$CP_DIR/drafts/tweets/"*.md 2>/dev/null | wc -l)
  if [ "$TWEETS" -gt 0 ]; then
    REMINDERS="${REMINDERS}\n- X投稿候補: ${TWEETS}件 (drafts/tweets/)"
  fi

  # 公開待ち記事
  QUEUE_ZEN=$(find "$CP_DIR/publish_queue/zenn" -name "*.md" 2>/dev/null | wc -l)
  QUEUE_SUB=$(find "$CP_DIR/publish_queue/substack" -name "*.md" 2>/dev/null | wc -l)
  if [ "$((QUEUE_ZEN + QUEUE_SUB))" -gt 0 ]; then
    REMINDERS="${REMINDERS}\n- 公開待ち: Zenn ${QUEUE_ZEN}本 / Substack ${QUEUE_SUB}本"
  fi

  if [ -n "$REMINDERS" ]; then
    echo ""
    echo "📋 content-pipeline 日常タスク:"
    echo -e "$REMINDERS"
  fi
fi

exit 0
