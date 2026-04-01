#!/bin/bash
# Stop Hook ラッパー
# stop_hook_active が true のときは即終了（無限ループ防止）
if [ "${stop_hook_active}" = "true" ]; then
  exit 0
fi

/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
  -File 'C:\Users\ojita\.claude\hooks\play-random-sound.ps1'
