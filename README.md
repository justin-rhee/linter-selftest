# linter-selftest

[![tests](https://github.com/justin-rhee/linter-selftest/actions/workflows/test.yml/badge.svg)](https://github.com/justin-rhee/linter-selftest/actions/workflows/test.yml)

What's a clean report worth if you've never watched the rule fire? Mine came back
clean three times before I thought to ask. One of the rules had never run at all:
it lived as a line of prose in a checklist a model worked through at run time,
and somewhere between the checklist and the run it got skipped. Two notes ended
up carrying a value that wasn't allowed, in the field that decides whether a note
gets pushed out to other tools, and there they sat until I found them weeks later
by reading the notes myself. Nothing errored. A rule that never runs and a corpus
with nothing wrong in it print exactly the same thing.

If you've got a linter, a policy check, a guard rule, or a review step anywhere
in your setup, you have this too. So: a small markdown linter that proves its own
rules can fire.

## Use it if

- a check of yours has never once reported a finding
- your rules are added by hand and nothing notices when one goes missing
- you'd rather a green report mean something than arrive on time

## How it works

The linter here reads markdown notes and has exactly two rules: a `status` field
has to hold one of three values, and a note marked `published` has to reach two
distinct sources by following its `cites` links, which means walking a chain,
since a note usually cites another note rather than a source directly.

Two rules is enough to carry `--selftest`, the piece I'd copy into something of
my own. It does two things and exits 2 if either fails.

Every rule runs against a corpus carrying exactly its own defect and has to
report it, which catches a rule whose body was deleted, commented out, or never
wired in. Every rule also runs against a corpus with nothing wrong in it, where
the result has to be empty. That second half catches the opposite failure: a rule
that reports on every note passes all five positive fixtures, because all five
contain notes, and only a clean corpus tells a working rule from one that always
says yes.

The rule list is read out of the source rather than kept by hand, because a
hand-kept list fails exactly the way the original rule did: somebody writes a
rule, doesn't add it to the list, nothing notices. So the self-test compares the
names in the source against the names the fixtures claim and complains in both
directions. A rule with no fixture is an error, and a fixture pointing at a rule
no code emits is what names the dead rule when you delete its body.

The checker also lives outside the notes it checks. A validator stored inside the
thing it validates can be rewritten by anyone with write access, and after that
it approves whatever they like. This one takes the directory as an argument and
reads note content as data, never executing or interpreting it.

```
$ python3 src/linter_selftest.py notes/
notes: 2 finding(s)
  status-value  Margins.md: status='pubished' is not one of ['draft', 'published', 'review']
  thin-sourcing Headcount.md: published on 1 distinct source(s), needs 2
```

A clean run says so, and then says what a clean run is worth.

```
$ python3 src/linter_selftest.py notes/
notes: no findings.
Run --selftest before believing that. An unexercised linter and a
clean corpus print the same thing.
```

## Try it before you install it

Download the one file and run the self-test. It builds its own corpus in a temp
directory, so it touches nothing of yours.

```
$ python3 linter_selftest.py --selftest
self-test OK: 2 rule(s), 5 fixture(s) each proved to fire, clean corpus quiet
$ echo $?
0
```

Then break it on purpose. Find the line that reports a bad status value and
replace it with `pass`:

```
$ python3 linter_selftest.py --selftest
SELF-TEST FAILED. A clean report from this linter means nothing:
  x a status outside the allowed set: expected 'status-value' to fire, got nothing
  x a fixture expects rule 'status-value' but no code emits it
$ echo $?
2
```

That's the whole claim, and checking it yourself takes about a minute.

## Install

Copy `src/linter_selftest.py` next to your code, or read it and copy the shape
into the linter you already have. Standard library only, so there's nothing to
install and no virtualenv to make.

```
python3 linter_selftest.py path/to/notes    # exit 0 clean, 1 findings
python3 linter_selftest.py --selftest       # exit 0 proved, 2 not proved
python3 linter_selftest.py --json notes/    # findings as JSON
```

Wire `--selftest` into CI next to your test suite. It's a second or two, and it's
the only thing standing between you and a green report that means nothing.

If you're copying the shape rather than the file, four parts make it work:

- one fixture per rule, carrying that rule's defect and nothing else, asserted to
  produce that rule's finding
- one corpus with nothing wrong in it, asserted to produce no findings at all
- the rule list read out of the source, so a rule with no fixture is an error
  rather than an oversight
- a non-zero exit on either failure, run automatically, so nobody has to remember
  to look

## What it won't do

The two rules are an example. If you want a real linter for your notes this isn't
it, and the self-test is the part to take.

It proves a rule can fire, not that the rule is right. A fixture built around a
misunderstanding of what the rule should catch passes cleanly, and the self-test
has no way to know your fixture is dishonest. That judgment stays with you, which
is why this doesn't replace review.

The clean corpus only covers the shapes that are in it, so a rule firing wrongly
on some note shape nobody added is a false positive that ships. Each time you
find one, add that shape to the corpus. That's how the corpus in here grew a note
reaching its sources through two other notes

The rule inventory works by finding `Finding("name"` in the source, so a rule
building its name from a variable or a formatted string is invisible to the scan.

Note titles are filenames and resolution is case-sensitive, while macOS
filesystems aren't, so two notes differing only by case are one file on a Mac and
two on Linux. The self-test refuses to write fixtures that differ only by case,
but a real corpus of yours can still fall into it.

Verified on Python 3.9.6, with a test asserting the syntax parses under 3.7
rules, though I haven't run it there, so treat 3.9 as the floor. Windows is
untested. It's not a security tool either: it catches a rule that can't fire, not
a rule someone removed on purpose.

## How I tested it

12 offline checks, each against a throwaway copy of the tool:
`python3 tests/test_linter_selftest.py`.

Five of them break the tool on purpose, because the only way to test that
`--selftest` exits non-zero when a rule can't fire is to make that true and
watch it happen.

Deleting a rule's body is the first, and two separate parts of the self-test
report it, so removing either one still leaves the mutation caught.

```
SELF-TEST FAILED. A clean report from this linter means nothing:
  x a status outside the allowed set: expected 'status-value' to fire, got nothing
  x a fixture expects rule 'status-value' but no code emits it
exit=2
```

A rule that fires on everything is the second, and I'd have skipped it if I
hadn't thought about it. Every positive fixture still passes, because every
fixture has notes and the noisy rule reports on all of them. Only the clean
corpus objects, with seven findings and a complaint that the rule has no fixture.

The third changed my mind about which half of the self-test does the work. The
sourcing rule follows a citation from one note to the next, so I disabled that
line and re-ran: every positive fixture still fired and noticed nothing, while
the clean corpus went red, because a legitimate note reaching its two sources
through two other notes now read as unsourced. That one is in the suite now as
`disabling the chain walk turns the clean corpus red`, so it can't quietly stop
being true.

Run locally on macOS 15 with the system python3, 3.9.6. Linux comes from the CI
matrix, not from anything I ran by hand.

## License

MIT, see [LICENSE](LICENSE). No warranty. Security posture and how to report a
problem: [SECURITY.md](SECURITY.md).

Design decisions and what changed while building it: [docs/ADR.md](docs/ADR.md).

One of a handful of small tools I pulled out of the agent setup I run day to day. I use them all myself, so I notice quickly when one breaks. Open an issue anytime, whether something's wrong or you just want to ask about it. I'll read it and fix what I can. More of them on my [GitHub profile](https://github.com/justin-rhee).
