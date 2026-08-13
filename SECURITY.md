# Security policy: linter-selftest

## Posture

linter-selftest is provided as-is, with no warranty (see LICENSE). It is a
correctness tool for people who write checks, not a security boundary, and it
makes no promise about stopping anything malicious.

The honest ceiling: it detects a rule that cannot fire and a rule that fires on
everything. It does not detect a rule that is wrong, a rule someone removed on
purpose, or a fixture written around a misunderstanding of what the rule should
catch. Anyone who can edit the source can edit the fixtures alongside it, and the
self-test will certify the result.

Two properties worth knowing before you rely on it.

The rule inventory is a textual scan for `Finding("name"` in the source. A rule
that builds its name from a variable is invisible to it, so the coverage check
will not know that rule exists.

Note content is read as data. The frontmatter parser is a small regex over flat
`key: value` lines. It does not import a YAML library, so a note cannot cause
object construction during parsing, and nothing in a note is ever executed or
interpreted. Notes are read with `errors="replace"`, so malformed bytes cannot
raise from the read.

## Validation status

The offline suite in `tests/test_linter_selftest.py` has been run: 12 checks, all
passing, on Python 3.9.6 under macOS. Five of the twelve mutate the tool on
purpose and assert that it then refuses to certify itself, covering both
directions of the headline claim: a rule that cannot fire, and a clean corpus
that produces a finding.

The load-bearing mutation was also run by hand. Disabling the citation chain walk
turns the clean corpus red with exit 2 and leaves every positive fixture passing.
The line was restored and the suite is green again, and that mutation now runs in
the suite so it cannot quietly stop being true.

There is no fuzzing corpus and no adversarial corpus. The threat model is an
honest author with a rule that silently does not run, not somebody trying to
smuggle a broken check past the self-test, and a hostile author defeats this
trivially by writing a fixture that agrees with a broken rule. That is a limit of
the design, not a bug to fix.

## Reporting a problem

Report privately through this repository's Security tab, using GitHub's
"Report a vulnerability" flow, or by opening a minimal issue that describes the
impact without a working exploit. Please give a reasonable window for a fix
before publishing details.

For a correctness bug that is not security sensitive, a normal issue with a
reproduction is the fastest path.
