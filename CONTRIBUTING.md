# Contributing

Thank you for taking an interest in the development of *markwork*! Since
this project is the work of a single developer, this document attempts to
provide an overview of the development process. This process does result
in a particular structure, and while this structure is quite rigid, the
process itself is not.

## Setup

*markwork* is a build-time Sphinx extension; its runtime dependencies are
Sphinx and Pygments, both pulled in on install. The development process
makes use of 'mamba' to provide a virtual environment. You do not need to
use 'mamba', but it is strongly recommended that you use some sort of
virtual environment rather than system Python. This recommendation applies
generally to Python development.

The [miniforge](https://github.com/conda-forge/miniforge) distribution
provides a convenient way to get 'mamba'. Refer to the link provided for
installation instructions. For arch, the 'aur' does provide a package:

```terminaloutput
yay -S miniforge
```

Once installed, clone the repository and create the virtual environment
with:

```terminaloutput
mamba env create -f environment.yml
mamba activate markwork_env
```

Then install the package in editable mode so the tests and the docs build
pick it up:

```terminaloutput
pip install -e .
```

## Version Support

*markwork* supports Python 3.10 and up. The floor is 3.10 because the full
feature set needs `sys.stdlib_module_names` and the position attributes on
`ast.alias`, both added in 3.10. Every feature works there and nothing in
*markwork* needs anything newer, so there is no backport machinery to
maintain: no `from __future__ import annotations`, no `TYPE_CHECKING`
dance, and the walrus operator and other modern syntax are fair game.

## Testing and Coverage

A point of pride for *markwork* is the 100% branch coverage of the test
suite. This requirement is non-negotiable. The CI pipeline contains a
measurement of the coverage that is authoritative, and included in the
repository is the `coverage_test.sh` script that reliably achieves the
same results. It runs all the tests in the `tests` directory with branch
coverage and, if all pass, opens the HTML report in the system browser.

The suite is decomposed into small pure helpers, so most of the engine
tests directly, without Sphinx in the loop. Each test case lives in its
own `test_*.py`. One check reaches the network: the live-anchor
verification against docs.python.org, in `test_network_anchors.py`. It is
skipped unless `MARKWORK_NETWORK` is set in the environment, and it is
excluded from the coverage accounting, so the offline run stays
deterministic.

A failing test means fix the source, not weaken the test. The tests are
the spec.

## Documentation

The documentation is built with [Sphinx][sphinx], but it takes an unusual
approach: it is built by *markwork* itself, documenting *markwork*. This
is the dogfood. Rather than extracting and reformatting docstrings, the
page for a source file *is* that file, shown verbatim with syntax
highlighting. Nothing is imported and no docstrings are parsed: the engine
reads each file as text, highlights it with Pygments, and wires the result
into a navigable site, so what you read on the site is exactly the code in
the repository.

Only files reachable from a package's public `__all__` get a page, which
keeps private helper modules out of view, and a mirror of the `tests`
directory is included so the tests document their own usage. Each
documented symbol gains two cross-reference sections, 'Used in' and 'Usage
in testing', that list every line in the source and the tests where the
symbol appears, each one a link to that exact line.

The rendered source is itself click-through: every name is wrapped in a
link to where it is defined. A *markwork* symbol links to its page, a name
defined earlier in the same file links back to that line, and a
standard-library member or a builtin links out to the matching page on the
official Python documentation. These links are read from the syntax tree,
so they land exactly rather than by guesswork. To preview the whole site
locally, run `build_docs.sh`, which builds the pages into `docs/_build`
and opens them in the browser.

## STYLE

Horizontal scrolling is the worst! No line shall exceed 77 characters
ever for any reason! Because of this limitation we cannot afford four
spaces per indentation and thus make do with two-space indentation.

Each class lives in its own file, named for it, and the same applies to
the test suite, where every test case has its own `test_*.py`. Private
dunder names carry both a leading and a trailing double underscore, for
example `__compiled_func__`, and never the single-leading `__name` form,
so that Python's name mangling never rewrites them.

Docstrings are natural prose in full sentences, declarative rather than
imperative. Since the page is the source itself, a docstring earns its
place only by adding what the code cannot show. Rather than having a
docstring tautologically explain that `getFoo` is the getter function for
`Foo`, just omit it entirely.

Spelling is British. File handling is explicit: initialise the handle to
None and use try/except/else/finally rather than a `with open(...)` block.
And the engine is built without `re`: *markwork* uses `ast`, the
tokenizer, and plain string methods instead. For a text tool, a
regex-free engine is both a value and a point of pride. Never import `re`
in the package.

## LICENSE

*markwork* is released under Apache-2.0, and contributions are accepted
under the same license. This is not a separate agreement you have to sign.
Section 5 of the license already provides that anything you intentionally
submit for inclusion is licensed under Apache-2.0 unless you state
otherwise, so the inbound and outbound terms match and no contributor
license agreement is needed.

The patent provisions live in section 3. Contributing grants a
royalty-free patent license covering your contribution, so the project and
its users are protected against a later patent claim over code you added.
The same section is the reverse card: if anyone starts patent litigation
alleging that *markwork* infringes, their patent license under Apache-2.0
terminates on the day the suit is filed. By opening a pull request you
accept these terms for your contribution.

[sphinx]: https://www.sphinx-doc.org/
