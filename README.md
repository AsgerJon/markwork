[![PyPI version](https://badge.fury.io/py/markwork.svg)](https://pypi.org/project/markwork/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Framework: Sphinx](https://img.shields.io/badge/Sphinx-extension-1A5276.svg)](https://www.sphinx-doc.org/)

# markwork v0.1.0 (alpha)

**markwork** publishes your source as your documentation. The page for a
file *is* that file: rendered verbatim, syntax-highlighted, and with every
name turned into a link to wherever it is defined. It replaces autodoc,
not Sphinx.

Stop documenting your code. Start publishing it.

The name is `markwork`, from the Danish `makværk`, with a wink at markup.

# Table of Contents

- [Installation](#installation)
- [You Already Wrote the Docs](#you-already-wrote-the-docs)
- [Click a Name, Land on the Definition](#click-a-name-land-on-the-definition)
- [Every Page Ends With Its Tests](#every-page-ends-with-its-tests)
- [Quickstart](#quickstart)
- [Themes](#themes)
- [Contributing](#contributing)
- [License](#license)

# Installation

Install with pip:

```bash
pip install markwork
```

This pulls in Sphinx and Pygments. markwork rides on Sphinx for the HTML
shell, search, theme, and hosting. What it replaces is autodoc.

# You Already Wrote the Docs

Here is a function. It is documented. You have written a hundred like it:

```python
def fib(n: int) -> int:
  """Return the nth Fibonacci number.

  Parameters
  ----------
  n : int
      Position in the sequence, counting from zero.

  Returns
  -------
  int
      The nth Fibonacci number.

  Examples
  --------
  >>> fib(10)
  55
  """
  a, b = 0, 1
  for _ in range(n):
    a, b = b, a + b
  return a


class IsEven(metaclass=type('_', (), {'__call__': lambda *a: not a[1] % 2})):
  """
  Parity test of integers. 

  Parameters
  ----------
  n : int
      The integer to test.

  Returns
  -------
  bool
      True if 'n' is even, False otherwise.

  Examples
  --------
  >>> IsEven(4)
  True
  >>> IsEven(7)
  False
  """
```

Then the ceremony starts. A `.rst` stub. An `automodule` directive. A
docstring style your theme half-renders. A `[source]` link that ejects the
reader into a separate viewer to see the four lines that actually matter.

Wouldn't it be easier if you wrote that docstring and were just *done*?

Now you are. Add one line to `conf.py`:

```python
extensions = ["markwork"]
```

markwork publishes the function — docstring, signature, body, all of it —
exactly as you wrote it. The page is the source. You already finished the
documentation; you just did not know it yet.

# Click a Name, Land on the Definition

markwork reads your syntax tree, so every name on the page is wired to
where it comes from. You do not read the docs by scrolling. You read them
the way you read code — by following definitions:

```
widget.py     click Point  →  geometry.py:14   (the def, highlighted)
geometry.py   click hypot  →  docs.python.org/3/library/math.html
sequences.py  click fib    →  sequences.py:30  (back to its own def)
```

Project symbols and same-file names jump inside your docs, at the exact
line. Standard-library members and builtins jump to the official Python
documentation. A name shadowed by a local binding stays unlinked, so a
link never sends you somewhere wrong.

# Every Page Ends With Its Tests

Scroll to the bottom of any symbol's page and the tests that exercise it
are waiting there — listed for you, no digging, file and line, each line a
link straight to the assertion:

```
fib()

Usage in testing
────────────────
  tests/test_sequences.py:  12,  19,  27
```

Click `19` and you land on that line of the test. Per function, you can
see exactly what is covering it. You did write tests, right?

# Quickstart

A complete `src/`-layout project, zero to rendered docs in about a minute.

```
acme/
├─ src/acme/__init__.py     # re-exports your public names, sets __all__
├─ src/acme/widget.py
├─ tests/test_widget.py
└─ docs/
   ├─ conf.py               # extensions = ["markwork"]
   └─ index.rst
```

markwork follows your **public API**: every name in the package's `__all__`
becomes a page, a re-exported symbol pulls in its defining file, and the
`tests/` tree is mirrored for you. So the package's `__init__.py` is your
table of contents:

```python
# src/acme/__init__.py
from .widget import Widget

__all__ = ["Widget"]
```

`docs/index.rst` needs a single include — markwork writes the tree into
`_source/`:

```rst
acme
====

.. include:: _source/_packages.txt
```

Build it:

```bash
pip install markwork furo
sphinx-build -b html docs docs/_build/html
```

Open `docs/_build/html/index.html`. One page per source file, every name a
link, the test suite mirrored alongside.

The defaults assume a single package under `src/` and a `tests/` directory
beside it; the project root is the parent of the folder holding `conf.py`.
Override when needed:

```python
markwork_package = "acme"      # auto-detected when src/ holds one package
markwork_src_root = "src"      # source root, relative to the project
markwork_tests_root = "tests"  # test root, relative to the project
```

Flat layout, with the package at the project root instead of under `src/`?
Point the source root at the root and name the package explicitly:

```python
markwork_src_root = "."
markwork_package = "acme"
```

Requires Python 3.10 or newer.

# Themes

markwork is theme-independent and works with any Sphinx theme: furo,
`sphinx_rtd_theme`, the PyData theme, the built-in alabaster, or your own.
The rendered source is a stock Pygments block, so its syntax colours come
from the active theme's own Pygments style, and the bundled stylesheet
uses inherited and fixed colours so the go-to-definition underlines and
the line-jump highlight read on a light or a dark theme alike.

These docs are built with furo as a preference, not a requirement. To
preview under a different installed theme, set `MARKWORK_THEME`:

```bash
MARKWORK_THEME=alabaster sphinx-build -b html docs docs/_build/html
```

# Contributing

Contributions are welcome. Open an issue or a pull request at
[github.com/AsgerJon/markwork](https://github.com/AsgerJon/markwork).

# License

markwork is released under the Apache License 2.0 (Apache-2.0). See
[LICENSE](LICENSE) for the full text.
