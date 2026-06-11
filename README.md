# markwork

Sphinx docs without autodoc: your source, exactly, made click-through.

markwork is a Sphinx extension that replaces the docstring-extraction
model of autodoc. Instead of summarising your code, the published page
for a file *is* that file, rendered verbatim with Pygments and made
navigable. Every name is a link to where it is defined: a project symbol
or a same-file module-scope name jumps to its definition, and a
standard-library member or a builtin links out to docs.python.org. The
links are read from the syntax tree, so they land exactly rather than by
guesswork.

The name is `markwork`, from the Danish `makværk`, with a wink at markup.

## Install

```bash
pip install markwork
```

This pulls in Sphinx and Pygments. markwork rides on Sphinx for the HTML
shell, search, theme, and hosting; what it replaces is autodoc.

## Use

Add one line to your `conf.py`:

```python
extensions = ["markwork"]
```

Then include the generated package tree from your `index.rst`:

```rst
.. include:: _source/_packages.txt
```

By default markwork documents the single package found under `src/` and
mirrors the `tests/` directory. Three configuration values steer it when
the defaults do not fit:

```python
markwork_package = "yourpackage"   # auto-detected when only one exists
markwork_src_root = "src"          # source root, relative to the project
markwork_tests_root = "tests"      # test root, relative to the project
```

The project root is taken to be the parent of the directory holding
`conf.py`.

## What you get

- Every source file reachable from a package's public `__all__` is
  rendered verbatim, one page each, with a tests tree mirroring `tests/`.
- "Used in" and "Usage in testing" back-references on each symbol page.
- Go-to-definition links on every name: project symbols and same-file
  names jump within the docs, standard-library members and builtins link
  to docs.python.org.
- All of it computed from the AST and the Pygments token stream, with no
  regular expressions anywhere in the engine.

## Licence

markwork is released under the Apache License 2.0. See `LICENSE`.
