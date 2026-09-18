#!/usr/bin/env python3
"""Verify that consuming code's references to WEO terms still resolve.

Consumers annotate their models with the WEO term each one implements. There are
two ways to write that reference, and this checks both.

TERM REFERENCES (preferred) name the term itself:

    // `weo:Recommendation` (`weo-decision.ttl`)

A term name is stable for the life of the term, so the only way this goes wrong
is if the term is renamed or removed — which this catches.

LINE CITATIONS name a position in a file:

    // weo-decision.ttl:78-82

These are exact when written and silently false the moment anything is inserted
above them. Nothing breaks; the comment just starts naming a different term, and
the next reader trusts it. Worse, a line range can drift onto a *different* valid
term, in which case it still resolves cleanly and only a human comparing the
prose to the range would notice. Prefer term references; this mode exists to
catch the stragglers.

    python tools/verify_citations.py ../launch-guardian ../if-control-center
    python tools/verify_citations.py --ref origin/main ~/src/launch-guardian
    python tools/verify_citations.py .          # defaults to the cwd

Line-citation statuses:
    OK              the range covers exactly one term
    SPANS-MULTIPLE  the range runs across a term boundary — tighten it
    NO-TERM         the range covers no declaration (usually module header prose;
                    those cannot be re-anchored to a term name, so quote without
                    a line number instead)
    OUT-OF-RANGE    the file is now shorter than the citation

Term-reference statuses:
    OK              the term is declared in the ontology
    UNDECLARED      no module declares it — renamed, removed, or a typo

Exits non-zero if anything in either mode fails.

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
TERM_REF = re.compile(r"(?<![\w-])weo:([A-Za-z][\w-]*)")
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
    """Yield (label, text) for each candidate file, from a git ref or the worktree.

    This file is skipped. Its docstring demonstrates a bad citation, on purpose,
    and the checker reading its own example reported a failure on every clean
    run — which teaches the one habit a checker must never teach, that a red
    result is background noise.
    """
    me = os.path.basename(__file__)
    if ref:
        listing = subprocess.run(
            ["git", "grep", "-l", "-e", r"weo-.*\.ttl:", "-e", r"weo:", ref],
            cwd=root, capture_output=True, text=True,
        )
        for spec in listing.stdout.split():
            label = spec.split(":", 1)[1]
            if os.path.basename(label) == me:
                continue
            blob = subprocess.run(["git", "show", spec], cwd=root,
                                  capture_output=True, text=True).stdout
            yield label, blob
        return
    for directory, subdirs, files in os.walk(root):
        subdirs[:] = [d for d in subdirs if d not in SKIP_DIRS]
        for name in files:
            if not name.endswith(TEXT_SUFFIXES) or name == me:
                continue
            path = os.path.join(directory, name)
            try:
                text = open(path, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            if "ttl:" in text or "weo:" in text:
                yield os.path.relpath(path, root), text


def declared_terms() -> set[str]:
    """Every term any module declares — the vocabulary a consumer may name."""
    terms: set[str] = set()
    for name in os.listdir(ONTOLOGY_DIR):
        if not (name.startswith("weo-") and name.endswith(".ttl")):
            continue
        with open(os.path.join(ONTOLOGY_DIR, name), encoding="utf-8") as handle:
            for line in handle:
                match = DECLARATION.match(line)
                if match:
                    terms.add(match.group(1))
    return terms


def check(roots: list[str], ref: str | None) -> int:
    ontology = load_ontology()
    vocabulary = declared_terms()
    rows = []
    term_rows = []
    for root in roots:
        label = os.path.basename(os.path.abspath(root))
        for filename, text in sources(root, ref):
            for line_number, line in enumerate(text.split("\n"), 1):
                for term in TERM_REF.findall(line):
                    status = "OK" if term in vocabulary else "UNDECLARED"
                    term_rows.append((label, filename, line_number,
                                      "weo:" + term, status))
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

    if not rows and not term_rows:
        print("No WEO references found. Nothing to verify.")
        return 0

    failures = [row for row in rows if row[4] != "OK"]
    bad_terms = [row for row in term_rows if row[4] != "OK"]

    if rows:
        rows.sort()
        width = max(len(row[3]) for row in rows)
        print("LINE CITATIONS")
        for repo, filename, line_number, citation, status, resolved in rows:
            marker = " " if status == "OK" else "✗"
            print(f"{marker} {repo}/{filename}:{line_number}  {citation:{width}}  "
                  f"{status:15} {resolved}")
        print(f"\n  {len(rows)} citations · {len(rows) - len(failures)} OK · "
              f"{len(failures)} to fix")
        if failures:
            print("\n  Re-anchor a failing citation to the term name "
                  "(`weo:Recommendation`) rather than widening the range.")
        print()

    if term_rows:
        distinct = sorted({row[3] for row in term_rows})
        print("TERM REFERENCES")
        for repo, filename, line_number, term, status in sorted(bad_terms):
            print(f"✗ {repo}/{filename}:{line_number}  {term}  {status}")
        print(f"  {len(term_rows)} references · {len(distinct)} distinct terms · "
              f"{len(bad_terms)} unresolved")
        if bad_terms:
            print("\n  An unresolved term was renamed, removed, or mistyped. Check it "
                  "against the module it claims to come from.")

    return 1 if (failures or bad_terms) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("roots", nargs="*", default=["."],
                        help="repositories or directories to scan (default: cwd)")
    parser.add_argument("--ref", help="scan this git ref instead of the working tree")
    args = parser.parse_args()
    return check(args.roots or ["."], args.ref)


if __name__ == "__main__":
    sys.exit(main())
