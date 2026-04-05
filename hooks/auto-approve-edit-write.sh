#!/bin/bash
# PermissionRequest hook: Edit/Write を対話セッションで自動承認
# --print モードでは hook 自体が動作しないため、サブプロセスには影響しない

cat <<'EOJSON'
{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}
EOJSON
