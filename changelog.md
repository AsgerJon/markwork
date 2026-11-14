# Changelog

This changelog covers stable releases. Development ('-dev') and release
candidate ('-rc') builds are not logged on their own; their changes are
rolled into the release they lead up to.

## [Unreleased]

### Added

- The `markwork` command (also `python -m markwork`): point it at a
  repository and it builds the click-through docs from a throwaway
  configuration, detecting the source root, package and tests root from
  what the project declares, and leaving the repository untouched.
- A package without a readable `__all__` is documented from its
  conventionally public names (what its `__init__.py` defines or imports,
  then its submodules and subpackages, none with a leading underscore)
  instead of rendering as a single empty page.
- `__all__` is read through literal `+=`, `.extend()` and `.append()` and
  annotated assignments, wherever it sits at module scope.
- The attribute after an imported project module links to its symbol or
  submodule: `Thing` in `pkg.mod.Thing`, and the usage sections count it.
- A name in `__all__` that resolves to nothing is a Sphinx warning of type
  `markwork` rather than a silently missing page.
- A name a package resolves lazily through a module-level `__getattr__`
  (PEP 562) is followed into the hook to its real definition.
- The command builds with one Sphinx worker per CPU (`-j` to choose),
  more than halving the build time of a large project.
- `markwork_repo_root` configuration value, read relative to the conf.py
  directory, for docs that live outside the project.

### Fixed

- A re-export through a subpackage (`from .core import Thing`), a deeper
  module (`from .a.b import X`), an alias, an absolute self-import or a
  star import got no page. It is now followed to its real definition, so
  markwork's own `markwork.generate` page exists again.
- A non-ASCII character earlier on a line moved every link after it onto
  the wrong token, because the syntax tree counts columns in UTF-8 bytes.
- `except E as name` and match captures were not counted as bindings, so
  `except KeyError as id:` linked the later `id` to the builtin.
- Plain `import pkg.mod` usages were missing from the "Used in" and
  "Usage in testing" sections.
- A source file with a non-UTF-8 coding declaration crashed the whole
  build; one starting with a byte-order mark lost all its links; compile
  warnings from documented code (`SyntaxWarning`) leaked into the build
  log.
- A module named `rst` lost its toctree entry, since Sphinx strips one
  `.rst` from an entry.
- A page for a name ending in `_` (or holding `*` or a backtick) had an
  empty title, since rST read it as markup; titles are escaped now.
- A configured `markwork_package` that is not a package, or a missing
  source root, now fails with a message naming the setting to fix.
- The extension declares itself safe for parallel reading as well as
  writing, so `sphinx-build -j auto` no longer warns and reads serially.
- Every page carried the whole site's navigation tree (furo renders it
  in full), so a site grew with the square of its page count: worktoy's
  was 61 MB, two thirds of it navigation. Each page's tree now holds the
  top level and its own branch (`markwork_collapse_navigation`, on by
  default), and the `markwork` command no longer publishes copies of the
  generated rST: worktoy is 26 MB and builds in a third of the time.
- A file shown on several pages is lexed and scope-resolved once, roughly
  a third off the build time of a large project.

### Changed

- Names are resolved by Python's own scoping rules. A parameter, method,
  local or `except` name shadows only its own scope; before, any binding
  anywhere in a file unlinked that name everywhere in it. A module that
  star-imports gets no builtin links, since the star import may have
  replaced any of them.
- Engine API: `boundAnywhere`, `nestedBound`, `topLevelDefs`,
  `topLevelDefLines` and `addAliasSite` are replaced by `Scope`,
  `resolveScopes`, `moduleStatements`, `charOffset`, `attributeChain`,
  `readSource`, `parseSource` and `lexTokens`. `parseInit` gives `None`
  for a missing or computed `__all__`, and `SourceDocs.run` returns the
  warnings it found.

## [0.1.1] - 2026-06-14

Adds the Read the Docs configuration. The package itself is unchanged
from 0.1.0.

## [0.1.0] - 2026-06-14

First release. *markwork* begins as a standalone, pip-installable Sphinx
extension extracted from worktoy's documentation generator: a project
enables it with `extensions = ["markwork"]` and its docs then render the
project's source verbatim with go-to-definition links. The engine is
regex-free and the test suite holds 100% branch coverage.
