#!/usr/bin/env python3
"""
Generate a deterministic project tree from Git-tracked files.

Why:
- Deploy pulls from Git (`git reset --hard origin/main`), so *tracked files* are the only
  stable definition of what exists in the app codebase.
- Avoids noise: .venv, __pycache__, data/ etc. are not part of repo and should not drive sync.

Usage (from repo root):
  python scripts/dev/generate_repo_tree.py --out docs/PROJECT_TREE.md

Debug:
  - If it prints nothing: ensure you're in repo root and `git` is available.
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Node:
    """Tree node for file path segments."""
    children: Dict[str, "Node"] = field(default_factory=dict)
    is_file: bool = False


def _git_ls_files() -> List[str]:
    """
    Return git-tracked files as posix paths.
    Uses `git ls-files` so results match what deploy will ship.

    Troubleshooting:
      - If this fails, run `git status` manually to confirm repo context.
    """
    out = subprocess.check_output(["git", "ls-files"], text=True)
    files = [ln.strip() for ln in out.splitlines() if ln.strip()]
    files.sort()
    return files


def _build_tree(files: List[str]) -> Node:
    """
    Build an in-memory trie from file paths.

    Each segment becomes a node. Leaves are marked `is_file=True`.
    """
    root = Node()
    for p in files:
        cur = root
        parts = p.split("/")
        for i, seg in enumerate(parts):
            cur = cur.children.setdefault(seg, Node())
            if i == len(parts) - 1:
                cur.is_file = True
    return root


def _render(node: Node, prefix: str = "") -> List[str]:
    """
    Render the tree using unicode line drawing.
    Deterministic ordering: folders first, then files, both alphabetical.
    """
    lines: List[str] = []

    items = list(node.children.items())

    def sort_key(kv):
        name, child = kv
        is_dir = len(child.children) > 0 and not child.is_file
        # dirs first
        return (0 if is_dir else 1, name.lower())

    items.sort(key=sort_key)

    for idx, (name, child) in enumerate(items):
        last = idx == len(items) - 1
        branch = "└── " if last else "├── "
        lines.append(f"{prefix}{branch}{name}")

        # If it has children, continue rendering
        if child.children:
            ext = "    " if last else "│   "
            lines.extend(_render(child, prefix + ext))

    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/PROJECT_TREE.md")
    args = ap.parse_args()

    files = _git_ls_files()
    tree = _build_tree(files)

    header = [
        "# PROJECT TREE (git-tracked)",
        "",
        "Generat automat din `git ls-files` ca să reflecte exact ce se deploy-ează pe VPS.",
        "",
        "```text",
    ]
    body = _render(tree)
    footer = ["```", ""]

    content = "\n".join(header + body + footer)

    # Write output file
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"OK: wrote {args.out} ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
