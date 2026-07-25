#!/usr/bin/env python3
"""Pre-publish security checks. Modeled after sure-state's security-check.ts."""
import os
import re
import subprocess
import sys


def check_no_secrets():
    src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
    patterns = [
        (r"password\s*=\s*['\"].+['\"]", "Hardcoded password"),
        (r"api_key\s*=\s*['\"].+['\"]", "Hardcoded API key"),
        (r"secret\s*=\s*['\"].+['\"]", "Hardcoded secret"),
        (r"token\s*=\s*['\"].+['\"]", "Hardcoded token"),
    ]
    issues = []
    for root, _, files in os.walk(src_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath) as f:
                for i, line in enumerate(f, 1):
                    for pat, desc in patterns:
                        if re.search(pat, line):
                            issues.append(f"  {fpath}:{i} — {desc}")
    if issues:
        print("Security issues found:")
        for issue in issues:
            print(issue)
        return False
    print("No security issues found")
    return True


def check_dependencies():
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=columns"],
        capture_output=True, text=True,
    )
    print("Dependencies:")
    print(result.stdout)
    return True


if __name__ == "__main__":
    ok = True
    ok &= check_no_secrets()
    ok &= check_dependencies()
    sys.exit(0 if ok else 1)
