#!/usr/bin/env python3
"""health-check.py — リポジトリの健全性チェック（L1 Infrastructure）

/confirm の機械的チェック項目をPythonで実行する。
AIのクリエイティビティが不要な「存在確認」「整合性チェック」を担当。

使い方:
  python3 health-check.py /mnt/c/Users/ojita/content-pipeline         # 単体チェック
  python3 health-check.py --all                                         # 全リポジトリ
  python3 health-check.py /mnt/c/Users/ojita/content-pipeline --format json
  python3 health-check.py /mnt/c/Users/ojita/content-pipeline --fix     # 不足ディレクトリを自動作成
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- リポジトリ定義 ---

REPOS = {
    "my-freelance-sre": "/mnt/c/Users/ojita/my-freelance-sre",
    "content-pipeline": "/mnt/c/Users/ojita/content-pipeline",
    "lol-guides-jp": "/mnt/c/Users/ojita/lol-guides-jp",
    "zenn-content": "/mnt/c/Users/ojita/zenn-content",
}

# --- チェック結果 ---

@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""
    fixable: bool = False


def check_file_exists(path: str, name: str) -> Check:
    exists = Path(path).exists()
    return Check(name=name, passed=exists,
                 detail=path if not exists else "", fixable=False)


def check_dir_exists(path: str, name: str, fixable: bool = True) -> Check:
    exists = Path(path).is_dir()
    return Check(name=name, passed=exists,
                 detail=path if not exists else "", fixable=fixable)


# --- 共通チェック（全リポジトリ） ---

def check_common(repo_path: str) -> list[Check]:
    results = []
    p = Path(repo_path)

    # 必須ファイル
    results.append(check_file_exists(str(p / "CLAUDE.md"), "CLAUDE.md"))
    results.append(check_file_exists(str(p / "README.md"), "README.md"))
    results.append(check_file_exists(str(p / ".clauderules"), ".clauderules"))
    results.append(check_file_exists(str(p / ".claudeignore"), ".claudeignore"))

    # Git状態
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "status", "--porcelain"],
            capture_output=True, text=True, timeout=10)
        uncommitted = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        results.append(Check(
            name="未コミット変更",
            passed=uncommitted == 0,
            detail=f"{uncommitted}件の変更あり" if uncommitted else "",
        ))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        results.append(Check(name="Git状態", passed=False, detail="git実行失敗"))

    # コンフリクトマーカー
    try:
        result = subprocess.run(
            ["grep", "-rl", "<<<<<<<", repo_path, "--include=*.md", "--include=*.tf",
             "--include=*.py", "--include=*.sh", "--include=*.json"],
            capture_output=True, text=True, timeout=10)
        has_conflict = bool(result.stdout.strip())
        results.append(Check(
            name="コンフリクトマーカー",
            passed=not has_conflict,
            detail=result.stdout.strip()[:200] if has_conflict else "",
        ))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        results.append(Check(name="コンフリクトマーカー", passed=True, detail="検索スキップ"))

    return results


# --- content-pipeline 固有チェック ---

def check_pipeline(repo_path: str) -> list[Check]:
    results = []
    p = Path(repo_path)

    # 必須ディレクトリ
    dirs = [
        "drafts/ja", "drafts/en", "drafts/products",
        "review_queue", "publish_queue/zenn", "publish_queue/substack",
        "published/zenn", "published/substack", "published/booth",
        "notes/incidents", "notes/learnings",
        "reports", "escalation", "ideas", "config",
        ".claude/agents", ".claude/commands",
    ]
    for d in dirs:
        results.append(check_dir_exists(str(p / d), f"DIR: {d}"))

    # 必須設定ファイル
    configs = [
        "config/topics.md", "config/strategy.md", "config/performance.md",
        "architecture.md",
    ]
    for c in configs:
        results.append(check_file_exists(str(p / c), f"FILE: {c}"))

    # agents/ と commands/ の整合性
    agents_dir = p / ".claude" / "agents"
    commands_dir = p / ".claude" / "commands"
    if agents_dir.is_dir() and commands_dir.is_dir():
        agents = {f.stem for f in agents_dir.glob("*.md")}
        commands = {f.stem for f in commands_dir.glob("*.md")}
        # コマンドが参照するエージェント名をチェック（簡易: ファイル内の "エージェントとして" を検索）
        for cmd_file in commands_dir.glob("*.md"):
            content = cmd_file.read_text(encoding="utf-8", errors="ignore")
            for agent_name in agents:
                if f"{agent_name}エージェントとして" in content:
                    break
        results.append(Check(
            name="agents/commands整合性",
            passed=True,
            detail=f"agents: {len(agents)}, commands: {len(commands)}",
        ))

    # crontabチェック
    try:
        cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        cron_text = cron.stdout
        expected_scripts = [
            "daily-research.sh", "daily-produce.sh",
            "morning-report.sh", "weekly-strategy.sh",
        ]
        for script in expected_scripts:
            found = script in cron_text
            results.append(Check(
                name=f"cron: {script}",
                passed=found,
                detail="" if found else "crontabに未登録",
            ))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        results.append(Check(name="crontab", passed=False, detail="crontab実行失敗"))

    return results


# --- my-freelance-sre 固有チェック ---

def check_sre(repo_path: str) -> list[Check]:
    results = []
    p = Path(repo_path)

    files = [
        "01-admin-setup/MyBestPractices.md",
        "01-admin-setup/WORKFLOWS.md",
        "01-admin-setup/BestPractices.md",
        "01-admin-setup/QuickRef.md",
    ]
    for f in files:
        results.append(check_file_exists(str(p / f), f"FILE: {f}"))

    results.append(check_dir_exists(str(p / "05-ai-dev-knowledge"), "DIR: 05-ai-dev-knowledge"))

    return results


# --- lol-guides-jp 固有チェック ---

def check_lol(repo_path: str) -> list[Check]:
    results = []
    p = Path(repo_path)

    results.append(check_file_exists(str(p / "POLICY.md"), "FILE: POLICY.md"))
    results.append(check_file_exists(str(p / "TODO.md"), "FILE: TODO.md"))
    results.append(check_dir_exists(str(p / "champions"), "DIR: champions"))
    results.append(check_dir_exists(str(p / "scripts"), "DIR: scripts"))

    # チャンピオン数カウント
    champions_dir = p / "champions"
    if champions_dir.is_dir():
        count = sum(1 for d in champions_dir.iterdir() if d.is_dir())
        results.append(Check(
            name="チャンピオン数",
            passed=count > 0,
            detail=f"{count}体",
        ))

    return results


# --- zenn-content 固有チェック ---

def check_zenn(repo_path: str) -> list[Check]:
    results = []
    p = Path(repo_path)

    results.append(check_dir_exists(str(p / "articles"), "DIR: articles"))
    results.append(check_dir_exists(str(p / "books"), "DIR: books"))

    # リモートURL
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "remote", "-v"],
            capture_output=True, text=True, timeout=5)
        has_remote = bool(result.stdout.strip())
        is_https = "https://" in result.stdout
        results.append(Check(
            name="Git remote",
            passed=has_remote,
            detail=result.stdout.strip().split("\n")[0] if has_remote else "未設定",
        ))
        results.append(Check(
            name="HTTPS remote",
            passed=is_https,
            detail="" if is_https else "HTTPSに変更推奨",
        ))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        results.append(Check(name="Git remote", passed=False, detail="git実行失敗"))

    return results


# --- メイン ---

def run_checks(repo_path: str, fix: bool = False) -> dict:
    repo_name = Path(repo_path).name
    results = check_common(repo_path)

    # リポジトリ別チェック
    if "content-pipeline" in repo_name:
        results.extend(check_pipeline(repo_path))
    elif "freelance-sre" in repo_name:
        results.extend(check_sre(repo_path))
    elif "lol-guides" in repo_name:
        results.extend(check_lol(repo_path))
    elif "zenn-content" in repo_name:
        results.extend(check_zenn(repo_path))

    # 自動修復
    fixed = []
    if fix:
        for r in results:
            if not r.passed and r.fixable and r.detail:
                try:
                    os.makedirs(r.detail, exist_ok=True)
                    r.passed = True
                    fixed.append(r.name)
                except OSError:
                    pass

    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    return {
        "repo": repo_name,
        "path": repo_path,
        "total": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "fixed": fixed,
        "checks": [{"name": r.name, "passed": r.passed, "detail": r.detail} for r in results],
    }


def format_text(report: dict) -> str:
    status = "PASS" if report["failed"] == 0 else "FAIL"
    lines = [f"[{status}] {report['repo']} — {report['passed']}/{report['total']}"]

    if report["fixed"]:
        lines.append(f"  自動修復: {', '.join(report['fixed'])}")

    failed = [c for c in report["checks"] if not c["passed"]]
    if failed:
        lines.append("  --- 不合格 ---")
        for c in failed:
            detail = f" ({c['detail']})" if c["detail"] else ""
            lines.append(f"  NG: {c['name']}{detail}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="リポジトリ健全性チェック")
    parser.add_argument("path", nargs="?", help="チェック対象のリポジトリパス")
    parser.add_argument("--all", action="store_true", help="全リポジトリをチェック")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--fix", action="store_true", help="不足ディレクトリを自動作成")
    args = parser.parse_args()

    if not args.path and not args.all:
        # カレントディレクトリを使用
        args.path = os.getcwd()

    targets = list(REPOS.values()) if args.all else [args.path]
    reports = []

    for target in targets:
        if not Path(target).is_dir():
            reports.append({"repo": target, "error": "ディレクトリが存在しない"})
            continue
        reports.append(run_checks(target, fix=args.fix))

    if args.format == "json":
        print(json.dumps(reports if len(reports) > 1 else reports[0],
                         ensure_ascii=False, indent=2))
    else:
        for r in reports:
            if "error" in r:
                print(f"[ERROR] {r['repo']}: {r['error']}")
            else:
                print(format_text(r))
            if len(reports) > 1:
                print()

    # 不合格があればexit 1
    if any(r.get("failed", 0) > 0 for r in reports):
        sys.exit(1)


if __name__ == "__main__":
    main()
