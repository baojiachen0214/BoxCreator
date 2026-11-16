"""Publication audit of Git's index, without printing matching secret values."""
import re
import subprocess
from pathlib import Path


def findings(text):
    rules = {
        "provider-token": r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})",
        "private-key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "bearer-value": r"(?i)authorization[\s\"':=]+bearer\s+[A-Za-z0-9_.-]{16,}",
        "literal-credential": r'''(?im)^\s*(?:export\s+)?(?:[A-Z0-9_]*API_KEY|[A-Z0-9_]*SECRET|[A-Z0-9_]*TOKEN|PASSWORD)\s*=\s*["']?[A-Za-z0-9_/+.-]{16,}''',
        "private-machine-path": "/" + r"(?:Users|home)/[A-Za-z0-9_\u4e00-\u9fff.-]+/",
    }
    return [name for name, pattern in rules.items() if re.search(pattern, text)]


def audit_index(root):
    root = Path(root)
    raw = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z", "--cached"])
    files = [p.decode() for p in raw.split(b"\0") if p]
    if not files: raise ValueError("Stage the intended public files before auditing")
    issues = []
    blocked = {".env", ".venv", "node_modules", "input", "work", "output", "deliverables"}
    for rel in files:
        p = Path(rel)
        if blocked.intersection(p.parts) or p.suffix in {".pem", ".key", ".blend", ".mp4", ".zip", ".log", ".jsonl"}:
            issues.append({"file": rel, "reason": "private-or-generated-file"})
        # Read the staged version, so unstaged edits cannot hide a committed value.
        blob = subprocess.check_output(["git", "-C", str(root), "show", f":{rel}"])
        mode = subprocess.check_output(["git", "-C", str(root), "ls-files", "-s", "--", rel]).split()[0]
        if mode == b"120000": issues.append({"file": rel, "reason": "symlink-needs-explicit-review"})
        for reason in findings(blob.decode("utf-8", errors="replace")):
            issues.append({"file": rel, "reason": reason})
    return {"staged_files": len(files), "issues": issues,
            "scope": "Git index only; separately review history, release assets, image metadata and account screenshots"}
