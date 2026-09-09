#!/usr/bin/env python3
"""Verify `weo-*.ttl:LINE` citations in consuming code still land on their term.

launch-guardian and if-control-center annotate their models with the WEO term each
one implements, cited by file **and line** — `weo-decision.ttl:46-49`. Those
citations are exact when written and silently false the moment anything is
inserted above them. Nothing breaks; the comments just start pointing at the wrong
term, and the next reader trusts them.

This resolves every citation against the ontology as it stands now and exits
non-zero if any of them no longer names exactly one term.

    python tools/verify_citations.py ../launch-guardian ../if-control-center
    python tools/verify_citations.py --ref origin/main ~/src/launch-guardian
    python tools/verify_citations.py .          # defaults to the cwd

Statuses:
    OK              the range covers exactly one term
    SPANS-MULTIPLE  the range runs across a term boundary — tighten it
    NO-TERM         the range covers no declaration (usually module header prose;
                    those cannot be re-anchored to a term name, so quote without
                    a line number instead)
    OUT-OF-RANGE    the file is now shorter than the citation

No third-party dependencies: this is meant to run in anyone's CI.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

ONTOLOGY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CITATION = re.compile(r"(weo-[a-z]+\.ttl):(\d+)(?:\s*-\s*(\d+))?")
DECLARATION = re.compile(r"^weo:([\w-]+)\s+(?:a\s|rdfs:|skos:)")
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".next", "coverage", "__pycache__"}
TEXT_SUFFIXES = (".ts", ".tsx", ".js", ".mjs", ".cjs", ".py", ".md", ".cypher", ".graphql", ".gql")


def term_spans(path: str) -> tuple[dict[int, str], int]:
    """Map each line number to the term declared there, or None outside any block."""
    lines = open(path, encoding="utf-8").read().split("\n")
    mapping: dict[int, str] = {}
    current: str | None = None
    for number, line in enumerate(lines, 1):
        match = DECLARATION.match(line)
        if match:
            current = match.group(1)
        if current:
            mapping[number] = current
        # A Turtle statement ends at a bare `.` — the block is over.
        if current and re.search(r"(^|\s)\.\s*$", line):
            current = None
    return mapping, len(lines)


def load_ontology() -> dict[str, tuple[dict[int, str], int]]:
    return {
        name: term_spans(os.path.join(ONTOLOGY_DIR, name))
        for name in os.listdir(ONTOLOGY_DIR)
        if name.startswith("weo-") and name.endswith(".ttl")
    }


def sources(root: str, ref: str | None):
    """Yield (label, text) for each candidate file, from a git ref or the worktree."""
    if ref:
        listing = subprocess.run(
            ["git", "grep", "-l", r"weo-.*\.ttl:", ref],
            cwd=root, capture_output=True, text=True,
        )
        for spec in listing.stdout.split():
            blob = subprocess.run(["git", "show", spec], cwd=root,
                                  capture_output=True, text=True).stdout
            yield spec.split(":", 1)[1], blob
        return
    for directory, subdirs, files in os.walk(root):
        subdirs[:] = [d for d in subdirs if d not in SKIP_DIRS]
        for name in files:
            if not name.endswith(TEXT_SUFFIXES):
                continue
            path = os.path.join(directory, name)
            try:
                text = open(path, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            if "ttl:" in text:
                yield os.path.relpath(path, root), text


def check(roots: list[str], ref: str | None) -> int:
    ontology = load_ontology()
    rows = []
    for root in roots:
        label = os.path.basename(os.path.abspath(root))
        for filename, text in sources(root, ref):
            for line_number, line in enumerate(text.split("\n"), 1):
                for hit in CITATION.finditer(line):
                    name = hit.group(1)
                    start = int(hit.group(2))
                    end = int(hit.group(3) or hit.group(2))
                    if name not in ontology:
                        rows.append((label, filename, line_number, hit.group(0),
                                     "NO-SUCH-FILE", ""))
                        continue
                    mapping, length = term_spans(os.path.join(ONTOLOGY_DIR, name))
                    if end > length:
                        rows.append((label, filename, line_number, hit.group(0),
                                     "OUT-OF-RANGE", f"file is {length} lines"))
                        continue
                    found = sorted({mapping[n] for n in range(start, end + 1) if n in mapping})
                    if len(found) == 1:
                        status = "OK"
                    elif not found:
                        status = "NO-TERM"
                    else:
                        status = "SPANS-MULTIPLE"
                    rows.append((label, filename, line_number, hit.group(0), status,
                                 " + ".join("weo:" + f for f in found)))

    if not rows:
        print("No weo-*.ttl citations found. Nothing to verify.")
        return 0

    rows.sort()
    width = max(len(row[3]) for row in rows)
    failures = [row for row in rows if row[4] != "OK"]
    for repo, filename, line_number, citation, status, resolved in rows:
        marker = " " if status == "OK" else "✗"
        print(f"{marker} {repo}/{filename}:{line_number}  {citation:{width}}  "
              f"{status:15} {resolved}")
    print(f"\n{len(rows)} citations · {len(rows) - len(failures)} OK · {len(failures)} to fix")
    if failures:
        print("\nRe-anchor a failing citation to the term name (`weo:Recommendation`) "
              "rather than widening the range.")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("roots", nargs="*", default=["."],
                        help="repositories or directories to scan (default: cwd)")
    parser.add_argument("--ref", help="scan this git ref instead of the working tree")
    args = parser.parse_args()
    return check(args.roots or ["."], args.ref)


if __name__ == "__main__":
    sys.exit(main())
