#!/usr/bin/env python3
"""Offline test suite for linter-selftest. No network, no credentials, and every
check runs against a throwaway copy of the tool in its own temp directory.

    python3 tests/test_linter_selftest.py

Five of these checks break the tool on purpose. The claim being tested is that
`--selftest` exits non-zero when a rule cannot fire and when a clean corpus
produces a finding, and the only way to test that is to make each of those
things true and watch it happen.

Exit 0 only if every check passes.
"""

import ast
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "src", "linter_selftest.py")

with open(TOOL) as _f:
    SOURCE = _f.read()

PASS = 0
FAIL = 0


def check(name, fn):
    """Run one check. A check is a function that raises on failure."""
    global PASS, FAIL
    d = tempfile.mkdtemp(prefix="linter-selftest-test-")
    try:
        fn(d)
        print("  ok    %s" % name)
        PASS += 1
    except Exception as exc:
        print("  FAIL  %s: %s: %s" % (name, type(exc).__name__, exc))
        FAIL += 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


def run(script, *args):
    p = subprocess.run([sys.executable, script] + list(args),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def mutated(d, needle, *new_lines):
    """Write a copy of the tool with the one line containing `needle` replaced.

    The needle has to match exactly one line. A mutation that silently matched
    nothing would leave the tool intact and the check would pass for the wrong
    reason, which is the failure this whole package is about."""
    lines = SOURCE.splitlines(True)
    hits = [i for i, line in enumerate(lines) if needle in line]
    assert len(hits) == 1, "needle %r matched %d lines, wanted exactly 1" % (needle, len(hits))
    i = hits[0]
    indent = " " * (len(lines[i]) - len(lines[i].lstrip()))
    lines[i:i + 1] = [indent + text + "\n" for text in new_lines]
    path = os.path.join(d, "mutated.py")
    with open(path, "w") as f:
        f.write("".join(lines))
    return path


def write_notes(d, files):
    for rel, content in files.items():
        path = os.path.join(d, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)


CLEAN_NOTE = "---\ntype: note\nstatus: draft\ncites: []\n---\nbody\n"
BAD_NOTE = "---\ntype: note\nstatus: pubished\ncites: []\n---\nbody\n"


# --- the tool, unmodified --------------------------------------------------

def t_selftest_passes(d):
    code, out = run(TOOL, "--selftest")
    assert code == 0, "selftest exited %d:\n%s" % (code, out)
    assert "self-test OK" in out, out


def t_clean_dir_exits_zero(d):
    write_notes(d, {"notes/One.md": CLEAN_NOTE})
    code, out = run(TOOL, d)
    assert code == 0, "expected 0 on a clean directory, got %d:\n%s" % (code, out)
    assert "no findings" in out, out


def t_findings_exit_one(d):
    write_notes(d, {"notes/One.md": BAD_NOTE})
    code, out = run(TOOL, d)
    assert code == 1, "expected 1 on a directory with findings, got %d:\n%s" % (code, out)
    assert "status-value" in out, out


def t_json_output_parses(d):
    write_notes(d, {"notes/One.md": BAD_NOTE})
    code, out = run(TOOL, d, "--json")
    import json
    parsed = json.loads(out)
    assert code == 1 and len(parsed) == 1, out
    assert parsed[0]["rule"] == "status-value", out


# --- break the claim: a rule that cannot fire ------------------------------

def t_dead_rule_is_caught(d):
    """Arm one. Take the body out of a rule so it can never report anything.
    The tool has to refuse to certify itself, and has to name the dead rule."""
    path = mutated(d, 'out.append(Finding("status-value"', "pass")
    code, out = run(path, "--selftest")
    assert code == 2, "a dead rule exited %d, expected 2:\n%s" % (code, out)
    assert "SELF-TEST FAILED" in out, out
    assert "status-value" in out, "the failure did not name the dead rule:\n%s" % out


def t_dead_rule_reported_twice(d):
    """The same mutation should be caught by the fixture that expects the rule
    AND by the source scan that finds no code emitting it. Two independent
    detections, so removing either one still leaves the mutation caught."""
    path = mutated(d, 'out.append(Finding("status-value"', "pass")
    _, out = run(path, "--selftest")
    assert "expected 'status-value' to fire" in out, out
    assert "no code emits it" in out, out


# --- break the claim: a rule that always fires -----------------------------

def t_promiscuous_rule_is_caught(d):
    """Arm two, and the half almost nobody writes. A linter that reports a
    finding on every note passes every positive fixture, because every fixture
    contains a note. Only the clean corpus catches it."""
    path = mutated(d, 'status = fields.get("status", "").strip()',
                   'status = fields.get("status", "").strip()',
                   'out.append(Finding("always-fires", rel, "every note, every time"))')
    code, out = run(path, "--selftest")
    assert code == 2, "a promiscuous rule exited %d, expected 2:\n%s" % (code, out)
    assert "CLEAN CORPUS produced" in out, out


# --- load-bearing: disable the mechanism, watch a check go red -------------

def t_chain_walk_is_load_bearing(d):
    """Stop the sourcing rule from following a citation to the note behind it.
    Every positive fixture still fires, so nothing in the positive half notices.
    The clean corpus is what goes red, because a legitimate note that reaches
    its two sources through two other notes now looks unsourced."""
    path = mutated(d, "stack.append(nxt)", "pass")
    code, out = run(path, "--selftest")
    assert code == 2, "the neutered chain walk exited %d, expected 2:\n%s" % (code, out)
    assert "CLEAN CORPUS produced 1 finding(s)" in out, out
    assert "thin-sourcing" in out, out


# --- the rule inventory ----------------------------------------------------

def t_unfixtured_rule_is_caught(d):
    """A rule nobody wrote a fixture for. It never fires here, so no fixture
    fails; the source scan is the only thing that sees it."""
    path = mutated(d, 'status = fields.get("status", "").strip()',
                   'status = fields.get("status", "").strip()',
                   'if status == "\\x00never":',
                   '    out.append(Finding("orphan-rule", rel, "unreachable"))')
    code, out = run(path, "--selftest")
    assert code == 2, "an unfixtured rule exited %d, expected 2:\n%s" % (code, out)
    assert "rule 'orphan-rule' has no fixture" in out, out


# --- the fixtures themselves -----------------------------------------------

def t_case_folded_names_are_refused(d):
    """Two fixture names that differ only by case are one file on macOS and two
    on Linux. The harness refuses the pair rather than passing on one platform
    and failing on the other."""
    sys.path.insert(0, os.path.join(HERE, "..", "src"))
    import linter_selftest as tool
    from pathlib import Path
    try:
        tool.write_corpus(Path(d), {"notes/Same.md": CLEAN_NOTE, "notes/same.md": CLEAN_NOTE})
    except AssertionError as exc:
        assert "case is folded" in str(exc), str(exc)
        return
    raise AssertionError("write_corpus accepted two names that differ only by case")


def t_shipped_fixture_names_are_distinct(d):
    sys.path.insert(0, os.path.join(HERE, "..", "src"))
    import linter_selftest as tool
    names = list(tool.CLEAN_CORPUS)
    for _, extra, _ in tool.FIXTURES:
        names.extend(extra)
    lowered = [n.lower() for n in names]
    dupes = set(n for n in lowered if lowered.count(n) > 1)
    assert not dupes, "fixture names collide once case is folded: %s" % sorted(dupes)


# --- portability -----------------------------------------------------------

def t_syntax_parses_under_old_python(d):
    """The syntax is checked against Python 3.7 rules. This says nothing about
    library behaviour on 3.7, which is why the README claims 3.9 and not 3.7."""
    ast.parse(SOURCE, filename="linter_selftest.py", feature_version=(3, 7))


CHECKS = [
    ("the shipped tool certifies itself", t_selftest_passes),
    ("a clean directory exits 0", t_clean_dir_exits_zero),
    ("a directory with findings exits 1", t_findings_exit_one),
    ("--json emits parseable findings", t_json_output_parses),
    ("a rule that cannot fire is caught and named", t_dead_rule_is_caught),
    ("a dead rule is caught two independent ways", t_dead_rule_reported_twice),
    ("a rule that always fires is caught by the clean corpus", t_promiscuous_rule_is_caught),
    ("disabling the chain walk turns the clean corpus red", t_chain_walk_is_load_bearing),
    ("a rule with no fixture is caught", t_unfixtured_rule_is_caught),
    ("two names differing only by case are refused", t_case_folded_names_are_refused),
    ("the shipped fixture names survive a case-folding filesystem", t_shipped_fixture_names_are_distinct),
    ("the source parses under Python 3.7 syntax rules", t_syntax_parses_under_old_python),
]


def main():
    print("linter-selftest: %d offline checks" % len(CHECKS))
    for name, fn in CHECKS:
        check(name, fn)
    print("")
    print("%d passed, %d failed" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
