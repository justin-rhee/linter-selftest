# Architecture Decision Records (ADRs)

Why this is shaped the way it is, including the decision I got wrong first and
the one a test argued me out of.

## The self-test is part of the tool, not part of the test suite

The thing that failed was a rule that never executed. The report was clean, and
clean was also what the report said when everything was fine, so there was no
signal anywhere to notice. Whatever fixed that had to run at the same moment
somebody was deciding whether to believe the output.

A proof that lives in `tests/` does not travel. This is a single file people copy
into their own project, and the copy is exactly where the proof is needed and
exactly what a test directory gets left behind by. The person pasting the file
into their setup has no clone, no suite, and no reason to go look for one.

So `--selftest` is a flag on the tool. It builds its corpora in a temp directory,
touches nothing of the caller's, runs in about a second, and exits 2 when it
cannot certify itself. Anyone holding the file can ask it to prove itself, and CI
can ask it on every push. The suite in `tests/` still exists, and its job is
different: it breaks the self-test on purpose to check that the self-test still
notices.

One consequence worth naming. There is more self-test in this file than there is
linter, 111 lines against 95. For a tool this small that ratio looks wrong, right
up until you remember that the 95 lines are a linter nobody has a reason to
trust.

## The clean corpus is the half that earns its place

I expected the positive fixtures to be the valuable part. One fixture per rule,
each carrying that rule's defect, each asserted to produce that rule's finding.
That catches the failure I actually had, so it felt like the whole answer.

It is not, and the mutation that showed me is in the suite now. The sourcing rule
follows a citation from one note to the next, because a note usually cites
another note rather than a source directly. I disabled the one line that
continues the walk and re-ran. Every positive fixture still fired, all five of
them, and the positive half of the self-test reported nothing wrong. The clean
corpus went red, because a legitimate note that reaches its two sources through
two other notes had started reading as unsourced.

The general version of that is worse than the specific one. Consider a rule that
reports a finding on every note it sees. It passes every positive fixture,
because every fixture contains notes, so a self-test built only from positive
fixtures certifies a linter that has stopped discriminating entirely. Nothing in
the positive half can tell a working rule apart from one that always says yes.
Only a corpus with nothing wrong in it can.

So the clean corpus runs first, and a finding there is reported before any
fixture result, since a linter that flags everything makes every positive result
below it meaningless.

## The rule list is read out of the source

Once the fixtures existed, the obvious next question was what happens to a rule
nobody wrote a fixture for. The obvious answer was a list of rule names at the
top of the file, checked against the fixtures.

That list has the same failure mode as the rule that started all of this. Someone
writes a rule, does not add the name, and nothing notices, which is precisely the
shape of the original defect reproduced one level up. A control that fails the
same way as the thing it controls is not a control.

So the self-test reads the file's own source and pulls out every rule name that
appears in a `Finding(...)` call, then compares that set against the names the
fixtures claim. A name in the source with no fixture is an error. A fixture
pointing at a name no code emits is an error too, and that second direction is
what makes the output name the dead rule when you delete a rule's body.

The cost is that the scan is textual, so a rule that builds its name from a
variable is invisible to it. That is in the README as a limit. I would rather
have a check that covers the normal case and says where it stops than a hand-kept
list that covers nothing and looks complete.

## Each finding is appended on one line

Small and worth writing down, because it looks like formatting and is not. The
break-the-claim tests work by rewriting exactly one line of the source and
running the result, and a `findings.append(...)` split across two lines cannot be
replaced with `pass` without producing a syntax error. The first version did
exactly that: the mutated copy would not parse, so the probe reported an
indentation error rather than exercising anything. That is the lucky version of
getting it wrong, since it is loud. So the detail string is built on its own line
and the append is one line.

The unlucky version is a probe whose search string matches nothing, which leaves
the tool intact and the check passing for a reason that has nothing to do with
the claim. The helper asserts its search string matches exactly one line, so a
probe that has drifted out of date fails instead.

## Two rules, not the fifteen it started as

This came out of a checker for a private store of notes, with a schema, required
fields per type, identifier formats, directory rules, staleness windows, and a
handful of cross-document constraints. None of that transfers. The schema was
specific to one person's filing system, and a reader would have had to work
through several hundred lines of somebody else's field names to find the twenty
lines that are actually the idea.

What transfers is the proof shape, so the rules were cut to two. One is trivial
and is the one that failed in real life: a field has to hold one of a few allowed
values. The other has a chain walk, a cycle guard, and a distinctness requirement,
which is enough structure for a real mutation to hide in. Between them they cover
both halves of the self-test, and the second is the reason the load-bearing test
has something interesting to disable.

Two rules does mean this reads as a toy if you come at it as a linter. It is not
offered as one.

## Fixture filenames cannot differ only by case

The original had a latent bug that only luck kept quiet. Notes are addressed by
filename, and the note map is keyed on the filename with the extension removed.
On Linux, `Anchor.md` and `anchor.md` are two files. On macOS they are one, and
whichever fixture is written second silently overwrites the first.

The consequence is not a loud failure, which is what makes it worth guarding. On
a Mac you get a corpus quietly missing a control, and a self-test that passes
because the case it was supposed to check is not there any more. On Linux the
same code has both files and behaves differently. The suite is green in one place
and red in the other, and the green one is lying.

The helper that writes a corpus now refuses two names that collide once case is
folded, and raises before writing anything. A second check walks the shipped
fixture names and asserts the same property, so the guard is exercised even when
no fixture is currently trying to violate it. The corpus in here dodges the
hazard on purpose rather than by accident, and the names are far enough apart
that nobody has to think about it while adding the next one.

This is a property of the harness, not a lint rule. A real corpus of yours can
still contain two notes differing only by case, and this tool will resolve links
to them by exact match. That limit is in the README.

## The checker lives outside the notes it checks

The store this came from is written to by more than one process, including an
agent, so the store is treated as untrusted input. A validator kept inside the
thing it validates is only as trustworthy as write access to that thing: whoever
can edit the notes can edit the checker, and after that the checker approves
whatever they like. The same argument applies to a repository's own lint config,
which is why the interesting version of this problem is not hypothetical.

So the checker takes the directory as an argument and lives somewhere else, and
it reads note content as data. It parses frontmatter with a small regex, never
imports a YAML library that could be induced to construct objects, and never
executes or interprets anything it reads.

## What is deliberately not here

No mutation testing framework. The three mutations that matter are written out by
hand in the suite, they run in a second, and they are readable as English. A
framework would generate hundreds of mutations of a 150 line file and bury the
three that carry the argument.

No YAML dependency. The frontmatter parser handles flat `key: value` pairs and
nothing else, which is all the example needs, and it keeps the file to a single
copy-and-run artifact with no install step. A real linter with real schema needs
would swap in a parser, and should read the note above about which parsers can
construct objects.

No auto-fix. The point of this package is that a report can be wrong in a way
that is invisible, and a tool that rewrites your files on the strength of such a
report is a worse version of the original problem.
