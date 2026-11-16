# linter-selftest

[![tests](https://github.com/justin-rhee/linter-selftest/actions/workflows/test.yml/badge.svg)](https://github.com/justin-rhee/linter-selftest/actions/workflows/test.yml) [![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) ![python >= 3.9](https://img.shields.io/badge/python-%3E%3D3.9-blue.svg) ![zero dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)

Proves every rule in a linter can still catch something, so a clean report actually means clean.

```
$ python3 linter_selftest.py --selftest
self-test OK: 2 rule(s), 5 fixture(s) each proved to fire, clean corpus quiet

# now replace the line that reports a bad status with `pass`
$ python3 linter_selftest.py --selftest
SELF-TEST FAILED. A clean report from this linter means nothing:
  x a status outside the allowed set: expected 'status-value' to fire, got nothing
  x a fixture expects rule 'status-value' but no code emits it
$ echo $?
2
```

A clean report, three times over, hid a rule that had never run. It lived as a line of prose in a checklist a model worked through, and somewhere along the way it got skipped. Two notes sat with a disallowed value for weeks until I found them by hand. A rule that never runs and a folder with nothing wrong print exactly the same thing.

## Use it if

- a check of yours has never once reported a finding
- your rules are added by hand and nothing notices when one goes missing
- you'd rather a green report mean something than arrive on time

## Install

One Python file, standard library only. Copy `src/linter_selftest.py` next to your code, or copy the shape into the linter you already have, and wire `--selftest` into CI. It builds its own notes in a temp folder, so trying it touches nothing of yours. The shape is four parts:

- one fixture per rule, carrying only that rule's defect, asserted to produce its finding
- one set of notes with nothing wrong, asserted to produce no findings
- the rule list read out of the source, so a rule with no fixture is an error
- a non-zero exit on either failure, run automatically

## How it works

The example linter has two rules: a `status` field must hold one of three values, and a note marked `published` must reach two distinct sources through its `cites` links. `--selftest` exits 2 if any rule stays silent on its own defect, or if any rule fires on the clean set. The rule list comes from the source rather than a hand-kept list, because a hand-kept list fails exactly the way the original rule did.

## What it won't do

- serve as a real linter for your notes, since the two rules are only an example
- prove a rule is right, only that it can fire, so a fixture built on a misunderstanding passes cleanly
- cover note shapes missing from the clean set, so a rule misfiring on one ships until you add it
- see a rule whose name is built from a variable, since the inventory looks for `Finding("name"` in the source
- tell apart two notes that differ only by case, though the self-test refuses to write fixtures like that
- run on Windows, which is untested, or below Python 3.9.6, the floor verified here
- stand in for a security tool, since it catches a rule that can't fire, not one removed on purpose

## How I tested it

- 12 offline checks, each against a throwaway copy of the tool: `python3 tests/test_linter_selftest.py`
- five break the tool on purpose, since the only way to test a non-zero exit is to make it true and watch
- disabling the citation chain walk left every positive fixture firing while the clean set went red, and that case is pinned in the suite

## License

MIT. See [LICENSE](LICENSE). No warranty. Security notes and how to report a problem: [SECURITY.md](SECURITY.md). Design decisions: [docs/ADR.md](docs/ADR.md).

<!-- related:start -->
## Related

- [hook-canary](https://github.com/justin-rhee/hook-canary): proves an installed hook still works by running it
- [scar-audit](https://github.com/justin-rhee/scar-audit): shows which written rules your agent quietly skips

Part of a small set of tools I pulled out of my own agent harness. I use them myself and read every issue. More on my [GitHub profile](https://github.com/justin-rhee).
<!-- related:end -->
