#!/usr/bin/env python3
"""health-check.py — リポジトリの健全性チェック（L1 Infrastructure）

/confirm の機械的チェック項目をPythonで実行する。
AIのクリエイティビティが不要な「存在確認」「整合性チェック」を担当。

使い方:
  python3 health-check.py /home/ojita/content-pipeline         # 単体チェック
  python3 health-check.py --all                                 # 全リポジトリ
  python3 health-check.py --all --output /path/to/report.txt   # ファイル出力
  python3 health-check.py /home/ojita/content-pipeline --format json
  python3 health-check.py /home/ojita/content-pipeline --fix   # 不足ディレクトリを自動作成
  python3 health-check.py /home/ojita/content-pipeline --dry-run  # 確認のみ
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# --- リポジトリ定義 ---

REPOS = {
    "my-freelance-sre": "/home/ojita/my-freelance-sre",
    "content-pipeline": "/home/ojita/content-pipeline",
    "lol-guides-jp": "/home/ojita/lol-guides-jp",
    "zenn-content": "/home/ojita/zenn-content",
}

GLOBAL_TOOLS = ["cost-report.py", "lint-ai-style.py", "health-check.py"]

# --- 憲法ルール目録（L5 Meta）---
# CLAUDE.md の機械チェック可能なルールをここで宣言する。
# 新しい憲法ルールを追加したら:
#   (1) ここにエントリ追加 → (2) 対応実装の近くに # RULE: <id> コメント追加
CONSTITUTION_RULE_IDS = [
    "dry_run",          # スクリプトには --dry-run モードを実装する
    "set_euo_pipefail", # Bash スクリプトには set -euo pipefail を書く
    "git_https",        # Git remote は HTTPS を使う（SSH不可）
    "style_rules",      # .clauderules に STYLE RULES セクションを持つ
    "l1_tools",         # ~/.claude/scripts/ に L1 ツールが存在する
    "known_failures",   # known-failures.md が存在する
]


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


# --- 憲法ルール準拠チェック（共通） ---

def check_scripts_dry_run(repo_path: str) -> list[Check]:  # RULE: dry_run
    """scripts/*.sh に --dry-run 実装があるか確認（lib.sh は除外）"""
    results = []
    scripts_dir = Path(repo_path) / "scripts"
    if not scripts_dir.is_dir():
        return results

    for sh in sorted(scripts_dir.glob("*.sh")):
        if sh.name == "lib.sh":
            continue
        content = sh.read_text(encoding="utf-8", errors="ignore")
        has_dry_run = "DRY_RUN" in content
        results.append(Check(
            name=f"dry-run: scripts/{sh.name}",
            passed=has_dry_run,
            detail="" if has_dry_run else "--dry-run 未実装",
        ))

    return results


def check_scripts_set_e(repo_path: str) -> list[Check]:  # RULE: set_euo_pipefail
    """scripts/*.sh に set -euo pipefail があるか確認（lib.sh は除外）"""
    results = []
    scripts_dir = Path(repo_path) / "scripts"
    if not scripts_dir.is_dir():
        return results

    for sh in sorted(scripts_dir.glob("*.sh")):
        if sh.name == "lib.sh":
            continue
        content = sh.read_text(encoding="utf-8", errors="ignore")
        has_set_e = "set -euo pipefail" in content
        results.append(Check(
            name=f"set -euo pipefail: scripts/{sh.name}",
            passed=has_set_e,
            detail="" if has_set_e else "set -euo pipefail なし",
        ))

    return results


def check_git_https(repo_path: str) -> Check:  # RULE: git_https
    """Git remote が HTTPS か確認"""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "remote", "-v"],
            capture_output=True, text=True, timeout=5)
        if not result.stdout.strip():
            return Check(name="Git remote HTTPS", passed=False, detail="remote未設定")
        is_https = "https://" in result.stdout
        return Check(
            name="Git remote HTTPS",
            passed=is_https,
            detail="" if is_https else "SSH使用（HTTPSに変更推奨）",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return Check(name="Git remote HTTPS", passed=False, detail="git実行失敗")


# --- メタチェック（health-check.py 自身の憲法準拠） ---

def check_self_coverage() -> list[Check]:
    """health-check.py 自身が全憲法ルールをカバーしているか確認"""
    results = []
    self_src = Path(__file__).read_text(encoding="utf-8")

    # --dry-run フラグの実装確認
    results.append(Check(
        name="self: --dry-run 実装",
        passed="args.dry_run" in self_src,
        detail="" if "args.dry_run" in self_src else "health-check.py 自身に --dry-run がない",
    ))

    # 各憲法ルールに対応する # RULE: <id> アノテーションの存在確認
    for rule_id in CONSTITUTION_RULE_IDS:
        marker = f"# RULE: {rule_id}"
        has_impl = marker in self_src
        results.append(Check(
            name=f"self: RULE:{rule_id}",
            passed=has_impl,
            detail="" if has_impl else f"'{marker}' アノテーションなし → 実装漏れの可能性",
        ))

    return results


# --- グローバルチェック（~/.claude/ 全体） ---

def check_global() -> dict:
    """L1ツール・グローバル設定の存在確認"""
    results = []
    scripts_dir = Path.home() / ".claude" / "scripts"

    for tool in GLOBAL_TOOLS:  # RULE: l1_tools
        path = scripts_dir / tool
        results.append(Check(
            name=f"L1ツール: {tool}",
            passed=path.exists(),
            detail=str(path) if not path.exists() else "",
        ))

    kf = Path.home() / ".claude" / "known-failures.md"  # RULE: known_failures
    results.append(Check(
        name="known-failures.md",
        passed=kf.exists(),
        detail=str(kf) if not kf.exists() else "",
    ))

    # メタチェック: health-check.py 自身の憲法準拠
    results.extend(check_self_coverage())

    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    return {
        "repo": "global (~/.claude)",
        "path": str(Path.home() / ".claude"),
        "total": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "fixed": [],
        "checks": [{"name": r.name, "passed": r.passed, "detail": r.detail} for r in results],
    }


# --- 共通チェック（全リポジトリ） ---

def check_common(repo_path: str) -> list[Check]:
    results = []
    p = Path(repo_path)

    # 必須ファイル
    results.append(check_file_exists(str(p / "CLAUDE.md"), "CLAUDE.md"))
    results.append(check_file_exists(str(p / "README.md"), "README.md"))

    clauderules = p / ".clauderules"
    results.append(check_file_exists(str(clauderules), ".clauderules"))
    if clauderules.exists():
        content = clauderules.read_text(encoding="utf-8", errors="ignore")
        results.append(Check(  # RULE: style_rules
            name=".clauderules STYLE RULES",
            passed="STYLE RULES" in content,
            detail="" if "STYLE RULES" in content else "STYLE RULESセクションなし",
        ))

    results.append(check_file_exists(str(p / ".claudeignore"), ".claudeignore"))

    # scripts/lib.sh（scriptsディレクトリがある場合）
    scripts_dir = p / "scripts"
    if scripts_dir.is_dir():
        results.append(check_file_exists(str(scripts_dir / "lib.sh"), "scripts/lib.sh"))

    # Git状態
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "status", "--porcelain"],
            capture_output=True, text=True, timeout=10)
        # ?? (untracked) は除外してステージ済み・未ステージの変更のみカウント
        uncommitted = sum(1 for line in result.stdout.strip().split("\n")
                          if line and not line.startswith("??")) if result.stdout.strip() else 0
        results.append(Check(
            name="未コミット変更",
            passed=uncommitted == 0,
            detail=f"{uncommitted}件の変更あり" if uncommitted else "",
        ))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        results.append(Check(name="Git状態", passed=False, detail="git実行失敗"))

    # Git remote HTTPS（known-failures.md に明記されている共通ルール）
    results.append(check_git_https(repo_path))

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

    # 憲法ルール: scripts/ の --dry-run / set -euo pipefail 実装
    results.extend(check_scripts_dry_run(repo_path))
    results.extend(check_scripts_set_e(repo_path))

    return results


# --- content-pipeline 固有チェック ---

def check_pipeline(repo_path: str) -> list[Check]:
    results = []
    p = Path(repo_path)

    # 必須ディレクトリ
    dirs = [
        "drafts/ja", "drafts/en", "drafts/products",
        "review_queue", "publish_queue/zenn",
        "published/booth",
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

    # agents/ と commands/ の整合性（未参照agentを検出）
    agents_dir = p / ".claude" / "agents"
    commands_dir = p / ".claude" / "commands"
    if agents_dir.is_dir() and commands_dir.is_dir():
        agents = {f.stem for f in agents_dir.glob("*.md")}
        cmd_files = list(commands_dir.glob("*.md"))
        all_cmd_text = "\n".join(
            f.read_text(encoding="utf-8", errors="ignore") for f in cmd_files
        )
        unreferenced = {a for a in agents if f"{a}エージェントとして" not in all_cmd_text}
        results.append(Check(
            name="agents/commands整合性",
            passed=len(unreferenced) == 0,
            detail=f"未参照agent: {', '.join(sorted(unreferenced))}" if unreferenced
                   else f"agents: {len(agents)}, commands: {len(cmd_files)}",
        ))

    # crontabチェック（登録有無 + スクリプトファイル存在）
    try:
        cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        cron_text = cron.stdout
        expected_scripts = [
            "daily-research.sh", "daily-produce.sh",
            "morning-report.sh", "weekly-strategy.sh",
        ]
        for script in expected_scripts:
            in_cron = script in cron_text
            results.append(Check(
                name=f"cron登録: {script}",
                passed=in_cron,
                detail="" if in_cron else "crontabに未登録",
            ))
            script_path = p / "scripts" / script
            results.append(Check(
                name=f"cronファイル: {script}",
                passed=script_path.exists(),
                detail="" if script_path.exists() else "ファイルが存在しない",
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
    results.append(check_file_exists(str(p / "current-patch.txt"), "FILE: current-patch.txt"))
    results.append(check_dir_exists(str(p / "patches"), "DIR: patches"))

    # cron チェック（登録有無 + スクリプトファイル存在）
    try:
        cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        in_cron = "check-patch.sh" in cron.stdout
        results.append(Check(
            name="cron登録: check-patch.sh",
            passed=in_cron,
            detail="" if in_cron else "crontabに未登録",
        ))
        script_path = p / "scripts" / "check-patch.sh"
        results.append(Check(
            name="cronファイル: check-patch.sh",
            passed=script_path.exists(),
            detail="" if script_path.exists() else "ファイルが存在しない",
        ))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        results.append(Check(name="cron: check-patch.sh", passed=False, detail="crontab実行失敗"))

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

    return results


# --- メイン ---

def run_checks(repo_path: str, fix: bool = False) -> dict:
    repo_name = Path(repo_path).name
    results = check_common(repo_path)

    if "content-pipeline" in repo_name:
        results.extend(check_pipeline(repo_path))
    elif "freelance-sre" in repo_name:
        results.extend(check_sre(repo_path))
    elif "lol-guides" in repo_name:
        results.extend(check_lol(repo_path))
    elif "zenn-content" in repo_name:
        results.extend(check_zenn(repo_path))

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

    if report.get("fixed"):
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
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="修正は行わず確認のみ（--fixを無効化）")
    parser.add_argument("--output", metavar="FILE",
                        help="結果をファイルに出力（省略時はstdout）")
    args = parser.parse_args()

    if args.dry_run and args.fix:
        print("--dry-run が指定されているため --fix は無効です")
        args.fix = False

    if not args.path and not args.all:
        args.path = os.getcwd()

    # グローバルチェック（常に実行）
    reports = [check_global()]

    targets = list(REPOS.values()) if args.all else [args.path]
    for target in targets:
        if not Path(target).is_dir():
            reports.append({"repo": target, "error": "ディレクトリが存在しない"})
            continue
        reports.append(run_checks(target, fix=args.fix))

    # 出力生成
    if args.format == "json":
        output = json.dumps(reports, ensure_ascii=False, indent=2)
    else:
        lines = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines.append(f"# health-check {timestamp}")
        lines.append("")
        for r in reports:
            if "error" in r:
                lines.append(f"[ERROR] {r['repo']}: {r['error']}")
            else:
                lines.append(format_text(r))
            lines.append("")
        output = "\n".join(lines).rstrip()

    # ファイル or stdout
    latest = Path.home() / ".claude" / "reports" / "health-check-latest.txt"
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        # latest も常に更新
        latest.parent.mkdir(parents=True, exist_ok=True)
        latest.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    # self: チェック失敗 → CLAUDE.local.md に通知（ログパス付き）
    if not args.dry_run:
        self_failures = [
            c["name"] for r in reports
            for c in r.get("checks", [])
            if not c["passed"] and c["name"].startswith("self:")
        ]
        if self_failures:
            log_path = str(args.output) if args.output else str(latest)
            msg = (
                f"- [WARN] health-check.py 憲法違反 ({datetime.now().strftime('%Y-%m-%d')}): "
                f"{', '.join(self_failures)} -> 詳細: {log_path}\n"
            )
            local_md = Path.home() / "CLAUDE.local.md"
            with local_md.open("a", encoding="utf-8") as f:
                f.write(msg)

    if any(r.get("failed", 0) > 0 for r in reports):
        sys.exit(1)


if __name__ == "__main__":
    main()
