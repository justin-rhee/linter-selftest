# linter-selftest

[![tests](https://github.com/justin-rhee/linter-selftest/actions/workflows/test.yml/badge.svg)](https://github.com/justin-rhee/linter-selftest/actions/workflows/test.yml)

One plain linter for markdown notes that proves its own rules can fire: **checks status values against an allowed set**, **walks citation chains to published sources**, and **self-tests every rule against a defect corpus and a clean one**. It is one Python file, standard library only, with two example rules; the self-test is the part worth taking.

It was built after a clean report three times over hid a rule that had never run at all: it lived as a line of prose in a checklist a model worked through at run time, and somewhere between the checklist and the run it got skipped. Two notes ended up carrying a disallowed value in the field that decides whether a note gets pushed to other tools, and sat there until they were found by hand weeks later. Nothing errored. A rule that never runs and a corpus with nothing wrong in it print exactly the same thing.

## Use it if

- a check of yours has never once reported a finding
- your rules are added by hand and nothing notices when one goes missing
- you'd rather a green report mean something than arrive on time

## How it works

The linter reads markdown notes and has exactly two rules: a `status` field must hold one of three values, and a note marked `published` must reach two distinct sources by following its `cites` links, walking the chain since a note usually cites another note rather than a source directly.

```
$ python3 src/linter_selftest.py notes/
notes: 2 finding(s)
  status-value  Margins.md: status='pubished' is not one of ['draft', 'published', 'review']
  thin-sourcing Headcount.md: published on 1 distinct source(s), needs 2

$ python3 src/linter_selftest.py notes/
notes: no findings.
Run --selftest before believing that. An unexercised linter and a
clean corpus print the same thing.
```

`--selftest` does two things and exits 2 if either fails. Every rule runs against a corpus carrying exactly its own defect and has to report it, which catches a rule whose body was deleted, commented out, or never wired in. Every rule also runs against a corpus with nothing wrong in it, where the result has to be empty; that catches a rule that reports on every note, which passes all five positive fixtures because all five contain notes. The rule list is read out of the source rather than kept by hand, because a hand-kept list fails exactly the way the original rule did: a rule with no fixture is an error, and a fixture pointing at a rule no code emits is what names the dead rule when you delete its body.

The checker also lives outside the notes it checks. A validator stored inside the thing it validates can be rewritten by anyone with write access, and after that it approves whatever they like. This one takes the directory as an argument and reads note content as data, never executing or interpreting it.

## Try it before you install it

Download the one file and run the self-test. It builds its own corpus in a temp directory, so it touches nothing of yours.

```
$ python3 linter_selftest.py --selftest
self-test OK: 2 rule(s), 5 fixture(s) each proved to fire, clean corpus quiet
$ echo $?
0
```

Then break it on purpose: find the line that reports a bad status value and replace it with `pass`.

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

Copy `src/linter_selftest.py` next to your code, or read it and copy the shape into the linter you already have. Standard library only, so there's nothing to install. Wire `--selftest` into CI next to your test suite; it's a second or two, and it's the only thing standing between you and a green report that means nothing. If you're copying the shape rather than the file, four parts make it work:

- one fixture per rule, carrying that rule's defect and nothing else, asserted to produce that rule's finding
- one corpus with nothing wrong in it, asserted to produce no findings at all
- the rule list read out of the source, so a rule with no fixture is an error rather than an oversight
- a non-zero exit on either failure, run automatically, so nobody has to remember to look

## What it won't do

- serve as a real linter for your notes, since the two rules are an example and the self-test is the part worth taking
- prove a rule is right, only that it can fire, so a fixture built around a misunderstanding of what the rule should catch passes cleanly and the self-test has no way to know your fixture is dishonest
- cover note shapes that aren't in the clean corpus, so a rule firing wrongly on a shape nobody added is a false positive that ships, and each one you find belongs in the corpus
- see a rule whose name is built from a variable or a formatted string, since the inventory works by finding `Finding("name"` in the source
- tell two notes apart when they differ only by case, which is one file on macOS and two on Linux, though the self-test refuses to write fixtures like that
- run on Windows, which is untested, or below Python 3.9.6, which is the floor verified here; a test asserts the syntax parses under 3.7 rules but it hasn't been run there
- stand in for a security tool, since it catches a rule that can't fire rather than a rule someone removed on purpose

## How I tested it

12 offline checks, each against a throwaway copy of the tool: `python3 tests/test_linter_selftest.py`. Five of them break the tool on purpose, because the only way to test that `--selftest` exits non-zero when a rule can't fire is to make that true and watch it happen.

Deleting a rule's body is the first, and two separate parts of the self-test report it, so removing either one still leaves the mutation caught. A rule that fires on everything is the second, and it would have been easy to skip: every positive fixture still passes, because every fixture has notes and the noisy rule reports on all of them, and only the clean corpus objects, with seven findings and a complaint that the rule has no fixture.

The third changed which half of the self-test does the work. The sourcing rule follows a citation from one note to the next, so disabling that line and re-running left every positive fixture firing and noticing nothing while the clean corpus went red, because a legitimate note reaching its two sources through two other notes now read as unsourced. That one is in the suite now as `disabling the chain walk turns the clean corpus red`, so it can't quietly stop being true.

Run locally on macOS 15 with the system python3, 3.9.6. Linux comes from the CI matrix, not from anything run by hand. Design decisions and what changed while building it: [docs/ADR.md](docs/ADR.md).

## Platforms

macOS and Linux today. Windows on the way.

## License

MIT, see [LICENSE](LICENSE). No warranty. Security posture and how to report a problem: [SECURITY.md](SECURITY.md).

This little tool is one of a handful I pulled out of my own day-to-day agent setup. I use them all myself, so when something breaks I usually notice fast. But if you run into any issues, or anything that looks off, open an issue. I read every one. More tools on my [GitHub profile](https://github.com/justin-rhee).