#!/bin/bash
# PostToolUse hook: .tfファイル編集後にterraform fmt を自動実行

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Edit/Writeツールで.tfファイルが変更された場合のみ実行
if [[ "$TOOL" != "Edit" && "$TOOL" != "Write" ]]; then
  exit 0
fi

if [[ "$FILE" != *.tf ]]; then
  exit 0
fi

echo "🔍 .tf変更を検知 → terraform fmt を実行します" >&2

# Windows/WSL 両対応のパス解決
# WSLパス（/mnt/c/...）の場合はWindowsパスに変換、それ以外はそのまま使う
if command -v wslpath &>/dev/null && [[ "$FILE" == /mnt/* ]]; then
  WIN_FILE=$(wslpath -w "$FILE" 2>/dev/null)
else
  WIN_FILE="$FILE"
fi

if [ -n "$WIN_FILE" ]; then
  # terraform fmt: ファイル単体をフォーマット（initなしで動作）
  cmd.exe /c "terraform fmt \"${WIN_FILE}\"" 2>&1 || true
fi

exit 0
