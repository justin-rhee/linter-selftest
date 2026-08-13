#!/usr/bin/env python3
"""A two-rule markdown linter that proves its own rules can fire before it asks
anyone to believe a clean report.

I wrote it after a linter of mine reported a clean corpus three times while one
of its rules was never executed. A rule that cannot fire and a corpus with
nothing wrong in it print the same thing.

The two rules here are a worked example. The part worth copying is `--selftest`,
which does two things and exits 2 if either fails. Every rule runs against a
corpus carrying exactly that rule's defect and has to report it. Every rule also
runs against a corpus with nothing wrong in it, and the result has to be empty,
which is what catches a rule that fires on everything. A rule like that passes
all five positive fixtures, since all five contain notes.

The list of rules is read out of this file's own source rather than kept by
hand. A hand-kept list fails the way the original rule failed: somebody writes a
rule, does not add the name, and nothing notices.

Usage:
    linter_selftest.py [NOTES_DIR]   check a directory of markdown notes
    linter_selftest.py --selftest    prove every rule fires, and stays quiet
    linter_selftest.py --json        machine-readable findings

Exit: 0 clean, 1 findings, 2 self-test failure or bad invocation.

The checker lives outside the notes it checks, on purpose. A validator kept
inside the thing it validates can be rewritten by anyone who gets write access
to that thing, and after that it approves whatever they like. It reads note
content as data and never executes or interprets it.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from collections import namedtuple
from pathlib import Path

# ---- the example rules ---------------------------------------------------

STATUSES = {"draft", "review", "published"}
MIN_SOURCES = 2

FIELD_RE = re.compile(r"^(\w+):\s*(.*)$")
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

Finding = namedtuple("Finding", "rule path detail")


def parse_frontmatter(text):
    """Read the flat `key: value` block between the leading `---` fences.

    A YAML subset, standard library only, so this runs on a stock python3 with
    nothing to install and no virtualenv to activate."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fields = {}
    for line in text[3:end].strip("\n").split("\n"):
        m = FIELD_RE.match(line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields


def links_in(value):
    return [t.split("|")[0].strip() for t in LINK_RE.findall(value or "")]


def load_notes(root):
    """title -> (path relative to root, fields), for every note with frontmatter.

    Titles are filenames, which is how notes address each other in a link."""
    notes = {}
    for path in sorted(root.rglob("*.md")):
        fields = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        if fields is not None:
            notes[path.stem] = (str(path.relative_to(root)), fields)
    return notes


def source_termini(start, notes):
    """The distinct `source` notes reachable from `start` by following `cites`.

    A note often cites another note rather than a source directly, so this walks
    the chain instead of looking one hop out. Counting distinct end points and
    not citations is what makes "two sources" mean two: four notes that all trace
    back to the same source are one source, not four. `seen` guards a cycle."""
    found, seen, stack = set(), set(), list(start)
    while stack:
        title = stack.pop()
        if title in seen:
            continue
        seen.add(title)
        entry = notes.get(title)
        if entry is None:
            continue
        fields = entry[1]
        if fields.get("type") == "source":
            found.add(title)
            continue
        for nxt in links_in(fields.get("cites", "")):
            stack.append(nxt)
    return found


def check_notes(root):
    notes = load_notes(root)
    out = []
    for title, (rel, fields) in sorted(notes.items()):
        status = fields.get("status", "").strip()
        if status and status not in STATUSES:
            detail = "status=%r is not one of %s" % (status, sorted(STATUSES))
            out.append(Finding("status-value", rel, detail))
        if status == "published" and fields.get("type") != "source":
            sources = source_termini(links_in(fields.get("cites", "")), notes)
            if len(sources) < MIN_SOURCES:
                detail = ("published on %d distinct source(s), needs %d"
                          % (len(sources), MIN_SOURCES))
                out.append(Finding("thin-sourcing", rel, detail))
    return out


# ---- the self-test -------------------------------------------------------

def note(kind="note", status="draft", cites=()):
    links = ", ".join('"[[%s]]"' % c for c in cites)
    return "---\ntype: %s\nstatus: %s\ncites: [%s]\n---\nbody\n" % (kind, status, links)


# The negative control. Every note here is legitimate, so a run over this corpus
# has to be silent. "Chained" is the one that earns its place: it reaches two
# sources only through two other notes, so it stays quiet only while the chain
# walk works.
CLEAN_CORPUS = {
    "notes/Source alpha.md": note("source", "published"),
    "notes/Source beta.md": note("source", "published"),
    "notes/Direct.md": note(status="published", cites=("Source alpha", "Source beta")),
    "notes/Relay one.md": note(cites=("Source alpha",)),
    "notes/Relay two.md": note(cites=("Source beta",)),
    "notes/Chained.md": note(status="published", cites=("Relay one", "Relay two")),
    "notes/Rough.md": note(),
}

# (what the fixture is, the notes it adds to the clean corpus, the rule it must trip)
FIXTURES = [
    ("a status outside the allowed set",
     {"notes/Typo.md": note(status="pubished", cites=("Source alpha", "Source beta"))},
     "status-value"),
    ("published on a single source",
     {"notes/Thin.md": note(status="published", cites=("Source alpha",))},
     "thin-sourcing"),
    ("published on no sources at all",
     {"notes/Bare.md": note(status="published")},
     "thin-sourcing"),
    ("the same source cited twice is still one source",
     {"notes/Doubled.md": note(status="published", cites=("Source alpha", "Source alpha"))},
     "thin-sourcing"),
    ("two citation chains that converge on one source",
     {"notes/Converged.md": note(status="published", cites=("Relay one", "Relay three")),
      "notes/Relay three.md": note(cites=("Source alpha",))},
     "thin-sourcing"),
]


def write_corpus(root, files):
    """Write a corpus, refusing two filenames that differ only by case.

    macOS folds case and Linux does not, so such a pair is one file on my laptop
    and two in CI. The fixture that lost the coin toss never exists, the rule it
    was meant to exercise is proved by nothing, and the suite still says OK."""
    seen = {}
    for rel in files:
        key = rel.lower()
        if key in seen:
            raise AssertionError("corpus names collide once case is folded: %s and %s"
                                 % (seen[key], rel))
        seen[key] = rel
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def rules_in_source():
    """Every rule name this file can emit, read out of the source."""
    src = Path(__file__).read_text(encoding="utf-8")
    return set(re.findall(r'Finding\("([a-z][a-z-]*)"', src))


def selftest():
    failures = []

    # The negative control runs first. If a clean corpus produces findings, every
    # positive result below is worthless, because a linter that flags everything
    # trips every fixture without telling anything apart.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_corpus(root, CLEAN_CORPUS)
        noise = check_notes(root)
        if noise:
            shown = sorted(set("%s on %s" % (f.rule, f.path) for f in noise))
            failures.append("CLEAN CORPUS produced %d finding(s): %s%s"
                            % (len(noise), ", ".join(shown[:3]),
                               ", ..." if len(shown) > 3 else ""))

    # Positive controls. Each fixture carries one defect and has to be reported.
    for what, extra, expect in FIXTURES:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            files = dict(CLEAN_CORPUS)
            files.update(extra)
            write_corpus(root, files)
            fired = set(f.rule for f in check_notes(root))
            if expect not in fired:
                failures.append("%s: expected %r to fire, got %s"
                                % (what, expect, sorted(fired) or "nothing"))

    # Coverage, in both directions.
    emitted, claimed = rules_in_source(), set(e for _, _, e in FIXTURES)
    for rule in sorted(emitted - claimed):
        failures.append("rule %r has no fixture, so nothing proves it can fire" % rule)
    for rule in sorted(claimed - emitted):
        failures.append("a fixture expects rule %r but no code emits it" % rule)

    if failures:
        print("SELF-TEST FAILED. A clean report from this linter means nothing:")
        for line in failures:
            print("  x %s" % line)
        return 2
    print("self-test OK: %d rule(s), %d fixture(s) each proved to fire, clean corpus quiet"
          % (len(emitted), len(FIXTURES)))
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    positional = [a for a in argv[1:] if not a.startswith("--")]
    root = Path(positional[0]).expanduser() if positional else Path(".")
    if not root.is_dir():
        print("error: not a directory: %s" % root, file=sys.stderr)
        return 2

    findings = check_notes(root)
    if "--json" in argv:
        print(json.dumps([dict(f._asdict()) for f in findings], indent=2))
        return 1 if findings else 0
    if not findings:
        print("%s: no findings." % root)
        print("Run --selftest before believing that. An unexercised linter and a")
        print("clean corpus print the same thing.")
        return 0
    print("%s: %d finding(s)" % (root, len(findings)))
    for f in sorted(findings):
        print("  %-13s %s: %s" % (f.rule, f.path, f.detail))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
